import configparser
import logging
import os
from pathlib import Path
from typing import Any

try:
    import tomllib  # python>=3.11
except ImportError:
    import tomli as tomllib  # backport

from bugwarrior.config.validation import Config, validate_config

# The name of the environment variable that can be used to ovewrite the path
# to the bugwarriorrc file
BUGWARRIORRC = "BUGWARRIORRC"


def configure_logging(logfile, loglevel):
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
        logging.getLogger(spammer).setLevel(logging.WARN)


def get_config_path():
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
    # Build flavors from 'flavor' table
    flavors = {
        name: flavor_config for name, flavor_config in config.pop("flavor", {}).items()
    }

    # Handle 'general' as top-level key (TOML format, tests)
    if "general" in config:
        flavors["general"] = config.pop("general")

    services = {
        section: {**config.pop(section), "target": section}
        for section in list(config)
        if section not in {"hooks", "notifications"}
    }

    return {
        "flavors": flavors,
        "services": services,
        **config,  # remaining: "hooks" and "notifications" (if present)
    }


def parse_toml_file(configpath: str) -> dict:
    with open(configpath, 'rb') as file:
        return tomllib.load(file)


def parse_ini_file(configpath: str) -> dict:
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


def parse_file(configpath: str) -> dict:
    if Path(configpath).suffix == '.toml':
        config = parse_toml_file(configpath)
    else:
        config = parse_ini_file(configpath)
    return format_config(config)


def load_config(main_section, interactive, quiet) -> Config:
    configpath = get_config_path()
    rawconfig = parse_file(configpath)
    rawconfig['flavors'][main_section]['interactive'] = interactive
    config = validate_config(rawconfig, main_section, configpath)
    configure_logging(
        config.main.log_file, 'WARNING' if quiet else config.main.log_level
    )
    return config


# ConfigParser is not a new-style class, so inherit from object to fix super().
class BugwarriorConfigParser(configparser.ConfigParser):
    def __init__(self, *args, allow_no_value=True, **kwargs):
        super().__init__(
            *args, allow_no_value=allow_no_value, interpolation=None, **kwargs
        )

    def getint(self, section, option):
        """Accepts both integers and empty values."""
        try:
            return super().getint(section, option)
        except ValueError:
            if self.get(section, option) == '':
                return None
            else:
                raise ValueError(
                    "{section}.{option} must be an integer or empty.".format(
                        section=section, option=option
                    )
                )

    @staticmethod
    def optionxform(option):
        """Do not lowercase key names."""
        return option
