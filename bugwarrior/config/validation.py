import logging
import sys
import typing
from typing import TYPE_CHECKING, Annotated, Any, Union

import pydantic
from pydantic import Field, TypeAdapter
from pydantic_core import ErrorDetails

from bugwarrior.collect import get_service

from .schema import BaseConfig, Hooks, MainSectionConfig, Notifications, ServiceConfig

if TYPE_CHECKING:
    ServiceConfigType = ServiceConfig


log = logging.getLogger(__name__)


def _format_section_error(section: str | int, msg: str) -> str:
    return f"[{section}]  <- {msg}\n"


def _format_field_error(
    section: str | int, field: str | int, msg: str, error: ErrorDetails | dict
) -> str:
    formatted = f"[{section}]\n{field}"
    if error["type"] != "missing":
        formatted = f"{formatted} = {error['input']}"
    return f"{formatted}  <- {msg}\n"


def _format_service_error(error: ErrorDetails | dict) -> str:
    """Format validation error for service configs (discriminated union).

    loc structure:
    - (target,) - discriminator error (missing 'service')
    - (target, service_type) - model-level error
    - (target, service_type, '__root__') - model validator
    - (target, service_type, field) - field error
    """
    loc = error["loc"]
    msg = error["msg"]
    if error["type"] == "extra_forbidden":
        msg = "unrecognized option"

    target = loc[0]

    if len(loc) == 1:
        return _format_section_error(
            target, f"No option 'service' in section: '{target}'"
        )

    if len(loc) == 2 or loc[-1] == "__root__":
        return _format_section_error(target, msg)

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

    if len(loc) == 1 or loc[-1] == "__root__":
        return _format_section_error(flavor_name, msg)

    return _format_field_error(flavor_name, loc[1], msg, error)


def _format_simple_section_error(error: ErrorDetails | dict, section_name: str) -> str:
    """Format validation error for simple sections (hooks, notifications)."""
    loc = error["loc"]
    msg = error["msg"]
    if error["type"] == "extra_forbidden":
        msg = "unrecognized option"

    if not loc or loc[-1] == "__root__":
        return _format_section_error(section_name, msg)

    return _format_field_error(section_name, loc[0], msg, error)


def raise_validation_error(msg, config_path, error_count=1) -> typing.NoReturn:
    log.error(
        ("Validation error" if error_count == 1 else f"{error_count} validation errors")
        + f" found in {config_path}\n"
        f"See https://bugwarrior.readthedocs.io\n\n{msg}"
    )
    sys.exit(1)


def get_service_config_union_type(services: dict[str, dict[str, Any]]):
    service_config_classes = tuple(
        get_service(service["service"]).CONFIG_SCHEMA
        for service in services.values()
        if "service" in service
    )

    # Default to generic ServiceConfig if no service defined, mostly for tests
    if not service_config_classes:
        return ServiceConfig

    return Annotated[Union[service_config_classes], Field(discriminator="service")]


def validate_config(config: dict, main_section: str, config_path: str) -> "Config":
    error_messages: list[str] = []

    # Validate flavors
    flavors: dict[str, MainSectionConfig] = {}
    try:
        flavors = TypeAdapter(dict[str, MainSectionConfig]).validate_python(
            config.get("flavors", {})
        )
    except pydantic.ValidationError as error:
        error_messages.extend(_format_flavor_error(err) for err in error.errors())

    # Check for misquoted flavor sections (e.g., ["flavor.myflavor"] instead of [flavor.myflavor])
    services_config = config.get("services", {})
    misquoted_flavors = [name for name in services_config if name.startswith("flavor.")]
    for section in misquoted_flavors:
        error_messages.append(
            f'["{section}"]  <- Did you mean [{section}]?\n'
            "Use [flavor.name] (not quoted) to define a flavor.\n"
        )
        del services_config[section]

    # Validate service configs
    ServiceConfigType = get_service_config_union_type(services_config)
    service_configs: dict[str, ServiceConfigType] = {}
    try:
        service_configs = TypeAdapter(dict[str, ServiceConfigType]).validate_python(
            services_config
        )
    except pydantic.ValidationError as error:
        error_messages.extend(_format_service_error(err) for err in error.errors())

    # Validate hooks
    hooks = Hooks()
    try:
        hooks = TypeAdapter(Hooks).validate_python(config.get("hooks", {}))
    except pydantic.ValidationError as error:
        error_messages.extend(
            _format_simple_section_error(err, "hooks") for err in error.errors()
        )

    # Validate notifications
    notifications = Notifications()
    try:
        notifications = TypeAdapter(Notifications).validate_python(
            config.get("notifications", {})
        )
    except pydantic.ValidationError as error:
        error_messages.extend(
            _format_simple_section_error(err, "notifications") for err in error.errors()
        )

    # Check main_section exists in flavors
    if main_section not in flavors:
        error_messages.append(f"No section: '{main_section}'\n")

    # Check targets exist for all flavors
    available_targets = set(service_configs.keys())
    for flavor_name, flavor in flavors.items():
        missing = set(flavor.targets) - available_targets
        if missing:
            error_messages.append(
                f"[{flavor_name}] missing targets: {', '.join(sorted(missing))}\n"
            )

    if error_messages:
        raise_validation_error(
            "".join(error_messages), config_path, error_count=len(error_messages)
        )

    main = flavors[main_section]
    filtered_service_configs = [service_configs[target] for target in main.targets]

    return Config(
        service_configs=filtered_service_configs,
        main=main,
        hooks=hooks,
        notifications=notifications,
    )


class Config(BaseConfig):
    service_configs: list[ServiceConfig]
    main: MainSectionConfig
    hooks: Hooks = Hooks()
    notifications: Notifications = Notifications()
