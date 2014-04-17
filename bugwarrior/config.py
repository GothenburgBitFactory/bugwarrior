import codecs
from ConfigParser import ConfigParser
import optparse
import os
import subprocess
import sys

import six
import twiggy
from twiggy import log
from twiggy.levels import name2level


def asbool(some_value):
    """ Cast config values to boolean. """
    return six.text_type(some_value).lower() in [
        'y', 'yes', 't', 'true', '1', 'on'
    ]


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
        p = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        password = p.stdout.read()[:-1]

    if password is None:
        die("MISSING PASSWORD: oracle='%s', interactive=%s for service=%s" %
            (oracle, interactive, service))
    return password


def load_example_rc():
    fname = os.path.join(
        os.path.dirname(__file__),
        '../docs/source/configuration.rst'
    )
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
    config.readfp(
        codecs.open(
            os.path.expanduser(opts.config),
            "r",
            "utf-8",
        )
    )
    config.interactive = opts.interactive
    validate_config(config)

    return config


def get_taskrc_path(conf):
    path = '~/.taskrc'
    if conf.has_option('general', 'taskrc'):
        path = conf.get('general', 'taskrc')
    return os.path.normpath(
        os.path.expanduser(path)
    )


# This needs to be imported here and not above to avoid a circular-import.
from bugwarrior.services import SERVICES
