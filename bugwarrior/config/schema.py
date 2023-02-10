import logging
import os
import pathlib
import re
import sys
import typing

import pydantic.error_wrappers
import taskw
import typing_extensions

from bugwarrior.services import get_service

from .data import BugwarriorData

log = logging.getLogger(__name__)


class StrippedTrailingSlashUrl(pydantic.AnyUrl):

    @classmethod
    def validate(cls, value, field, config):
        return super().validate(value.rstrip('/'), field, config)


class UrlSchemeError(pydantic.errors.UrlSchemeError):
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
            raise pydantic.errors.UrlPortError()

        user = parts['user']
        if cls.user_required and user is None:
            raise pydantic.errors.UrlUserInfoError()

        return parts


# Pydantic complicates the use of sets or lists as default values.
class ConfigList(frozenset):

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value):
        """ Cast config values to lists of strings """
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


class PydanticConfig(pydantic.BaseConfig):
    allow_mutation = False  # config is faux-immutable
    extra = 'forbid'  # do not allow undeclared fields
    validate_all = True  # validate default fields


class MainSectionConfig(pydantic.BaseModel):

    class Config(PydanticConfig):
        @staticmethod
        def alias_generator(string: str) -> str:
            """ Handle fields with a period in the name. """
            return string.replace('__', '.')

        # To set BugwarriorData based on taskrc:
        allow_mutation = True
        arbitrary_types_allowed = True

    # required
    targets: ConfigList

    # mutated after validation
    data: typing.Optional[BugwarriorData] = None
    interactive: typing.Optional[bool] = None

    # optional
    taskrc: TaskrcPath = pydantic.Field(
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

    # Fields with a period in the name (fixed by alias)
    log__level: typing_extensions.Literal[
        ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'DISABLED')
    ] = 'INFO'
    log__file: typing.Optional[LoggingPath] = None


class Hooks(pydantic.BaseModel):
    pre_import: ConfigList = ConfigList([])


class Notifications(pydantic.BaseModel):
    notifications: bool = False
    # Although upstream supports it, pydantic has problems with Literal[None].
    backend: typing.Optional[typing_extensions.Literal[
        ('gobject', 'growlnotify', 'applescript')]] = None
    finished_querying_sticky: bool = True
    task_crud_sticky: bool = True
    only_on_new_tasks: bool = False


class SchemaBase(pydantic.BaseSettings):
    class Config(PydanticConfig):
        # Allow extra top-level sections so all targets don't have to be selected.
        extra = 'ignore'

    DEFAULT: dict  # configparser feature

    hooks: Hooks = Hooks()
    notifications: Notifications = Notifications()


class ValidationErrorEnhancedMessages(list):
    """ Methods loosely adapted from pydantic.error_wrappers. """

    def __init__(self, error: pydantic.ValidationError):
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
            if len(e['loc']) == 2:  # Error is in option
                option = e['loc'][-1].split('.').pop()
                try:
                    scoped = f"{model._PREFIX}.{option}"
                except AttributeError:  # not a service model
                    pass
                else:
                    if scoped in model.schema()['properties'].keys():
                        e['msg'] = (f"expected prefix '{model._PREFIX}': "
                                    f"did you mean '{scoped}'?")
        return f'{self.display_error_loc(e)}  <- {e["msg"]}\n'

    def flatten(self, err, loc=None):
        for error in err.raw_errors:
            if isinstance(error, pydantic.error_wrappers.ErrorWrapper):

                if loc:
                    error_loc = loc + error.loc_tuple()
                else:
                    error_loc = error.loc_tuple()

                if isinstance(error.exc, pydantic.ValidationError):
                    yield from self.flatten(error.exc, error_loc)
                else:
                    e = pydantic.error_wrappers.error_dict(
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
        f'See https://bugwarrior-docs.readthedocs.io\n\n{msg}'
    )
    sys.exit(1)


def validate_config(config, main_section, config_path):
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
    bugwarrior_config_model = pydantic.create_model(
        'bugwarriorrc',
        __base__=SchemaBase,
        **{main_section: (MainSectionConfig, ...)},
        **target_schemas)

    # Validate
    try:
        # Convert top-level model to dict since target names are dynamic and
        # a bunch of calls to getattr(config, target) inhibits readability.
        return dict(bugwarrior_config_model(**config))
    except pydantic.ValidationError as e:
        errors = ValidationErrorEnhancedMessages(e)
        raise_validation_error(
            str(errors), config_path, no_errors=len(errors))


# Dynamically add template fields to model.
_ServiceConfig = pydantic.create_model(
    '_ServiceConfig',
    **{f'{key}_template': '' for key in taskw.task.Task.FIELDS}
)


class ServiceConfigMetaclass(pydantic.main.ModelMetaclass):
    """
    Dynamically insert alias_generator with prefix.

    Pydantic parses the schema in ModelMetaclass so we have to insert the
    alias prior to that.
    """
    def __new__(mcs, name, bases, namespace, prefix, **kwargs):
        if prefix is not None:

            class PydanticServiceConfig(PydanticConfig):
                @staticmethod
                def alias_generator(string: str) -> str:
                    """ Add prefixes. """
                    return (string if string == 'service'
                            else f'{prefix}.{string}')

            namespace['Config'] = PydanticServiceConfig
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        cls._PREFIX = prefix
        return cls


class ServiceConfig(_ServiceConfig,  # type: ignore  # (dynamic base class)
                    metaclass=ServiceConfigMetaclass, prefix=None):
    """ Base class for service configurations. """

    # added during validation (computed field support will land in pydantic-2)
    templates: dict = {}

    # Optional fields shared by all services.
    only_if_assigned: str = ''
    also_unassigned: bool = False
    default_priority: typing_extensions.Literal['', 'L', 'M', 'H'] = 'M'
    add_tags: ConfigList = ConfigList([])
    description_template: str = ''

    @pydantic.root_validator
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
            if template:
                values['templates'][key] = template
        return values

    @pydantic.root_validator
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

    @pydantic.root_validator
    def deprecate_project_name(cls, values):
        if hasattr(cls, '_DEPRECATE_PROJECT_NAME'):
            if values['project_name'] != '':
                log.warning('project_name is deprecated in favor of project_template')
        return values
