import contextlib
import typing
import unittest.mock

from pydantic import Field

from bugwarrior import config, services
from bugwarrior.collect import get_service_instances
from bugwarrior.config import validation
from bugwarrior.config.load import format_config
from bugwarrior.task import Task, Udas

from .services.base import get_mock_service


class DumbConfig(config.ServiceConfig):
    service: typing.Literal["test"] = "test"
    KEYRING_SERVICE = 'test://'

    import_labels_as_tags: bool = False
    label_template: str = "{{label}}"


class DumbUdas(Udas):
    UNIQUE_KEY = ("dumburl",)

    dumburl: str | None = Field(default=None, title="Dumb URL")
    dumbtype: str | None = Field(default=None, title="Dumb Type")


class DumbTask(Task):
    udas: DumbUdas


class DumbService(services.Service):
    API_VERSION = services.LATEST_API_VERSION
    UDAS_CLASS = DumbUdas
    CONFIG_SCHEMA = DumbConfig
    PRIORITY_MAP: dict = {}

    def to_taskwarrior(self, record, extra):
        return DumbTask(
            project=extra.get("project"),
            priority=self.config.default_priority,
            annotations=extra.get("annotations", []),
            tags=self.get_tags_from_labels(record, record.get("labels", [])),
            udas=DumbUdas(
                dumburl=record.get("url", ""),
                dumbtype=extra.get("type", "issue"),
            ),
        )

    def get_default_description(self, record):
        return self.build_default_description(
            title=record.get("title", ""),
            url=record.get("url", ""),
            number=record.get("number", ""),
        )

    def issues(self):
        raise NotImplementedError


def make_issue(general_overrides=None, config_overrides=None):
    service = get_mock_service(
        DumbService, config_overrides, general_overrides=general_overrides
    )
    return service.get_issue_for_record({})


#: Modules that import get_service by name and must be patched together so the
#: fake service resolves consistently across config loading, collection, and db.
_GET_SERVICE_MODULES = (
    'bugwarrior.config.schema',
    'bugwarrior.config.validation',
    'bugwarrior.config',
    'bugwarrior.db',
    'bugwarrior.collect',
)


@contextlib.contextmanager
def register_services(mapping=None):
    """
    Make fake services resolvable via get_service for the duration of a block.

    Patches get_service in every module that imports it so that orchestration
    code (config loading, collection, db) resolves the given name-to-class
    mapping instead of the real entry points. Defaults to mapping the "test"
    service to DumbService.
    """
    mapping = mapping or {'test': DumbService}

    def fake_get_service(name):
        try:
            return mapping[name]
        except KeyError:
            raise ValueError(
                f"Configured service '{name}' not found. "
                "Is it installed? Or misspelled?"
            )

    with contextlib.ExitStack() as stack:
        for module in _GET_SERVICE_MODULES:
            stack.enter_context(
                unittest.mock.patch(f'{module}.get_service', fake_get_service)
            )
        yield


def validate(config) -> validation.Config:
    formatted_config = format_config(config)
    return validation.validate_config(formatted_config, 'general', 'configpath')


def get_validated_service(config):
    return get_service_instances(validate(config))[0]
