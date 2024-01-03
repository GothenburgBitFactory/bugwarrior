import abc
import copy
import re

from dateutil.parser import parse as parse_date
from dateutil.tz import tzlocal
from jinja2 import Template
import pytz

from taskw.task import Task

from bugwarrior.config.secrets import get_service_password
from bugwarrior.db import MARKUP, URLShortener

import logging
log = logging.getLogger(__name__)


class IssueService(abc.ABC):
    """ Abstract base class for each service """
    # Which class should this service instantiate for holding these issues?
    ISSUE_CLASS = None
    # Which class defines this service's configuration options?
    CONFIG_SCHEMA = None

    def __init__(self, config, main_config):
        self.config = config
        self.main_config = main_config

        log.info("Working on [%s]", self.config.target)

    def get_password(self, key, login='nousername'):
        password = getattr(self.config, key)
        keyring_service = self.get_keyring_service(self.config)
        if not password or password.startswith("@oracle:"):
            password = get_service_password(
                keyring_service, login, oracle=password,
                interactive=self.main_config.interactive)
        return password

    def get_issue_for_record(self, record, extra=None):
        return self.ISSUE_CLASS(
            record, self.config, self.main_config, extra=extra)

    def build_annotations(self, annotations, url=None):
        final = []
        if url and self.main_config.annotation_links:
            final.append(url)
        if self.main_config.annotation_comments:
            for author, message in annotations:
                message = message.strip()
                if not message or not author:
                    continue

                if not self.main_config.annotation_newlines:
                    message = message.replace('\n', '').replace('\r', '')

                annotation_length = self.main_config.annotation_length
                if annotation_length:
                    message = '%s%s' % (
                        message[:annotation_length],
                        '...' if len(message) > annotation_length else ''
                    )
                final.append('@%s - %s' % (author, message))
        return final

    def include(self, issue):
        """ Return true if the issue in question should be included """
        if self.config.only_if_assigned:
            owner = self.get_owner(issue)
            include_owners = [self.config.only_if_assigned]

            if self.config.also_unassigned:
                include_owners.append(None)

            return owner in include_owners

        return True

    @abc.abstractmethod
    def get_owner(self, issue):
        """ Override this for filtering on tickets """
        raise NotImplementedError()

    @abc.abstractmethod
    def issues(self):
        """ Returns a list of dicts representing issues from a remote service.

        Each item in the list should be a dict that looks something like this:

            {
                "description": "Some description of the issue",
                "project": "some_project",
                "priority": "H",
                "annotations": [
                    "This is an annotation",
                    "This is another annotation",
                ]
            }


        The description can be 'anything' but must be consistent and unique for
        issues you're pulling from a remote service.  You can and should use
        the ``.description(...)`` method to help format your descriptions.

        The project should be a string and may be anything you like.

        The priority should be one of "H", "M", or "L".
        """
        raise NotImplementedError()

    @staticmethod
    def get_keyring_service(service_config):
        """ Given the keyring service name for this service. """
        raise NotImplementedError


