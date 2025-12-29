import logging
import os
from pathlib import Path
import re
import sys
import typing
from typing import Annotated, Any, Generic, Literal

import pydantic
from pydantic import (
    AfterValidator,
    AnyUrl,
    BeforeValidator,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationInfo,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError
import taskw

from bugwarrior.collect import get_service

from .data import BugwarriorData, get_data_path

log = logging.getLogger(__name__)


def validate_url(url: str):
    return str(AnyUrl(url)).rstrip("/")


StrippedTrailingSlashUrl = Annotated[str, BeforeValidator(validate_url)]


def validate_no_scheme_url(value: str) -> str:
    if "://" in value:
        scheme = value.split("://")[0]
        raise PydanticCustomError(
            "url_scheme_not_allowed",
            "URL should not include scheme ('{scheme}')",
            {"scheme": scheme},
        )

    return value.rstrip("/")


NoSchemeUrl = Annotated[str, BeforeValidator(validate_no_scheme_url)]


def parse_config_list(value: str | list[str]) -> list[str]:
    """Cast ini string to a list of strings."""
    if isinstance(value, str):
        return [
            item.strip()
            for item in re.split(r",(?![^{]*})", value.strip())
            if item != ""
        ]
    return value


ConfigList = Annotated[list[str], BeforeValidator(parse_config_list)]


ExpandedPath = Annotated[
    Path,
    BeforeValidator(os.path.expandvars),
    AfterValidator(lambda path: path.expanduser()),
]


def _validate_file_exists(path: Path) -> Path:
    """Validate that path points to an existing file."""
    resolved = path.resolve()
    if not resolved.is_file():
        raise PydanticCustomError(
            "file_not_found",
            "Unable to find taskrc file at {path}.",
            {"path": str(resolved)},
        )
    return resolved


TaskrcPath = Annotated[ExpandedPath, AfterValidator(_validate_file_exists)]


def get_default_taskrc() -> Path:
    """Mimic taskwarrior's logic for finding taskrc."""
    # Allow $TASKRC override.
    env_taskrc = os.getenv("TASKRC")
    if env_taskrc:
        path = Path(os.path.expandvars(env_taskrc)).expanduser()
        return _validate_file_exists(path)

    # Default to ~/.taskrc
    taskrc = Path.home() / ".taskrc"
    if taskrc.is_file():
        return taskrc

    # If no ~/.taskrc, use $XDG_CONFIG_HOME/task/taskrc if exists, or
    # ~/.config/task/taskrc if $XDG_CONFIG_HOME is unset
    xdg_config_home = os.getenv("XDG_CONFIG_HOME")
    if xdg_config_home:
        xdg_config_taskrc = Path(xdg_config_home) / "task" / "taskrc"
        if xdg_config_taskrc.is_file():
            return xdg_config_taskrc
    else:
        dotconfig_taskrc = Path.home() / ".config" / "task" / "taskrc"
        if dotconfig_taskrc.is_file():
            return dotconfig_taskrc.expanduser()

    raise OSError("Unable to find taskrc file. (Try running `task`.)")


T = typing.TypeVar("T")


def _validate_unsupported(value: T) -> T:
    if value:
        raise ValueError("Option is unsupported by service.")
    return value


class UnsupportedOption(Generic[T]):
    def __class_getitem__(cls, item: type) -> Any:
        return Annotated[item, AfterValidator(_validate_unsupported)]


class BaseConfig(pydantic.BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=True)


class MainSectionConfig(BaseConfig):
    """The :ref:`common_configuration:Main Section` configuration, plus computed attributes:"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # required
    targets: ConfigList

    # added during configuration loading
    #: Interactive status.
    interactive: bool = False

    @computed_field
    @property
    def data(self) -> BugwarriorData:
        """Local data storage."""
        return BugwarriorData(get_data_path(self.taskrc))

    # optional
    taskrc: TaskrcPath = Field(default_factory=get_default_taskrc)
    shorten: bool = False
    inline_links: bool = True
    annotation_links: bool = False
    annotation_comments: bool = True
    annotation_newlines: bool = False
    annotation_length: typing.Optional[int] = 45
    description_length: typing.Optional[int] = 35
    merge_annotations: bool = True
    merge_tags: bool = True
    replace_tags: bool = False
    static_tags: ConfigList = []
    static_fields: ConfigList = ["priority"]

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "DISABLED"] = (
        "INFO"
    )
    log_file: typing.Optional[ExpandedPath] = None


class Hooks(BaseConfig):
    pre_import: ConfigList = []


class Notifications(BaseConfig):
    notifications: bool = False
    backend: typing.Optional[Literal["gobject", "growlnotify", "applescript"]] = None
    finished_querying_sticky: bool = True
    task_crud_sticky: bool = True
    only_on_new_tasks: bool = False


class SchemaBase(BaseConfig):
    # Allow extra top-level sections so all targets don't have to be selected.
    model_config = ConfigDict(extra="ignore")

    hooks: Hooks = Hooks()
    notifications: Notifications = Notifications()


def get_validation_error_enhanced_messages(
    error: pydantic.ValidationError,
) -> list[str]:
    errors = []
    for _error in error.errors():
        msg = _error["msg"]
        if _error["type"] == "extra_forbidden":
            msg = "unrecognized option"
        loc = _error["loc"]
        loc_len = len(loc)

        if loc_len == 1 or (loc_len > 1 and loc[1] == "__root__"):
            formatted_error_loc = f"[{loc[0]}]"
        elif loc_len == 2:
            formatted_error_loc = f"[{loc[0]}]\n{loc[1]}"
            if _error["type"] != "missing":
                formatted_error_loc = f"{formatted_error_loc} = {_error['input']}"
        else:
            raise ValueError(
                "Configuration should not be nested more than two layers deep."
            )
        errors.append(f"{formatted_error_loc}  <- {msg}\n")
    return errors


def raise_validation_error(msg, config_path, no_errors=1) -> typing.NoReturn:
    log.error(
        ("Validation error" if no_errors == 1 else f"{no_errors} validation errors")
        + f" found in {config_path}\n"
        f"See https://bugwarrior.readthedocs.io\n\n{msg}"
    )
    sys.exit(1)


def get_target_validator(targets):
    @model_validator(mode='before')
    @classmethod
    def compute_target(cls, values):
        for target in targets:
            values[target]['target'] = target
        return values

    return compute_target


def validate_config(config: dict, main_section: str, config_path: str) -> dict:
    # Pre-validate the minimum requirements to build our pydantic models.
    try:
        main = config[main_section]
    except KeyError:
        raise_validation_error(f"No section: '{main_section}'", config_path)
    try:
        targets = TypeAdapter(ConfigList).validate_python(main['targets'])
    except KeyError:
        raise_validation_error(
            f"No option 'targets' in section: '{main_section}'", config_path
        )
    try:
        configmap = {target: config[target] for target in targets}
    except KeyError as e:
        raise_validation_error(f"No section: '{e.args[0]}'", config_path)
    servicemap = {}
    for target, serviceconfig in configmap.items():
        try:
            servicemap[target] = serviceconfig['service']
        except KeyError:
            raise_validation_error(
                f"No option 'service' in section: '{target}'", config_path
            )

    # Construct Service Models
    target_schemas = {
        target: (get_service(service).CONFIG_SCHEMA, ...)
        for target, service in servicemap.items()
    }

    # Construct Flavors
    flavor_schemas = {
        section: (MainSectionConfig, ...)
        for section in config.keys()
        if section.startswith('flavor.')
    }

    # Construct Validation Model
    bugwarrior_config_model = pydantic.create_model(
        'bugwarriorrc',
        __base__=SchemaBase,
        __validators__={'compute_target': get_target_validator(targets)},
        general=(MainSectionConfig, ...),
        **flavor_schemas,
        **target_schemas,
    )

    # Validate
    try:
        # Convert top-level model to dict since target names are dynamic and
        # a bunch of calls to getattr(config, target) inhibits readability.
        return dict(bugwarrior_config_model.model_validate(config))
    except pydantic.ValidationError as e:
        errors = get_validation_error_enhanced_messages(e)
        raise_validation_error("\n".join(errors), config_path, no_errors=len(errors))


# Dynamically add template fields to model.
_ServiceConfig = pydantic.create_model(
    "_ServiceConfig",
    __base__=BaseConfig,
    **{
        f"{key}_template": (typing.Optional[str], None)
        for key in taskw.task.Task.FIELDS
    },
)


class ServiceConfig(_ServiceConfig):
    """Pydantic_ base class for service configurations.

    .. _Pydantic: https://docs.pydantic.dev/latest/
    """

    # Added during validation (computed field)
    templates: dict = {}
    target: typing.Optional[str] = None

    # Optional fields shared by all services.
    only_if_assigned: str = ""
    also_unassigned: bool = False
    default_priority: Literal["", "L", "M", "H"] = "M"
    add_tags: ConfigList = []
    static_fields: ConfigList = []

    @model_validator(mode="before")
    @classmethod
    def compute_templates(cls, values):
        """Get any defined templates for configuration values.

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

        The above would cause all issues to receive a project name
        of 'myprojectname', regardless of what the project name of the
        generated issue was.

        """
        templates = {}
        for key in taskw.task.Task.FIELDS.keys():
            template = values.get(f'{key}_template')
            if template is not None:
                templates[key] = template
        values["templates"] = templates
        return values

    @field_validator('include_merge_requests', mode='after', check_fields=False)
    @classmethod
    def deprecate_filter_merge_requests(cls, value, info: ValidationInfo):
        if not hasattr(cls, '_DEPRECATE_FILTER_MERGE_REQUESTS'):
            return value

        filter_mr = info.data.get('filter_merge_requests', 'Undefined')
        if filter_mr != 'Undefined':
            if value != 'Undefined':
                raise ValueError(
                    'filter_merge_requests and include_merge_requests are incompatible.'
                )
            log.warning(
                'filter_merge_requests is deprecated in favor of include_merge_requests'
            )
            return not filter_mr
        elif value == 'Undefined':
            return True
        return value

    @field_validator('project_name', mode='after', check_fields=False)
    @classmethod
    def deprecate_project_name(cls, value):
        if hasattr(cls, '_DEPRECATE_PROJECT_NAME'):
            if value != '':
                log.warning('project_name is deprecated in favor of project_template')
        return value
