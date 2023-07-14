import codecs
import configparser
import logging
import os

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
    - $XDG_CONFIG_HOME/bugwarrior/bugwarriorc if exists
    - ~/.bugwarriorrc if exists
    - <dir>/bugwarrior/bugwarriorc if exists, for dir in $XDG_CONFIG_DIRS
    - $XDG_CONFIG_HOME/bugwarrior/bugwarriorc otherwise
    """
    if os.environ.get(BUGWARRIORRC):
        return os.environ[BUGWARRIORRC]
    xdg_config_home = (
        os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config'))
    xdg_config_dirs = (
        (os.environ.get('XDG_CONFIG_DIRS') or '/etc/xdg').split(':'))
    paths = [
        os.path.join(xdg_config_home, 'bugwarrior', 'bugwarriorrc'),
        os.path.expanduser("~/.bugwarriorrc")]
    paths += [
        os.path.join(d, 'bugwarrior', 'bugwarriorrc') for d in xdg_config_dirs]
    for path in paths:
        if os.path.exists(path):
            return path
    return paths[0]


def parse_file(configpath: str) -> dict:
    rawconfig = BugwarriorConfigParser()
    rawconfig.readfp(codecs.open(configpath, "r", "utf-8",))
    config = {}
    for section in rawconfig.sections():
        if section in ['hooks', 'notifications']:
            config[section] = rawconfig[section].items()
        elif section == 'general' or section.startswith('flavor.'):
            config[section] = {k.replace('log.', 'log_'): v
                               for k, v in rawconfig[section].items()}
        else:
            service = rawconfig[section].pop('service')
            service_prefix = 'ado' if service == 'azuredevops' else service
            config[section] = {'service': service}
            for k, v in rawconfig[section].items():
                try:
                    prefix, key = k.split('.')
                except ValueError:  # missing prefix
                    prefix = None
                    key = k
                if prefix != service_prefix:
                    raise SystemExit(
                        f"[{section}]\n{k} <-expected prefix "
                        f"'{service_prefix}': did you mean "
                        f"'{service_prefix}.{key}'?")
                config[section][key] = v
    return config


def load_config(main_section, interactive, quiet):
    configpath = get_config_path()
    rawconfig = parse_file(configpath)
    config = schema.validate_config(rawconfig, main_section, configpath)
    main_config = config[main_section]
    main_config.interactive = interactive
    main_config.data = data.BugwarriorData(
        data.get_data_path(config[main_section].taskrc))
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
