from future import standard_library
standard_library.install_aliases()
import codecs
from six.moves import configparser
import os
import subprocess
import sys

import six

import logging
log = logging.getLogger(__name__)

from bugwarrior.data import BugwarriorData


# The name of the environment variable that can be used to ovewrite the path
# to the bugwarriorrc file
BUGWARRIORRC = "BUGWARRIORRC"


def asbool(some_value):
    """ Cast config values to boolean. """
    return six.text_type(some_value).lower() in [
        'y', 'yes', 't', 'true', '1', 'on'
    ]


def aslist(value):
    """ Cast config values to lists of strings """
    return [item.strip() for item in value.strip().split(',')]


def asint(value):
    """ Cast config values to int, or None for empty strings."""
    if value == '':
        return None
    return int(value)


def get_keyring():
    """ Try to import and return optional keyring dependency. """
    try:
        import keyring
    except ImportError:
        raise ImportError(
            "Extra dependencies must be installed to use the keyring feature. "
            "Install them with `pip install bugwarrior[keyring]`.")
    return keyring


def get_service_password(service, username, oracle=None, interactive=False):
    """
    Retrieve the sensitive password for a service by:

      * retrieving password from a secure store (@oracle:use_keyring, default)
      * asking the password from the user (@oracle:ask_password, interactive)
      * executing a command and use the output as password
        (@oracle:eval:<command>)

    Note that the keyring may or may not be locked
    which requires that the user provides a password (interactive mode).

    :param service:     Service name, may be key into secure store (as string).
    :param username:    Username for the service (as string).
    :param oracle:      Hint which password oracle strategy to use.
    :return: Retrieved password (as string)

    .. seealso::
        https://bitbucket.org/kang/python-keyring-lib
    """
    import getpass

    password = None
    if not oracle or oracle == "@oracle:use_keyring":
        keyring = get_keyring()
        password = keyring.get_password(service, username)
        if interactive and password is None:
            # -- LEARNING MODE: Password is not stored in keyring yet.
            oracle = "@oracle:ask_password"
            password = get_service_password(service, username,
                                            oracle, interactive=True)
            if password:
                keyring.set_password(service, username, password)
        elif not interactive and password is None:
            log.error(
                'Unable to retrieve password from keyring. '
                'Re-run in interactive mode to set a password'
            )
    elif interactive and oracle == "@oracle:ask_password":
        prompt = "%s password: " % service
        password = getpass.getpass(prompt)
    elif oracle.startswith('@oracle:eval:'):
        command = oracle[13:]
        return oracle_eval(command)

    if password is None:
        die("MISSING PASSWORD: oracle='%s', interactive=%s for service=%s" %
            (oracle, interactive, service))
    return password


def oracle_eval(command):
    """ Retrieve password from the given command """
    p = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.wait()
    if p.returncode == 0:
        return p.stdout.readline().strip().decode('utf-8')
    else:
        die(
            "Error retrieving password: `{command}` returned '{error}'".format(
                command=command, error=p.stderr.read().strip()))


def load_example_rc():
    fname = os.path.join(
        os.path.dirname(__file__),
        'docs/configuration.rst'
    )
    with open(fname, 'r') as f:
        readme = f.read()
    example = readme.split('.. example')[1][4:]
    return example

error_template = """
*************************************************
* There was a problem with your bugwarriorrc    *
*   {error_msg}
* Here's an example template to help:           *
*************************************************
{example}"""


def die(error_msg):
    log.critical(error_template.format(
        error_msg=error_msg,
        example=load_example_rc(),
    ))
    sys.exit(1)


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
    config = BugwarriorConfigParser({'log.level': "INFO", 'log.file': None}, allow_no_value=True)
    path = get_config_path()
    config.readfp(codecs.open(path, "r", "utf-8",))
    config.interactive = interactive
    config.data = BugwarriorData(get_data_path(config, main_section))
    config.set(main_section, 'log.file', fix_logging_path(config, main_section))
    validate_config(config, main_section)
    return config


def get_taskrc_path(conf, main_section):
    path = os.getenv('TASKRC', '~/.taskrc')
    if conf.has_option(main_section, 'taskrc'):
        path = conf.get(main_section, 'taskrc')
    return os.path.normpath(
        os.path.expanduser(path)
    )


def get_data_path(config, main_section):
    taskrc = get_taskrc_path(config, main_section)

    # We cannot use the taskw module here because it doesn't really support
    # the `_` subcommands properly (`rc:` can't be used for them).
    line_prefix = 'data.location='

    # Take a copy of the environment and add our taskrc to it.
    env = dict(os.environ)
    env['TASKRC'] = taskrc

    if not os.path.isfile(taskrc):
        raise IOError('Unable to find taskrc file.')

    tw_show = subprocess.Popen(
        ('task', '_show'), stdout=subprocess.PIPE, env=env)
    data_location = subprocess.check_output(
        ('grep', '-e', '^' + line_prefix), stdin=tw_show.stdout)
    tw_show.wait()
    data_path = data_location[len(line_prefix):].rstrip().decode('utf-8')

    if not data_path:
        raise IOError('Unable to determine the data location.')

    return os.path.normpath(os.path.expanduser(data_path))


# ConfigParser is not a new-style class, so inherit from object to fix super().
class BugwarriorConfigParser(configparser.ConfigParser, object):
    def getint(self, section, option):
        """ Accepts both integers and empty values. """
        try:
            return super(BugwarriorConfigParser, self).getint(section, option)
        except ValueError:
            if self.get(section, option) == u'':
                return None
            else:
                raise ValueError(
                    "{section}.{option} must be an integer or empty.".format(
                        section=section, option=option))


class ServiceConfig(object):
    """ A service-aware wrapper for ConfigParser objects. """
    def __init__(self, config_prefix, config_parser, service_target):
        self.config_prefix = config_prefix
        self.config_parser = config_parser
        self.service_target = service_target

    def __getattr__(self, name):
        """ Proxy undefined attributes/methods to ConfigParser object. """
        return getattr(self.config_parser, name)

    def __contains__(self, key):
        """ Does service section specify this option? """
        return self.config_parser.has_option(
            self.service_target, self._get_key(key))

    def get(self, key, default=None, to_type=None):
        try:
            value = self.config_parser.get(self.service_target, self._get_key(key))
            if to_type:
                return to_type(value)
            return value
        except:
            return default

    def _get_key(self, key):
        return '%s.%s' % (self.config_prefix, key)


# This needs to be imported here and not above to avoid a circular-import.
from bugwarrior.services import get_service
