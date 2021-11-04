import codecs
import configparser
import logging
import os

from bugwarrior.services import get_service

from .data import BugwarriorData, get_data_path
from .parse import aslist, die, ServiceConfig

log = logging.getLogger(__name__)

# The name of the environment variable that can be used to ovewrite the path
# to the bugwarriorrc file
BUGWARRIORRC = "BUGWARRIORRC"


def validate_config(config, main_section):
    if not config.has_section(main_section):
        die("No [%s] section found." % main_section)

    logging.basicConfig(
        level=getattr(logging, config.get(main_section, 'log.level')),
        filename=config.get(main_section, 'log.file'),
    )

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

    if not config.has_option(main_section, 'targets'):
        die("No targets= item in [%s] found." % main_section)

    targets = aslist(config.get(main_section, 'targets'))
    targets = [t for t in targets if len(t)]

    if not targets:
        die("Empty targets= item in [%s]." % main_section)

    for target in targets:
        if target not in config.sections():
            die("No [%s] section found." % target)

    # Validate each target one by one.
    for target in targets:
        service = config.get(target, 'service')
        if not service:
            die("No 'service' in [%s]" % target)

        if not get_service(service):
            die("'%s' in [%s] is not a valid service." % (service, target))

        # Call the service-specific validator
        service = get_service(service)
        service_config = ServiceConfig(service.CONFIG_PREFIX, config, target)
        service.validate_config(service_config, target)


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


def fix_logging_path(config, main_section):
    """
    Expand environment variables and user home (~) in the log.file and return
    as relative path.
    """
    log_file = config.get(main_section, 'log.file')
    if log_file:
        log_file = os.path.expanduser(os.path.expandvars(log_file))
        if os.path.isabs(log_file):
            log_file = os.path.relpath(log_file)
    return log_file


def load_config(main_section, interactive=False):
    config = BugwarriorConfigParser({'log.level': "INFO", 'log.file': None})
    path = get_config_path()
    config.readfp(codecs.open(path, "r", "utf-8",))
    config.interactive = interactive
    config.data = BugwarriorData(get_data_path(config, main_section))
    config.set(
        main_section, 'log.file', fix_logging_path(config, main_section))
    validate_config(config, main_section)
    return config


# ConfigParser is not a new-style class, so inherit from object to fix super().
class BugwarriorConfigParser(configparser.ConfigParser, object):
    def __init__(self, *args, allow_no_value=True, **kwargs):
        super().__init__(*args, allow_no_value=allow_no_value, **kwargs)

    def getint(self, section, option):
        """ Accepts both integers and empty values. """
        try:
            return super().getint(section, option)
        except ValueError:
            if self.get(section, option) == u'':
                return None
            else:
                raise ValueError(
                    "{section}.{option} must be an integer or empty.".format(
                        section=section, option=option))
