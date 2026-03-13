import logging
import sys
from typing import TYPE_CHECKING, Annotated, Any, NoReturn, Union

from pydantic import Field, TypeAdapter, ValidationError
from pydantic_core import ErrorDetails

from bugwarrior.collect import get_service

from .schema import BaseConfig, Hooks, MainSectionConfig, Notifications, ServiceConfig

if TYPE_CHECKING:
    ServiceConfigType = ServiceConfig


log = logging.getLogger(__name__)


def _format_section_error(section: str, msg: str) -> str:
    return f"[{section}]  <- {msg}\n"


def _format_field_error(
    section: str, field: str, msg: str, error: ErrorDetails | dict
) -> str:
    formatted = f"[{section}]\n{field}"
    if error["type"] != "missing":
        formatted = f"{formatted} = {error['input']}"
    return f"{formatted}  <- {msg}\n"


def _format_service_error(
    error: ErrorDetails | dict, services: list[dict[str, Any]]
) -> str:
    """Format validation error for service configs.

    loc structure:
    - (index,) - 'service' key is missing, can't determine which model to validate against
    - (index, service_type) - model-level error
    - (index, service_type, '__root__') - model validator
    - (index, service_type, field) - field error
    """
    loc = error["loc"]
    msg = error["msg"]
    if error["type"] == "extra_forbidden":
        msg = "unrecognized option"

    index = int(loc[0])
    target = services[index]["target"]

    if len(loc) == 1:
        return _format_section_error(
            target, f"No option 'service' in section: '{target}'"
        )

    if len(loc) == 2 or loc[-1] == "__root__":
        return _format_section_error(target, msg)

    assert isinstance(loc[2], str)
    return _format_field_error(target, loc[2], msg, error)


def _format_flavor_error(error: ErrorDetails | dict) -> str:
    """Format validation error for flavors.

    loc structure:
    - (flavor_name, '__root__') - model validator
    - (flavor_name, field) - field error
    """
    loc = error["loc"]
    msg = error["msg"]

    flavor_name = loc[0]
    assert isinstance(flavor_name, str)

    if len(loc) == 1:
        raise ValueError(f"Unexpected error loc with single element: {loc}")

    if loc[-1] == "__root__":
        return _format_section_error(flavor_name, msg)

    assert isinstance(loc[1], str)
    return _format_field_error(flavor_name, loc[1], msg, error)


def _format_extra_section_error(error: ErrorDetails | dict) -> str:
    """Format validation error for extra options (hooks, notifications).

    loc structure:
    - (section_name, field) - field error
    - (section_name, '__root__') - model validator
    """
    loc = error["loc"]
    msg = error["msg"]
    if error["type"] == "extra_forbidden":
        msg = "unrecognized option"

    section_name = str(loc[0])

    if len(loc) == 1:
        raise ValueError(f"Unexpected error loc with single element: {loc}")

    if loc[-1] == "__root__":
        return _format_section_error(section_name, msg)

    assert isinstance(loc[1], str)
    return _format_field_error(section_name, loc[1], msg, error)


def raise_validation_error(msg, config_path, error_count=1) -> NoReturn:
    log.error(
        ("Validation error" if error_count == 1 else f"{error_count} validation errors")
        + f" found in {config_path}\n"
        f"See https://bugwarrior.readthedocs.io\n\n{msg}"
    )
    sys.exit(1)


def get_service_config_union_type(services: list[dict[str, Any]]):
    """
    Return a Union type of the ServiceConfig subclasses of the services actually configured.

    We don't want to include all available services because each service must be imported
    which could have side-effects.

    The returned type takes advantaged of Pydantic's "Discriminated Unions" feature
    to ensure that each service configuration is validated against
    the ServiceConfig corresponding to the correct service.
    """
    service_config_classes = tuple(
        get_service(service["service"]).CONFIG_SCHEMA
        for service in services
        if "service" in service
    )

    # Default to generic ServiceConfig if no service defined, mostly for tests
    if not service_config_classes:
        return ServiceConfig

    return Annotated[Union[service_config_classes], Field(discriminator="service")]


def validate_config(config: dict, main_section: str, config_path: str) -> "Config":
    error_messages: list[str] = []
    raw_flavors = config.pop("flavor", {})
    # Validate flavors
    try:
        flavors = TypeAdapter(dict[str, MainSectionConfig]).validate_python(raw_flavors)
    except ValidationError as error:
        flavors = {}
        error_messages.extend(_format_flavor_error(err) for err in error.errors())

    # Check for misquoted flavor sections (e.g., ["flavor.myflavor"] instead of [flavor.myflavor])
    raw_service_configs = []
    for service in config.pop("services", []):
        target = service["target"]
        if target.startswith("flavor."):
            error_messages.append(
                f'["{target}"]  <- Did you mean [{target}]?\n'
                "Use [flavor.name] (not quoted) to define a flavor.\n"
            )
        else:
            raw_service_configs.append(service)

    # Validate service configs
    ServiceConfigType = get_service_config_union_type(raw_service_configs)
    try:
        service_configs = TypeAdapter(list[ServiceConfigType]).validate_python(
            raw_service_configs
        )
    except ValidationError as error:
        error_messages.extend(
            _format_service_error(err, raw_service_configs) for err in error.errors()
        )
        service_configs = []

    # Check main_section exists in flavors
    if main_section not in raw_flavors:
        error_messages.append(f"No section: '{main_section}'\n")

    # Check targets exist for all flavors
    available_targets = {
        service_config["target"] for service_config in raw_service_configs
    }
    for flavor_name, flavor in flavors.items():
        missing = sorted(set(flavor.targets) - available_targets)
        for target in missing:
            error_messages.append(
                f"[{flavor_name}]\ntargets = {flavor.targets}  <- No [{target}] section found\n"
            )

    main = flavors.get(main_section, MainSectionConfig(targets=[]))
    filtered_service_configs = [
        service_config
        for service_config in service_configs
        if service_config.target in main.targets
    ]

    try:
        _config = Config(service_configs=filtered_service_configs, main=main, **config)
    except ValidationError as error:
        error_messages.extend(
            _format_extra_section_error(err) for err in error.errors()
        )

    if error_messages:
        raise_validation_error(
            "".join(error_messages), config_path, error_count=len(error_messages)
        )
    return _config


class Config(BaseConfig):
    service_configs: list[ServiceConfig]
    main: MainSectionConfig
    hooks: Hooks = Hooks()
    notifications: Notifications = Notifications()
