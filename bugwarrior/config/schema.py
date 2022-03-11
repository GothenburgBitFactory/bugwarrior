import configparser
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
        ('gobject', 'growlnotify')]] = None
    finished_querying_sticky: bool = True
    task_crud_sticky: bool = True
    only_on_new_tasks: bool = False


class SchemaBase(pydantic.BaseSettings):
    Config = PydanticConfig

    DEFAULT: dict  # configparser feature

    hooks: Hooks = Hooks()
    notifications: Notifications = Notifications()


class ValidationErrorEnhancedMessages(list):
    """ Methods loosely adapted from pydantic.error_wrappers. """

    def __init__(self, error: pydantic.ValidationError, targets, main_section):
        self.targets: list = targets
        self.main_section: str = main_section
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
            if len(e['loc']) == 1:  # Error is in section
                if e['loc'][0] not in self.targets:
                    e['msg'] = (
                        f"Unrecognized section '{e['loc'][0]}'. Did you forget"
                        f" to add it to 'targets' in the [{self.main_section}]"
                        " section?")
            elif len(e['loc']) == 2:  # Error is in option
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
    # Construct Service Models
    try:
        targets = ConfigList.validate(config.get(main_section, 'targets'))
        target_schemas = {target: (
            get_service(config.get(target, 'service')).CONFIG_SCHEMA, ...)
            for target in targets}
    except configparser.NoSectionError as e:
        raise_validation_error(str(e), config_path)
    except configparser.NoOptionError as e:
        raise_validation_error(str(e), config_path)

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
        errors = ValidationErrorEnhancedMessages(e, targets, main_section)
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

    # Optional fields shared by all services.
    only_if_assigned: str = ''
    also_unassigned: bool = False
    # Although upstream supports it, pydantic has problems with Literal[None].
    default_priority: typing.Optional[
        typing_extensions.Literal['L', 'M', 'H']] = 'M'
    add_tags: ConfigList = ConfigList([])
    description_template: str = ''

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
