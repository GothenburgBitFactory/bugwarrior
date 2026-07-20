import functools
import importlib
import inspect
import logging
import re
import typing

from ini2toml.types import IntermediateRepr, Translator
import pydantic

from .schema import (
    Hooks,
    MainSectionConfig,
    Notifications,
    ServiceConfig,
    parse_config_list,
)

log = logging.getLogger(__name__)


def to_type(section: IntermediateRepr, key: str, converter: typing.Callable) -> None:
    try:
        val = section[key]
    except KeyError:
        pass
    else:
        section[key] = converter(val)


def to_bool(section: IntermediateRepr, key: str) -> None:
    to_type(section, key, pydantic.TypeAdapter(bool).validate_python)


def to_int(section: IntermediateRepr, key: str) -> None:
    to_type(section, key, int)


def to_list(section: IntermediateRepr, key: str) -> None:
    to_type(section, key, parse_config_list)


def get_field_type(attrs: dict) -> typing.Optional[str]:
    if 'type' in attrs:
        return attrs['type']
    if 'anyOf' in attrs:
        non_null_types = [
            option.get('type')
            for option in attrs['anyOf']
            if option.get('type') != 'null'
        ]
        if len(non_null_types) == 1:
            return non_null_types[0]
    return None


@functools.cache
def _schema_properties(schema: type[pydantic.BaseModel]) -> dict:
    # model_json_schema() rebuilds the schema from scratch on every call, and
    # this is invoked once per config example in the docs build (~150+
    # times), so cache it per schema class.
    return schema.model_json_schema()['properties']


def convert_section(
    section: IntermediateRepr, schema: type[pydantic.BaseModel]
) -> None:
    for prop, attrs in _schema_properties(schema).items():
        field_type = get_field_type(attrs)
        if field_type == 'boolean':
            to_bool(section, prop)
        elif field_type == 'integer':
            to_int(section, prop)
        elif field_type == 'array':
            to_list(section, prop)


@functools.cache
def _service_schema(service: str) -> type[ServiceConfig]:
    # Resolving a service's config class scans the module with
    # inspect.getmembers() on every call, and this is invoked once per
    # config example in the docs build (~150+ times), so cache it per
    # service name.
    module_name = {'bugzilla': 'bz', 'phabricator': 'phab'}.get(service, service)
    service_module = importlib.import_module(f'bugwarrior.services.{module_name}')
    for _, obj in inspect.getmembers(service_module, predicate=inspect.isclass):
        if issubclass(obj, ServiceConfig):
            return obj
    raise ValueError(f"ServiceConfig class not found in {service} module.")


def process_values(doc: IntermediateRepr) -> IntermediateRepr:
    for name, section in doc.items():
        if isinstance(name, str):
            if name == 'general' or re.match(r'^flavor\.', name):
                convert_section(section, MainSectionConfig)
                for k in ['log.level', 'log.file']:
                    if k in section:
                        section.rename(k, k.replace('.', '_'))
            elif name == 'hooks':
                convert_section(section, Hooks)
            elif name == 'notifications':
                convert_section(section, Notifications)
            else:  # services
                service = section['service']

                # Validate and strip prefixes.
                for key in section.keys():
                    if isinstance(key, str) and key != 'service':
                        prefix = 'ado' if service == 'azuredevops' else service
                        newkey, subs = re.subn(f'^{prefix}\\.', '', key)
                        if subs != 1:
                            option = key.split('.').pop()
                            log.warning(
                                f"[{name}]\n{key} <-expected prefix "
                                f"'{prefix}': did you mean "
                                f"'{prefix}.{option}'?"
                            )
                        section.rename(key, newkey)

                # Get Config
                schema = _service_schema(service)

                # Convert Types
                convert_section(section, schema)
                if service == 'gitlab' and 'verify_ssl' in section.keys():
                    try:
                        to_bool(section, 'verify_ssl')
                    except pydantic.ValidationError:
                        # verify_ssl is allowed to be a path
                        pass

    return doc


def unquote_flavors(file_contents: str) -> str:
    return re.sub(
        r'\n\["flavor\.(?P<flavor>[^"]*)"\]', r'\n[flavor.\g<flavor>]', file_contents
    )


def activate(translator: Translator) -> None:
    profile = translator["bugwarriorrc"]
    profile.help_text = "Convert 'bugwarriorrc' files to 'bugwarrior.toml'"
    profile.intermediate_processors.append(process_values)
    profile.post_processors.append(unquote_flavors)
