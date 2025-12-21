"""
Service API
-----------
"""

import abc
import datetime
import logging
import math
import os
import re
import typing
import zoneinfo

from dateutil.parser import parse as parse_date
import dogpile.cache
from jinja2 import Template
import requests

from bugwarrior.config import schema, secrets

log = logging.getLogger(__name__)

DOGPILE_CACHE_PATH = os.path.expanduser(
    ''.join([os.getenv('XDG_CACHE_HOME', '~/.cache'), '/dagd-py3.dbm'])
)

if not os.path.isdir(os.path.dirname(DOGPILE_CACHE_PATH)):
    os.makedirs(os.path.dirname(DOGPILE_CACHE_PATH))
CACHE_REGION = dogpile.cache.make_region().configure(
    "dogpile.cache.dbm", arguments=dict(filename=DOGPILE_CACHE_PATH)
)

# MAJOR versions signal a breakage in backwards compatibility between services
# and previous releases of bugwarrior. That is, services implementing the new
# spec will cause breakages with older bugwarrior releases.
# MINOR versions signal extensions of the spec which enhance future releases of
# bugwarrior without breaking past releases.
LATEST_API_VERSION = 1.0


class URLShortener:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    @CACHE_REGION.cache_on_arguments()
    def shorten(self, url):
        if not url:
            return ''
        base = 'https://da.gd/s'
        return requests.get(base, params=dict(url=url)).text.strip()


def get_processed_url(main_config: schema.MainSectionConfig, url: str):
    """Returns a URL with conditional processing.

    If the following config key are set:

    - [general]shorten

    returns a shortened URL; otherwise returns the URL unaltered.

    """
    if main_config.shorten:
        return URLShortener().shorten(url)
    return url


class Issue(abc.ABC):
    """Base class for translating from foreign records to taskwarrior tasks.

    The upper case attributes and abstract methods need to be defined by
    service implementations, while the lower case attributes and concrete
    methods are provided by the base class.
    """

    #: Set to a dictionary mapping UDA short names with type and long name.
    #:
    #: Example::
    #:
    #:     {
    #:         'project_id': {
    #:             'type': 'string',
    #:             'label': 'Project ID',
    #:         },
    #:         'ticket_number': {
    #:             'type': 'number',
    #:             'label': 'Ticket Number',
    #:         },
    #:     }
    #:
    #: Note: For best results, dictionary keys should be unique!
    UDAS: dict
    #: Should be a tuple of field names (can be UDA names) that are usable for
    #: uniquely identifying an issue in the foreign system.
    UNIQUE_KEY: tuple[str, ...]
    #: Should be a dictionary of value-to-level mappings between the foreign
    #: system and the string values 'H', 'M' or 'L'.
    PRIORITY_MAP: dict

    def __init__(
        self,
        foreign_record: dict,
        config: schema.ServiceConfig,
        main_config: schema.MainSectionConfig,
        extra: dict,
    ):
        #: Data retrieved from the external service.
        self.record: dict = foreign_record
        #: An object whose attributes are this service's configuration values.
        self.config: schema.ServiceConfig = config
        #: An object whose attributes are the
        #: :ref:`common_configuration:Main Section` configuration values.
        self.main_config: schema.MainSectionConfig = main_config
        #: Data computed by the :class:`Service` class.
        self.extra: dict = extra

    @abc.abstractmethod
    def to_taskwarrior(self) -> dict:
        """Transform a foreign record into a taskwarrior dictionary."""
        raise NotImplementedError()

    @abc.abstractmethod
    def get_default_description(self) -> str:
        """Return a default description for this task.

        You should probably use :meth:`build_default_description` to achieve
        this.
        """
        raise NotImplementedError()

    def get_tags_from_labels(
        self,
        labels: list,
        toggle_option='import_labels_as_tags',
        template_option='label_template',
        template_variable='label',
    ) -> list[str]:
        """Transform labels into suitable taskwarrior tags, respecting configuration options.

        :param `labels`: Returned from the service.
        :param `toggle_option`: Option which, if false, would not import labels as tags.
        :param `template_option`: Configuration to use as the
            :ref:`field template<common_configuration:Field Templates>` for each label.
        :param `template_variable`: Name to use in the
            :ref:`field template<common_configuration:Field Templates>` context to refer to the
            label.
        """
        tags: list[str] = []

        if not getattr(self.config, toggle_option):
            return tags

        context = self.record.copy()
        label_template = Template(getattr(self.config, template_option))

        for label in labels:
            normalized_label = re.sub(r'[^a-zA-Z0-9]', '_', label)
            context.update({template_variable: normalized_label})
            tags.append(label_template.render(context))

        return tags

    def get_priority(self) -> typing.Literal['', 'L', 'M', 'H']:
        """Return the priority of this issue, falling back to ``default_priority`` configuration."""
        return self.PRIORITY_MAP.get(
            self.record.get('priority'), self.config.default_priority
        )

    def parse_date(
        self, date: str | None, timezone='deprecated'
    ) -> datetime.datetime | None:
        """Parse a date string into a datetime object.

        If the parsed date does not have a timezone, the UTC timezone is added.

        :param `date`: A time string parseable by `dateutil.parser.parse`
        """
        if timezone != 'deprecated':
            log.warning(
                "Deprecation Warning: Issue.parse_date's timezone parameter is deprecated and will "
                "be removed in a future API version."
            )

        if not date:
            return None

        _date = parse_date(date)
        if not _date.tzinfo:
            _date = _date.replace(
                tzinfo=datetime.timezone.utc
                if timezone == 'deprecated'
                else zoneinfo.ZoneInfo(timezone)
            )

        return _date.replace(microsecond=0)

    def build_default_description(
        self, title='', url='', number='', cls="issue"
    ) -> str:
        """Return a default description, respecting configuration options.

        :param `title`: Short description of the task.
        :param `url`: URL to the task on the service.
        :param `number`: Number associated with the task on the service.
        :param `cls`: The abbreviated type of task this is. Preferred options
            are ('issue', 'pull_request', 'merge_request', 'todo', 'task',
            'subtask').
        """
        cls_markup = {
            'issue': 'Is',
            'pull_request': 'PR',
            'merge_request': 'MR',
            'todo': '',
            'task': '',
            'subtask': 'Subtask #',
        }
        url_separator = ' .. '
        url = (
            get_processed_url(self.main_config, url)
            if self.main_config.inline_links
            else ''
        )
        desc_len = self.main_config.description_length
        return "(bw)%s#%s - %s%s%s" % (
            cls_markup.get(cls, cls.title()),
            number,
            title[:desc_len] if desc_len else title,
            url_separator if url else '',
            url,
        )


