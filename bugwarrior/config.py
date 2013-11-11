import twiggy
from twiggy import log
from twiggy.levels import name2level
import os
import optparse
import sys

from ConfigParser import ConfigParser, NoOptionError


def asbool(some_value):
    """ Cast config values to boolean. """
    return str(some_value).lower() in ['y', 'yes', 't', 'true', '1', 'on']


def get_service_password(service, username, oracle=None, interactive=False):
    """
    Retrieve the sensitive password for a service by:

      * retrieving password from a secure store (@oracle:use_keyring, default)
      * asking the password from the user (@oracle:ask_password, interactive)

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

    if password is None:
        die("MISSING PASSWORD: oracle='%s', interactive=%s for service=%s" %
            (oracle, interactive, service))
    return password


def load_example_rc():
    root = '/'.join(__file__.split('/')[:-1])
    fname = root + '/README.rst'
    with open(fname, 'r') as f:
        readme = f.read()
    example = readme.split('.. example')[1][4:]
    return example

error_template = """
*************************************************
* There was a problem with your ~/.bugwarriorrc *
*   {msg}
* Here's an example template to help:           *
*************************************************
{example}"""


def die(msg):
    log.options(suppress_newlines=False).critical(
        error_template,
        msg=msg,
        example=load_example_rc(),
    )
    sys.exit(1)


# This needs to be imported here and not above to avoid a circular-import.
from bugwarrior.services import SERVICES


def parse_args():
    p = optparse.OptionParser()
    p.add_option('-f', '--config', default='~/.bugwarriorrc')
    p.add_option('-i', '--interactive', action='store_true', default=False)
    return p.parse_args()


def validate_config(config):
    if not config.has_section('general'):
        die("No [general] section found.")

    twiggy.quickSetup(
        name2level(config.get('general', 'log.level')),
        config.get('general', 'log.file')
    )

    if not config.has_option('general', 'targets'):
        die("No targets= item in [general] found.")

    targets = config.get('general', 'targets')
    targets = [t.strip() for t in targets.split(",")]

    for target in targets:
        if target not in config.sections():
            die("No [%s] section found." % target)

    for option in ['bitly.api_user', 'bitly.api_key']:
        if not config.has_option('general', option):
            log.name('config').warning(
                "URLs will not be shortened with bit.ly"
            )

    # Validate each target one by one.
    for target in targets:
        service = config.get(target, 'service')
        if not service:
            die("No 'service' in [%s]" % target)

        if service not in SERVICES:
            die("'%s' in [%s] is not a valid service." % (service, target))

        # Call the service-specific validator
        SERVICES[service].validate_config(config, target)


def load_config():
    opts, args = parse_args()

    config = ConfigParser({'log.level': "DEBUG", 'log.file': None})
    config.read(os.path.expanduser(opts.config))
    config.interactive = opts.interactive
    validate_config(config)

    return config
