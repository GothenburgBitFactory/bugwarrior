import abc
import copy
import multiprocessing
import time

from pkg_resources import iter_entry_points

from dateutil.parser import parse as parse_date
from dateutil.tz import tzlocal
from jinja2 import Template
import pytz

from taskw.task import Task

from bugwarrior.config.secrets import get_service_password
from bugwarrior.db import MARKUP, URLShortener

import logging
log = logging.getLogger(__name__)


# Sentinels for process completion status
SERVICE_FINISHED_OK = 0
SERVICE_FINISHED_ERROR = 1

# Used by `parse_date` as a timezone when you would like a naive
# date string to be parsed as if it were in your local timezone
LOCAL_TIMEZONE = 'LOCAL_TIMEZONE'


def get_service(service_name):
    epoint = iter_entry_points(group='bugwarrior.service', name=service_name)
    try:
        epoint = next(epoint)
    except StopIteration:
        return None

    return epoint.load()


class IssueService(abc.ABC):
    """ Abstract base class for each service """
    # Which class should this service instantiate for holding these issues?
    ISSUE_CLASS = None
    # Which class defines this service's configuration options?
    CONFIG_SCHEMA = None

    def __init__(self, config, main_config, target):
        self.config = config
        self.main_config = main_config
        self.target = target

        log.info("Working on [%s]", self.target)

    def get_templates(self):
        """ Get any defined templates for configuration values.

        Users can override the value of any Taskwarrior field using
        this feature on a per-key basis.  The key should be the name of
        the field to you would like to configure the value of, followed
        by '_template', and the value should be a Jinja template
        generating the field's value.  As context variables, all fields
        on the taskwarrior record are available.

        For example, to prefix the returned
        project name for tickets returned by a service with 'workproject_',
        you could add an entry reading:

            project_template = workproject_{{project}}

        Or, if you'd simply like to override the returned project name
        for all tickets incoming from a specific service, you could add
        an entry like:

            project_template = myprojectname

        The above would cause all issues to recieve a project name
        of 'myprojectname', regardless of what the project name of the
        generated issue was.

        """
        templates = {}
        for key in Task.FIELDS.keys():
            template = getattr(self.config, f'{key}_template')
            if template:
                templates[key] = template
        return templates

    def get_password(self, key, login='nousername'):
        password = getattr(self.config, key)
        keyring_service = self.get_keyring_service(self.config)
        if not password or password.startswith("@oracle:"):
            password = get_service_password(
                keyring_service, login, oracle=password,
                interactive=self.main_config.interactive)
        return password

    def get_service_metadata(self):
        return {}

    def get_issue_for_record(self, record, extra=None):
        origin = {
            'annotation_length': self.main_config.annotation_length,
            'default_priority': self.config.default_priority,
            'description_length': self.main_config.description_length,
            'templates': self.get_templates(),
            'target': self.target,
            'shorten': self.main_config.shorten,
            'inline_links': self.main_config.inline_links,
            'add_tags': self.config.add_tags,
            'static_fields': self.config.static_fields,
        }
        origin.update(self.get_service_metadata())
        return self.ISSUE_CLASS(record, origin=origin, extra=extra)

    def build_annotations(self, annotations, url):
        final = []
        if self.main_config.annotation_links:
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

    def get_author(self, issue):
        """ Override this for filtering on tickets """
        raise NotImplementedError()

    @abc.abstractmethod
    def issues(self):
        """ Returns a list of dicts representing issues from a remote service.

        This is the main place to begin if you are implementing a new service
        for bugwarrior.  Override this to gather issues for each service.

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

    def __init__(self, foreign_record, origin=None, extra=None):
        self._foreign_record = foreign_record
        self._origin = origin if origin else {}
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

    def get_added_tags(self):
        added_tags = []
        for tag in self.origin['add_tags']:
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
            self.origin['default_priority']
        )

    def get_processed_url(self, url):
        """ Returns a URL with conditional processing.

        If the following config key are set:

        - [general]shorten

        returns a shortened URL; otherwise returns the URL unaltered.

        """
        if self.origin['shorten']:
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
                if timezone == LOCAL_TIMEZONE:
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
        url = url if self.origin['inline_links'] else ''
        desc_len = self.origin['description_length']
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
            if field in self.origin['templates']:
                template = Template(self.origin['templates'][field])
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

    @property
    def origin(self):
        return self._origin

    def __str__(self):
        return '%s: %s' % (
            self.origin['target'],
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


def _aggregate_issues(conf, main_section, target, queue):
    """ This worker function is separated out from the main
    :func:`aggregate_issues` func only so that we can use multiprocessing
    on it for speed reasons.
    """

    start = time.time()

    try:
        service = get_service(conf[target].service)(
            conf[target], conf[main_section], target)
        issue_count = 0
        for issue in service.issues():
            queue.put(issue)
            issue_count += 1
    except SystemExit as e:
        log.critical(str(e))
        queue.put((SERVICE_FINISHED_ERROR, (target, e)))
    except BaseException as e:
        if hasattr(e, 'request') and e.request:
            # Exceptions raised by requests library have the HTTP request
            # object stored as attribute. The request can have hooks attached
            # to it, and we need to remove them, as there can be unpickleable
            # methods. There is no one left to call these hooks anyway.
            e.request.hooks = {}
        log.exception("Worker for [%s] failed: %s" % (target, e))
        queue.put((SERVICE_FINISHED_ERROR, (target, e)))
    else:
        queue.put((SERVICE_FINISHED_OK, (target, issue_count, )))
    finally:
        duration = time.time() - start
        log.info("Done with [%s] in %fs" % (target, duration))


def aggregate_issues(conf, main_section, debug):
    """ Return all issues from every target. """
    log.info("Starting to aggregate remote issues.")

    # Create and call service objects for every target in the config
    targets = conf[main_section].targets

    queue = multiprocessing.Queue()

    log.info("Spawning %i workers." % len(targets))

    if debug:
        for target in targets:
            _aggregate_issues(conf, main_section, target, queue)
    else:
        for target in targets:
            proc = multiprocessing.Process(
                target=_aggregate_issues,
                args=(conf, main_section, target, queue)
            )
            proc.start()

            # Sleep for 1 second here to try and avoid a race condition where
            # all N workers start up and ask the gpg-agent process for
            # information at the same time.  This causes gpg-agent to fumble
            # and tell some of our workers some incomplete things.
            time.sleep(1)

    currently_running = len(targets)
    while currently_running > 0:
        issue = queue.get(True)
        if isinstance(issue, tuple):
            completion_type, args = issue
            if completion_type == SERVICE_FINISHED_ERROR:
                target, e = args
                log.exception(f"Aborted {target} due to critical error.")
                currently_running -= 1
                yield ('SERVICE FAILED', target)
            currently_running -= 1
            continue
        yield issue

    log.info("Done aggregating remote issues.")
