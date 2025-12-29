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


def to_type(section: IntermediateRepr, key: str, converter: typing.Callable):
    try:
        val = section[key]
    except KeyError:
        pass
    else:
        section[key] = converter(val)


def to_bool(section: IntermediateRepr, key: str):
    to_type(section, key, pydantic.TypeAdapter(bool).validate_python)


def to_int(section: IntermediateRepr, key: str):
    to_type(section, key, int)


def to_list(section: IntermediateRepr, key: str):
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


def convert_section(section: IntermediateRepr, schema: type[pydantic.BaseModel]):
    for prop, attrs in schema.model_json_schema()['properties'].items():
        field_type = get_field_type(attrs)
        if field_type == 'boolean':
            to_bool(section, prop)
        elif field_type == 'integer':
            to_int(section, prop)
        elif field_type == 'array':
            to_list(section, prop)


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
                module_name = {'bugzilla': 'bz', 'phabricator': 'phab'}.get(
                    service, service
                )
                service_module = importlib.import_module(
                    f'bugwarrior.services.{module_name}'
                )
                for name, obj in inspect.getmembers(
                    service_module, predicate=inspect.isclass
                ):
                    if issubclass(obj, ServiceConfig):
                        schema = obj
                        break
                else:
                    raise ValueError(
                        f"ServiceConfig class not found in {service} module."
                    )

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


def activate(translator: Translator):
    profile = translator["bugwarriorrc"]
    profile.description = "Convert 'bugwarriorrc' files to 'bugwarrior.toml'"
    profile.intermediate_processors.append(process_values)
    profile.post_processors.append(unquote_flavors)
