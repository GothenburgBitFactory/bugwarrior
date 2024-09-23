import abc
import os
import re

from dateutil.parser import parse as parse_date
from dateutil.tz import tzlocal
import dogpile.cache
from jinja2 import Template
import pytz
import requests

from bugwarrior.config import schema, secrets

import logging
log = logging.getLogger(__name__)

DOGPILE_CACHE_PATH = os.path.expanduser(''.join([
    os.getenv('XDG_CACHE_HOME', '~/.cache'), '/dagd-py3.dbm']))

if not os.path.isdir(os.path.dirname(DOGPILE_CACHE_PATH)):
    os.makedirs(os.path.dirname(DOGPILE_CACHE_PATH))
CACHE_REGION = dogpile.cache.make_region().configure(
    "dogpile.cache.dbm",
    arguments=dict(filename=DOGPILE_CACHE_PATH),
)


class URLShortener:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(
                cls, *args, **kwargs
            )
        return cls._instance

    @CACHE_REGION.cache_on_arguments()
    def shorten(self, url):
        if not url:
            return ''
        base = 'https://da.gd/s'
        return requests.get(base, params=dict(url=url)).text.strip()


def get_processed_url(main_config: schema.MainSectionConfig, url: str):
    """ Returns a URL with conditional processing.

    If the following config key are set:

    - [general]shorten

    returns a shortened URL; otherwise returns the URL unaltered.

    """
    if main_config.shorten:
        return URLShortener().shorten(url)
    return url


class Service(abc.ABC):
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
            password = secrets.get_service_password(
                keyring_service, login, oracle=password,
                interactive=self.main_config.interactive)
        return password

    def get_issue_for_record(self, record, extra=None):
        return self.ISSUE_CLASS(
            record, self.config, self.main_config, extra=extra)

    def build_annotations(self, annotations, url=None):
        final = []
        if url and self.main_config.annotation_links:
            final.append(get_processed_url(self.main_config, url))
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
        """ Returns a list of Issue instances representing issues from a remote service.

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
        self.record = foreign_record
        self.config = config
        self.main_config = main_config
        self.extra = extra if extra else {}

    @abc.abstractmethod
    def to_taskwarrior(self):
        """ Transform a foreign record into a taskwarrior dictionary."""
        raise NotImplementedError()

    @abc.abstractmethod
    def get_default_description(self):
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

    def get_priority(self):
        return self.PRIORITY_MAP.get(
            self.record.get('priority'),
            self.config.default_priority
        )

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
        url = get_processed_url(self.main_config, url) if self.main_config.inline_links else ''
        desc_len = self.main_config.description_length
        return "(bw)%s#%s - %s%s%s" % (
            cls_markup.get(cls, cls.title()),
            number,
            title[:desc_len] if desc_len else title,
            url_separator if url else '',
            url,
        )


class Client:
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
