import configparser
import logging
import os
from pathlib import Path
import tomllib
from typing import Any

from .validation import Config, validate_config

# The name of the environment variable that can be used to ovewrite the path
# to the bugwarriorrc file
BUGWARRIORRC = "BUGWARRIORRC"


def configure_logging(logfile: str | Path | None, loglevel: str) -> None:
    logging.basicConfig(filename=logfile, level=loglevel)

    # In general, its nice to log "everything", but some of the loggers from
    # our dependencies are very very spammy.  Here, we silence most of their
    # noise:
    spammers = [
        'bugzilla.base',
        'bugzilla.bug',
        'requests.packages.urllib3.connectionpool',
    ]
    for spammer in spammers:
        logging.getLogger(spammer).setLevel(logging.WARNING)


def get_config_path() -> str:
    """Determine path to config file. See docs/manpage.rst for precedence."""
    if os.environ.get(BUGWARRIORRC):
        return os.environ[BUGWARRIORRC]
    xdg_config_home = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser(
        '~/.config'
    )
    xdg_config_dirs = (os.environ.get('XDG_CONFIG_DIRS') or '/etc/xdg').split(':')
    paths = [
        os.path.join(xdg_config_home, 'bugwarrior', 'bugwarriorrc'),
        os.path.join(xdg_config_home, 'bugwarrior', 'bugwarrior.toml'),
        os.path.expanduser("~/.bugwarriorrc"),
        os.path.expanduser("~/.bugwarrior.toml"),
    ]
    paths += [os.path.join(d, 'bugwarrior', 'bugwarriorrc') for d in xdg_config_dirs]
    paths += [os.path.join(d, 'bugwarrior', 'bugwarrior.toml') for d in xdg_config_dirs]
    for path in paths:
        if os.path.exists(path):
            return path
    return paths[0]


def format_config(config: dict) -> dict[str, Any]:
    config = config.copy()
    formatted: dict[str, Any] = {}
    if "flavor" in config:
        formatted["flavor"] = {**config.pop("flavor")}
    if "general" in config:
        formatted.setdefault("flavor", {})["general"] = config.pop("general")
    for key in ("hooks", "notifications"):
        if key in config:
            formatted[key] = config.pop(key)
    formatted["services"] = [
        {**config.pop(section), "target": section} for section in list(config)
    ]
    return formatted


def parse_toml_file(configpath: str) -> dict[str, Any]:
    with open(configpath, 'rb') as file:
        return tomllib.load(file)


def parse_ini_file(configpath: str) -> dict[str, Any]:
    rawconfig = BugwarriorConfigParser()
    with open(configpath, encoding="utf-8") as buff:
        rawconfig.read_file(buff)

    config = {"flavor": {}}
    for section in rawconfig.sections():
        if section in ['hooks', 'notifications']:
            config[section] = dict(rawconfig[section])
        elif section == 'general' or section.startswith('flavor.'):
            name = section.removeprefix('flavor.')
            config["flavor"][name] = {
                key.replace('.', '_'): value
                for key, value in rawconfig[section].items()
            }

        # All other sections are assumed to be services
        else:
            service = rawconfig[section].pop('service')
            service_prefix = 'ado' if service == 'azuredevops' else service
            config[section] = {'service': service}
            for key, value in rawconfig[section].items():
                try:
                    prefix, unprefixed_key = key.split('.')
                except ValueError:  # missing prefix
                    prefix = None
                    unprefixed_key = key
                if prefix != service_prefix:
                    raise SystemExit(
                        f"[{section}]\n{key} <-expected prefix "
                        f"'{service_prefix}': did you mean "
                        f"'{service_prefix}.{unprefixed_key}'?"
                    )
                config[section][unprefixed_key] = value

    return config


def parse_file(configpath: str) -> dict[str, Any]:
    if Path(configpath).suffix == '.toml':
        config = parse_toml_file(configpath)
    else:
        config = parse_ini_file(configpath)
    return format_config(config)


def load_config(main_section: str, quiet: bool) -> Config:
    configpath = get_config_path()
    rawconfig = parse_file(configpath)
    config = validate_config(rawconfig, main_section, configpath)
    configure_logging(
        config.main.log_file, 'WARNING' if quiet else config.main.log_level
    )
    return config


# ConfigParser is not a new-style class, so inherit from object to fix super().
class BugwarriorConfigParser(configparser.ConfigParser):
    def __init__(self, *args: Any, allow_no_value: bool = True, **kwargs: Any) -> None:
        super().__init__(
            *args, allow_no_value=allow_no_value, interpolation=None, **kwargs
        )

    def getint(self, section: str, option: str, **kwargs: Any) -> int | None:  # ty: ignore[invalid-method-override]
        """Accepts both integers and empty values."""
        try:
            return super().getint(section, option, **kwargs)
        except ValueError:
            if self.get(section, option) == '':
                return None
            else:
                raise ValueError(f"{section}.{option} must be an integer or empty.")

    def optionxform(self, optionstr: str) -> str:
        """Do not lowercase key names."""
        return optionstr
