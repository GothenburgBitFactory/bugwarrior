import codecs
import configparser
import logging
import os

try:
    import tomllib  # python>=3.11
except ImportError:
    import tomli as tomllib  # backport

from . import data, schema

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
    """
    Determine the path to the config file. This will return, in this order of
    precedence:
    - the value of $BUGWARRIORRC if set
    - $XDG_CONFIG_HOME/bugwarrior/bugwarrior.toml if exists
    - $XDG_CONFIG_HOME/bugwarrior/bugwarriorc if exists
    - ~/.bugwarrior.toml if exists
    - ~/.bugwarriorrc if exists
    - <dir>/bugwarrior/bugwarrior.toml if exists, for dir in $XDG_CONFIG_DIRS
    - <dir>/bugwarrior/bugwarriorc if exists, for dir in $XDG_CONFIG_DIRS
    - $XDG_CONFIG_HOME/bugwarrior/bugwarrior.toml otherwise
    """
    if os.environ.get(BUGWARRIORRC):
        return os.environ[BUGWARRIORRC]
    xdg_config_home = (
        os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config'))
    xdg_config_dirs = (
        (os.environ.get('XDG_CONFIG_DIRS') or '/etc/xdg').split(':'))
    paths = [
        os.path.join(xdg_config_home, 'bugwarrior', 'bugwarrior.toml'),
        os.path.join(xdg_config_home, 'bugwarrior', 'bugwarriorrc'),
        os.path.expanduser("~/.bugwarrior.toml"),
        os.path.expanduser("~/.bugwarriorrc")]
    paths += [
        os.path.join(d, 'bugwarrior', 'bugwarrior.toml') for d in xdg_config_dirs]
    paths += [
        os.path.join(d, 'bugwarrior', 'bugwarriorrc') for d in xdg_config_dirs]
    for path in paths:
        if os.path.exists(path):
            return path
    return paths[0]


def parse_file(configpath: str) -> dict:
    if os.path.splitext(configpath)[-1] == '.toml':
        with open(configpath, 'rb') as f:
            config = tomllib.load(f)
    else:
        rawconfig = BugwarriorConfigParser()
        rawconfig.readfp(codecs.open(configpath, "r", "utf-8",))

        config = {'flavor': {}}
        for section in rawconfig.sections():
            if section == 'general':  # log.* -> log_*
                config[section] = {k.replace('.', '_'): v
                                   for k, v in rawconfig[section].items()}
            elif section.startswith('flavor.'):  # log.* -> log_*
                config['flavor'][section.split('.')[-1]] = {
                    k.replace('.', '_'): v
                    for k, v in rawconfig[section].items()}
            else:  # <prefix>.<option> -> <option>
                config[section] = {k.split('.')[-1]: v
                                   for k, v in rawconfig[section].items()}
    return config


class Config(dict):
    def __getitem__(self, key):
        """
        Treat keys containing dots as paths to sub-dictionaries.

        In toml, table names containing dots are parsed as nested tables. E.g.:

        >>> import tomllib
        >>> tomllib.loads("[foo.bar]")
        {'foo': {'bar': {}}}

        This override method allows us to continue accessing these nested
        dictionaries with a single string. (e.g.: `config['foo.bar']`)

        While this will universally apply to table names, at the time of this
        writing it is only useful for configuration "flavors".
        """
        if '.' not in key:
            return super().__getitem__(key)
        obj = self
        while '.' in key:
            nestkey, key = key.split('.', maxsplit=1)
            obj = obj[nestkey]
        return obj.__getitem__(key)


def load_config(main_section, interactive, quiet):
    configpath = get_config_path()
    rawconfig = parse_file(configpath)
    config_dict = schema.validate_config(rawconfig, main_section, configpath)
    config = Config(**config_dict)
    main_config = config[main_section]
    main_config.interactive = interactive
    main_config.data = data.BugwarriorData(
        data.get_data_path(main_config.taskrc))
    configure_logging(main_config.log_file,
                      'WARNING' if quiet else main_config.log_level)
    return config


# ConfigParser is not a new-style class, so inherit from object to fix super().
class BugwarriorConfigParser(configparser.ConfigParser):
    def __init__(self, *args, allow_no_value=True, **kwargs):
        super().__init__(*args, allow_no_value=allow_no_value, **kwargs)

    def getint(self, section, option):
        """ Accepts both integers and empty values. """
        try:
            return super().getint(section, option)
        except ValueError:
            if self.get(section, option) == '':
                return None
            else:
                raise ValueError(
                    "{section}.{option} must be an integer or empty.".format(
                        section=section, option=option))

    @staticmethod
    def optionxform(option):
        """ Do not lowercase key names. """
        return option
