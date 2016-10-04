from future import standard_library
standard_library.install_aliases()
import codecs
from configparser import ConfigParser
import os
import subprocess
import sys

import six

import logging
log = logging.getLogger(__name__)


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
    import keyring

    password = None
    if not oracle or oracle == "@oracle:use_keyring":
        password = keyring.get_password(service, username)
        if interactive and password is None:
            # -- LEARNING MODE: Password is not stored in keyring yet.
            oracle = "@oracle:ask_password"
            password = get_service_password(service, username,
                                            oracle, interactive=True)
            if password:
                keyring.set_password(service, username, password)
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
        return p.stdout.readline().strip()
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

    targets = config.get(main_section, 'targets')
    targets = [t for t in [t.strip() for t in targets.split(",")] if len(t)]

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
        get_service(service).validate_config(config, target)


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


def load_config(main_section, interactive=False):
    config = ConfigParser({'log.level': "INFO", 'log.file': None})
    path = get_config_path()
    config.readfp(codecs.open(path, "r", "utf-8",))
    config.interactive = interactive
    validate_config(config, main_section)
    return config


def get_taskrc_path(conf, main_section):
    path = os.getenv('TASKRC', '~/.taskrc')
    if conf.has_option(main_section, 'taskrc'):
        path = conf.get(main_section, 'taskrc')
    return os.path.normpath(
        os.path.expanduser(path)
    )


def get_data_path():
    return os.path.expanduser(os.getenv('TASKDATA', '~/.task'))


# This needs to be imported here and not above to avoid a circular-import.
from bugwarrior.services import get_service
