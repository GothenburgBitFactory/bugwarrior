"""
Service API
-----------
"""

import abc
from collections.abc import Iterable, Iterator
import logging
import math
import os
import re
from typing import TYPE_CHECKING, Any, Optional

import dogpile.cache
from jinja2 import Template
import requests

from bugwarrior.collect import CollectedIssue, make_unique_identifier
from bugwarrior.config import schema, secrets

if TYPE_CHECKING:
    from bugwarrior.task import Task, Udas

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
LATEST_API_VERSION = 2.0


class URLShortener:
    _instance = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "URLShortener":
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    @CACHE_REGION.cache_on_arguments()
    def shorten(self, url: str) -> str:
        if not url:
            return ''
        base = 'https://da.gd/s'
        return requests.get(base, params=dict(url=url)).text.strip()


def get_processed_url(main_config: schema.MainSectionConfig, url: str) -> str:
    """Returns a URL with conditional processing.

    If the following config key are set:

    - [general]shorten

    returns a shortened URL; otherwise returns the URL unaltered.

    """
    if main_config.shorten:
        return URLShortener().shorten(url)
    return url


class Service(abc.ABC):
    """Base class for fetching issues from the service.

    The upper case attributes and abstract methods need to be defined by
    service implementations, while the lower case attributes and concrete
    methods are provided by the base class.
    """

    #: Which version of the API does this service implement?
    API_VERSION: float
    #: Which Udas model declares this service's UDAs and unique key?
    UDAS_CLASS: type["Udas"]
    #: Which class defines this service's configuration options?
    CONFIG_SCHEMA: type[schema.ServiceConfig]
    #: Should be a dictionary of value-to-level mappings between the foreign
    #: system and the string values 'H', 'M' or 'L'.
    PRIORITY_MAP: dict

    def __init__(
        self, config: schema.ServiceConfig, main_config: schema.MainSectionConfig
    ) -> None:
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

    def get_secret(self, key: str, login: str = 'nousername') -> str:
        """Get a secret value, potentially from an :ref:`oracle <Secret Management>`.

        The secret key need not be a *password*, per se.

        :param `key`: Name of the configuration field of the given secret.
        :param `login`: Username associated with the password in a keyring, if
            applicable.
        """
        password = getattr(self.config, key)
        if not password or password.startswith("@oracle:"):
            password = secrets.get_service_password(
                self.config.keyring_service, login, oracle=password
            )
        return password

    def build_annotations(
        self, annotations: Iterable[tuple[str, str]], url: Optional[str] = None
    ) -> list[str]:
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
    def to_taskwarrior(self, record: dict[str, Any], extra: dict[str, Any]) -> "Task":
        """Transform a foreign record into a taskwarrior Task."""
        raise NotImplementedError()

    @abc.abstractmethod
    def get_default_description(self, record: dict[str, Any]) -> str:
        """Return a default description for this task.

        You should probably use :meth:`build_default_description` to achieve
        this.
        """
        raise NotImplementedError()

    def render_tags_from_labels(
        self, record: dict[str, Any], labels: list[str]
    ) -> list[str]:
        """Transform labels into suitable taskwarrior tags using the label template."""
        return [
            Template(self.config.label_template).render(
                {**record, "label": re.sub(r'[^a-zA-Z0-9]', '_', label)}
            )
            for label in labels
        ]

    def get_tags_from_labels(
        self,
        record: dict[str, Any],
        labels: list[str],
        toggle_option: str = 'import_labels_as_tags',
        template_option: str = 'label_template',
        template_variable: str = 'label',
    ) -> list[str]:
        """Transform labels into suitable taskwarrior tags, respecting configuration options."""
        using_deprecated_parameters = (
            toggle_option != 'import_labels_as_tags'
            or template_option != 'label_template'
            or template_variable != 'label'
        )
        if using_deprecated_parameters:
            log.warning(
                "Deprecation Warning: Issue.get_tags_from_labels's toggle_option, "
                "template_option, and template_variable parameters are deprecated and "
                "will be removed in a future API version."
            )

        if not getattr(self.config, toggle_option):
            return []

        if not using_deprecated_parameters:
            return self.render_tags_from_labels(record, labels)

        # deprecated path, to be removed once we remove the deprecated parameters.
        context = record.copy()
        label_template = Template(getattr(self.config, template_option))
        tags = []

        for label in labels:
            normalized_label = re.sub(r'[^a-zA-Z0-9]', '_', label)
            context.update({template_variable: normalized_label})
            tags.append(label_template.render(context))

        return tags

    def get_priority(self, record: dict[str, Any]) -> schema.Priority:
        """Return the priority of this issue, falling back to ``default_priority`` configuration."""
        return self.PRIORITY_MAP.get(
            record.get('priority'), self.config.default_priority
        )

    def build_default_description(
        self, title: str = '', url: str = '', number: str | int = '', cls: str = "issue"
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

    def _apply_templates(self, task: "Task", extra: dict[str, Any]) -> None:
        """Render the user's field and tag templates onto a mapped task.

        A field template overwrites whatever the service mapped for that field
        (including the default description); added tags are appended.
        """
        context = {**task.to_taskwarrior_data(), **extra}
        for field, template in self.config.templates.items():
            setattr(task, field, Template(template).render(context))

        for tag_template in self.config.add_tags:
            tag = Template(tag_template).render(context)
            if tag:
                task.tags.append(tag)

    def process_record(
        self, record: dict[str, Any], extra: dict[str, Any] | None = None
    ) -> CollectedIssue:
        """Map, refine and package a foreign record for synchronization.

        :param `record`: Foreign record.
        :param `extra`: Computed data which is not directly from the service.
        """
        extra = extra or {}
        task = self.to_taskwarrior(record, extra)
        task.description = self.get_default_description(record)
        self._apply_templates(task, extra)
        return CollectedIssue(
            task=task,
            identifier=make_unique_identifier(
                self.UDAS_CLASS.get_unique_key(), task.to_taskwarrior_data()
            ),
            target=self.config.target,
        )

    @abc.abstractmethod
    def issues(self) -> Iterator[CollectedIssue]:
        """Yield collected issues from a remote service.

        Fetch foreign records and pass each through :meth:`process_record`
        (which maps it to a typed Task, refines it, and packages it for
        synchronization).
        """
        raise NotImplementedError()


class Client:
    """Base class for making requests to service API's.

    This class is not strictly necessary but encourages a well-structured
    service in which the details of making and parsing http requests is
    compartmentalized.
    """

    @staticmethod
    def json_response(response: requests.Response) -> Any:
        """Return json if response is OK."""
        # If we didn't get good results, just bail.
        if response.status_code != 200:
            raise OSError(
                f"Non-200 status code {response.status_code}; {response.url}; {response.text}"
            )
        return response.json()


# NOTE: __all__ determines the stable, public API.
__all__ = [Client.__name__, Service.__name__]
