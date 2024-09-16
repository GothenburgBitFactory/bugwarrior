import logging
import os
import pathlib
import re
import sys
import typing

import pydantic.v1
import pydantic.v1.error_wrappers
import taskw
import typing_extensions

from bugwarrior.collect import get_service

from .data import BugwarriorData, get_data_path

log = logging.getLogger(__name__)


class StrippedTrailingSlashUrl(pydantic.v1.AnyUrl):

    @classmethod
    def validate(cls, value, field, config):
        return super().validate(value.rstrip('/'), field, config)


class UrlSchemeError(pydantic.v1.UrlSchemeError):
    msg_template = "URL should not include scheme ('{scheme}')"


class NoSchemeUrl(StrippedTrailingSlashUrl):

    @classmethod
    def validate_parts(
            cls, parts: typing.Dict[str, str]) -> typing.Dict[str, str]:
        scheme = parts['scheme']
        if scheme is not None:
            raise UrlSchemeError(scheme=scheme)

        port = parts['port']
        if port is not None and int(port) > 65_535:
            raise pydantic.v1.errors.UrlPortError()

        user = parts['user']
        if cls.user_required and user is None:
            raise pydantic.v1.errors.UrlUserInfoError()

        return parts


# Pydantic complicates the use of sets or lists as default values.
class ConfigList(frozenset):

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value):
        """ Cast ini string to a list of strings """
        try:
            return [
                item.strip() for item in re.split(",(?![^{]*})", value.strip())
                if item != '']
        except AttributeError:  # not a string, presumably an iterable
            return value


# HACK https://stackoverflow.com/a/34116756
class ExpandedPath(type(pathlib.Path())):  # type: ignore

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, path):
        return os.path.expanduser(os.path.expandvars(path))


class LoggingPath(ExpandedPath):

    @classmethod
    def validate(cls, path):
        return os.path.relpath(super().validate(path))


class TaskrcPath(ExpandedPath):

    @classmethod
    def validate(cls, path):
        expanded_path = super().validate(os.path.normpath(path))
        if not os.path.isfile(expanded_path):
            raise OSError(f"Unable to find taskrc file at {expanded_path}.")
        return expanded_path


class PydanticConfig(pydantic.v1.BaseConfig):
    allow_mutation = False  # config is faux-immutable
    extra = 'forbid'  # do not allow undeclared fields
    validate_all = True  # validate default fields


class MainSectionConfig(pydantic.v1.BaseModel):

    class Config(PydanticConfig):
        arbitrary_types_allowed = True

    # required
    targets: ConfigList

    # added during configuration loading
    interactive: bool

    # added during validation (computed field support will land in pydantic-2)
    data: typing.Optional[BugwarriorData] = None

    @pydantic.v1.root_validator
    def compute_data(cls, values):
        values['data'] = BugwarriorData(get_data_path(values['taskrc']))
        return values

    # optional
    taskrc: TaskrcPath = pydantic.v1.Field(
        default_factory=lambda: TaskrcPath(os.getenv('TASKRC', '~/.taskrc')))
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
    static_tags: ConfigList = ConfigList([])
    static_fields: ConfigList = ConfigList(['priority'])

    log_level: typing_extensions.Literal[
        ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'DISABLED')
    ] = 'INFO'
    log_file: typing.Optional[LoggingPath] = None


class Hooks(pydantic.v1.BaseModel):
    pre_import: ConfigList = ConfigList([])


class Notifications(pydantic.v1.BaseModel):
    notifications: bool = False
    # Although upstream supports it, pydantic has problems with Literal[None].
    backend: typing.Optional[typing_extensions.Literal[
        ('gobject', 'growlnotify', 'applescript')]] = None
    finished_querying_sticky: bool = True
    task_crud_sticky: bool = True
    only_on_new_tasks: bool = False


class SchemaBase(pydantic.v1.BaseSettings):
    class Config(PydanticConfig):
        # Allow extra top-level sections so all targets don't have to be selected.
        extra = 'ignore'

    hooks: Hooks = Hooks()
    notifications: Notifications = Notifications()