class Issue(abc.ABC):
    # Set to a dictionary mapping UDA short names with type and long name.
    #
    # Example::
    #
    #     {
    #         'project_id': {
    #             'type': 'string',
    #             'label': 'Project ID',
    #         },
    #         'ticket_number': {
    #             'type': 'number',
    #             'label': 'Ticket Number',
    #         },
    #     }
    #
    # Note: For best results, dictionary keys should be unique!
    UDAS = {}
    # Should be a tuple of field names (can be UDA names) that are usable for
    # uniquely identifying an issue in the foreign system.
    UNIQUE_KEY = []
    # Should be a dictionary of value-to-level mappings between the foreign
    # system and the string values 'H', 'M' or 'L'.
    PRIORITY_MAP = {}

    def __init__(self, foreign_record, config, main_config, extra=None):
        self._foreign_record = foreign_record
        self.config = config
        self.main_config = main_config
        self._extra = extra if extra else {}

    def update_extra(self, extra):
        self._extra.update(extra)

    @abc.abstractmethod
    def to_taskwarrior(self):
        """ Transform a foreign record into a taskwarrior dictionary."""
        raise NotImplementedError()

    @abc.abstractmethod
    def get_default_description(self):
        """ Return the old-style verbose description from bugwarrior.

        This is useful for two purposes:

        * Finding and linking historically-created records.
        * Allowing people to keep using the historical description
          for taskwarrior.

        """
        raise NotImplementedError()

    def get_tags_from_labels(self,
                             labels,
                             toggle_option='import_labels_as_tags',
                             template_option='label_template',
                             template_variable='label'):
        tags = []

        if not getattr(self.config, toggle_option):
            return tags

        context = self.record.copy()
        label_template = Template(getattr(self.config, template_option))

        for label in labels:
            normalized_label = re.sub(r'[^a-zA-Z0-9]', '_', label)
            context.update({template_variable: normalized_label})
            tags.append(label_template.render(context))

        return tags

    def get_added_tags(self):
        added_tags = []
        for tag in self.config.add_tags:
            tag = Template(tag).render(self.get_template_context())
            if tag:
                added_tags.append(tag)

        return added_tags

    def get_taskwarrior_record(self, refined=True):
        if not getattr(self, '_taskwarrior_record', None):
            self._taskwarrior_record = self.to_taskwarrior()
        record = copy.deepcopy(self._taskwarrior_record)
        if refined:
            record = self.refine_record(record)
        if 'tags' not in record:
            record['tags'] = []
        if refined:
            record['tags'].extend(self.get_added_tags())
        return record

    def get_priority(self):
        return self.PRIORITY_MAP.get(
            self.record.get('priority'),
            self.config.default_priority
        )

    def get_processed_url(self, url):
        """ Returns a URL with conditional processing.

        If the following config key are set:

        - [general]shorten

        returns a shortened URL; otherwise returns the URL unaltered.

        """
        if self.main_config.shorten:
            return URLShortener().shorten(url)
        return url

    def parse_date(self, date, timezone='UTC'):
        """ Parse a date string into a datetime object.

        :param `date`: A time string parseable by `dateutil.parser.parse`
        :param `timezone`: The string timezone name (from `pytz.all_timezones`)
            to use as a default should the parsed time string not include
            timezone information.

        """
        if date:
            date = parse_date(date)
            if not date.tzinfo:
                if timezone == '':
                    tzinfo = tzlocal()
                else:
                    tzinfo = pytz.timezone(timezone)
                date = date.replace(tzinfo=tzinfo)
            return date
        return None

    def build_default_description(
        self, title='', url='', number='', cls="issue"
    ):
        cls_markup = {
            'issue': 'Is',
            'pull_request': 'PR',
            'merge_request': 'MR',
            'todo': '',
            'task': '',
            'subtask': 'Subtask #',
        }
        url_separator = ' .. '
        url = url if self.main_config.inline_links else ''
        desc_len = self.main_config.description_length
        return "%s%s#%s - %s%s%s" % (
            MARKUP,
            cls_markup.get(cls, cls.title()),
            number,
            title[:desc_len] if desc_len else title,
            url_separator if url else '',
            url,
        )

    def get_template_context(self):
        context = (
            self.get_taskwarrior_record(refined=False).copy()
        )
        context.update(self.extra)
        context.update({
            'description': self.get_default_description(),
        })
        return context

    def refine_record(self, record):
        for field in Task.FIELDS.keys():
            if field in self.config.templates:
                template = Template(self.config.templates[field])
                record[field] = template.render(self.get_template_context())
            elif hasattr(self, 'get_default_%s' % field):
                record[field] = getattr(self, 'get_default_%s' % field)()
        return record

    def __iter__(self):
        record = self.get_taskwarrior_record()
        yield from record.keys()

    def keys(self):
        return list(self.__iter__())

    def iterkeys(self):
        return self.__iter__()

    def items(self):
        record = self.get_taskwarrior_record()
        return list(record.items())

    def iteritems(self):
        record = self.get_taskwarrior_record()
        yield from record.items()

    def update(self, *args):
        raise AttributeError(
            "You cannot set attributes on issues."
        )

    def get(self, attribute, default=None):
        try:
            return self[attribute]
        except KeyError:
            return default

    def __getitem__(self, attribute):
        record = self.get_taskwarrior_record()
        return record[attribute]

    def __setitem__(self, attribute, value):
        raise AttributeError(
            "You cannot set attributes on issues."
        )

    def __delitem__(self, attribute):
        raise AttributeError(
            "You cannot delete attributes from issues."
        )

    @property
    def record(self):
        return self._foreign_record

    @property
    def extra(self):
        return self._extra

    def __str__(self):
        return '%s: %s' % (
            self.config.target,
            self.get_taskwarrior_record()['description']
        )

    def __repr__(self):
        return '<%s>' % str(self)


class ServiceClient:
    """ Abstract class responsible for making requests to service API's. """
    @staticmethod
    def json_response(response):
        # If we didn't get good results, just bail.
        if response.status_code != 200:
            raise OSError(
                "Non-200 status code %r; %r; %r" % (
                    response.status_code, response.url, response.text,
                ))
        if callable(response.json):
            # Newer python-requests
            return response.json()
        else:
            # Older python-requests
            return response.json