class Service(abc.ABC):
    """Base class for fetching issues from the service.

    The upper case attributes and abstract methods need to be defined by
    service implementations, while the lower case attributes and concrete
    methods are provided by the base class.
    """

    #: Which version of the API does this service implement?
    API_VERSION: float
    #: Which class should this service instantiate for holding these issues?
    ISSUE_CLASS: type[Issue]
    #: Which class defines this service's configuration options?
    CONFIG_SCHEMA: type[schema.ServiceConfig]

    def __init__(
        self, config: schema.ServiceConfig, main_config: schema.MainSectionConfig
    ):
        over_version = math.floor(LATEST_API_VERSION) + 1
        if self.API_VERSION >= over_version:
            raise ValueError(
                f"Incompatible Service: {config.service} implements api "
                f"version {self.API_VERSION} but this version of bugwarrior "
                f"only supports versions less than {over_version}."
            )

        #: An object whose attributes are this service's configuration values.
        self.config = config
        #: An object whose attributes are the
        #: :ref:`common_configuration:Main Section` configuration values.
        self.main_config = main_config

        log.info("Working on [%s]", self.config.target)

    def get_secret(self, key, login='nousername') -> str:
        """Get a secret value, potentially from an :ref:`oracle <Secret Management>`.

        The secret key need not be a *password*, per se.

        :param `key`: Name of the configuration field of the given secret.
        :param `login`: Username associated with the password in a keyring, if
            applicable.
        """
        password = getattr(self.config, key)
        keyring_service = self.get_keyring_service(self.config)
        if not password or password.startswith("@oracle:"):
            password = secrets.get_service_password(
                keyring_service,
                login,
                oracle=password,
                interactive=self.main_config.interactive,
            )
        return password

    def get_issue_for_record(self, record, extra=None) -> Issue:
        """Instantiate and return an issue for the given record.

        :param `record`: Foreign record.
        :param `extra`: Computed data which is not directly from the service.
        """
        extra = extra if extra is not None else {}
        return self.ISSUE_CLASS(record, self.config, self.main_config, extra=extra)

    def build_annotations(
        self, annotations: list, url: typing.Optional[str] = None
    ) -> list:
        """Format annotations, respecting configuration values.

        :param `annotations`: Comments from service.
        :param `url`: Url to prepend to the annotations.
        """
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
                        '...' if len(message) > annotation_length else '',
                    )
                final.append('@%s - %s' % (author, message))
        return final

    @abc.abstractmethod
    def issues(self):
        """A generator yielding Issue instances representing issues from a remote service.

        Each item in the list should be a dict that looks something like this:

        .. code-block:: python

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
    @abc.abstractmethod
    def get_keyring_service(service_config) -> str:
        """Return the keyring name for this service."""
        raise NotImplementedError


class Client:
    """Base class for making requests to service API's.

    This class is not strictly necessary but encourages a well-structured
    service in which the details of making and parsing http requests is
    compartmentalized.
    """

    @staticmethod
    def json_response(response: requests.Response):
        """Return json if response is OK."""
        # If we didn't get good results, just bail.
        if response.status_code != 200:
            raise OSError(
                "Non-200 status code %r; %r; %r"
                % (response.status_code, response.url, response.text)
            )
        if callable(response.json):
            # Newer python-requests
            return response.json()
        else:
            # Older python-requests
            return response.json


# NOTE: __all__ determines the stable, public API.
__all__ = [Client.__name__, Issue.__name__, Service.__name__]