class ValidationErrorEnhancedMessages(list):
    """ Methods loosely adapted from pydantic.error_wrappers. """

    def __init__(self, error: pydantic.v1.ValidationError):
        super().__init__(self.flatten(error))

    def __str__(self):
        return '\n'.join(self)

    @staticmethod
    def display_error_loc(e):
        loc_len = len(e['loc'])
        if loc_len == 1 or e['loc'][1] == '__root__':
            return f"[{e['loc'][0]}]"
        elif loc_len == 2:
            # TODO We should be able to display the value itself:
            # https://github.com/samuelcolvin/pydantic/issues/784
            return f"[{e['loc'][0]}]\n{e['loc'][1]}"
        raise ValueError(
            'Configuration should not be nested more than two layers deep.')

    def display_error(self, e, error, model):
        if e['type'] == 'value_error.extra':
            e['msg'] = 'unrecognized option'
        return f'{self.display_error_loc(e)}  <- {e["msg"]}\n'

    def flatten(self, err, loc=None):
        for error in err.raw_errors:
            if isinstance(error, pydantic.v1.error_wrappers.ErrorWrapper):

                if loc:
                    error_loc = loc + error.loc_tuple()
                else:
                    error_loc = error.loc_tuple()

                if isinstance(error.exc, pydantic.v1.ValidationError):
                    yield from self.flatten(error.exc, error_loc)
                else:
                    e = pydantic.v1.error_wrappers.error_dict(
                        error.exc, PydanticConfig, error_loc)
                    yield self.display_error(e, error, err.model)
            elif isinstance(error, list):
                yield from self.flatten(error, loc=loc)
            else:
                raise RuntimeError(f'Unknown error object: {error}')


def raise_validation_error(msg, config_path, no_errors=1):
    log.error(
        ('Validation error' if no_errors == 1
         else f'{no_errors} validation errors') +
        f' found in {config_path}\n'
        f'See https://bugwarrior.readthedocs.io\n\n{msg}'
    )
    sys.exit(1)


def get_target_validator(targets):

    @pydantic.v1.root_validator(pre=True, allow_reuse=True)
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
        targets = ConfigList.validate(main['targets'])
    except KeyError:
        raise_validation_error(
            f"No option 'targets' in section: '{main_section}'", config_path)
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
                f"No option 'service' in section: '{target}'", config_path)

    # Construct Service Models
    target_schemas = {target: (get_service(service).CONFIG_SCHEMA, ...)
                      for target, service in servicemap.items()}

    # Construct Validation Model
    bugwarrior_config_model = pydantic.v1.create_model(
        'bugwarriorrc',
        __base__=SchemaBase,
        __validators__={'compute_target': get_target_validator(targets)},
        general=(MainSectionConfig, ...),
        flavor={flavor: (MainSectionConfig, ...)
                for flavor in config.get('flavor', {}).values()},
        **target_schemas)

    # Validate
    try:
        # Convert top-level model to dict since target names are dynamic and
        # a bunch of calls to getattr(config, target) inhibits readability.
        return dict(bugwarrior_config_model(**config))
    except pydantic.v1.ValidationError as e:
        errors = ValidationErrorEnhancedMessages(e)
        raise_validation_error(
            str(errors), config_path, no_errors=len(errors))


# Dynamically add template fields to model.
_ServiceConfig = pydantic.v1.create_model(
    '_ServiceConfig',
    **{f'{key}_template': (typing.Optional[str], None)
       for key in taskw.task.Task.FIELDS}
)


class ServiceConfig(_ServiceConfig):  # type: ignore  # (dynamic base class)
    """ Base class for service configurations. """
    Config = PydanticConfig

    # Added during validation (computed field support will land in pydantic-2)
    templates: dict = {}
    target: typing.Optional[str] = None

    # Optional fields shared by all services.
    only_if_assigned: str = ''
    also_unassigned: bool = False
    default_priority: typing_extensions.Literal['', 'L', 'M', 'H'] = 'M'
    add_tags: ConfigList = ConfigList([])
    description_template: typing.Optional[str] = None

    @pydantic.v1.root_validator
    def compute_templates(cls, values):
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
        for key in taskw.task.Task.FIELDS.keys():
            template = values.get(f'{key}_template')
            if template is not None:
                values['templates'][key] = template
        return values

    @pydantic.v1.root_validator
    def deprecate_filter_merge_requests(cls, values):
        if hasattr(cls, '_DEPRECATE_FILTER_MERGE_REQUESTS'):
            if values['filter_merge_requests'] != 'Undefined':
                if values['include_merge_requests'] != 'Undefined':
                    raise ValueError(
                        'filter_merge_requests and include_merge_requests are incompatible.')
                values['include_merge_requests'] = not values['filter_merge_requests']
                log.warning(
                    'filter_merge_requests is deprecated in favor of include_merge_requests')
            elif values['include_merge_requests'] == 'Undefined':
                values['include_merge_requests'] = True
        return values

    @pydantic.v1.root_validator
    def deprecate_project_name(cls, values):
        if hasattr(cls, '_DEPRECATE_PROJECT_NAME'):
            if values['project_name'] != '':
                log.warning('project_name is deprecated in favor of project_template')
        return values
