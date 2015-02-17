import codecs
from ConfigParser import ConfigParser
import os
import subprocess
import sys

import six
import twiggy
from twiggy import log
from twiggy.levels import name2level
from xdg import BaseDirectory


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
            #stderr=subprocess.STDOUT
        )
        password = p.stdout.read()[:-1]

    if password is None:
        die("MISSING PASSWORD: oracle='%s', interactive=%s for service=%s" %
            (oracle, interactive, service))
    return password


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


def validate_config(config, main_section):
    if not config.has_section(main_section):
        die("No [%s] section found." % main_section)

    twiggy.quickSetup(
        name2level(config.get(main_section, 'log.level')),
        config.get(main_section, 'log.file')
    )

    if not config.has_option(main_section, 'targets'):
        die("No targets= item in [%s] found." % main_section)

    targets = config.get(main_section, 'targets')
    targets = filter(lambda t: len(t), [t.strip() for t in targets.split(",")])

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

        if service not in SERVICES:
            die("'%s' in [%s] is not a valid service." % (service, target))

        # Call the service-specific validator
        SERVICES[service].validate_config(config, target)


def load_config(main_section):
    config = ConfigParser({'log.level': "DEBUG", 'log.file': None})
    path = None
    first_path = BaseDirectory.load_first_config('bugwarrior')
    if first_path is not None:
        path = os.path.join(first_path, 'bugwarriorrc')
    old_path = os.path.expanduser("~/.bugwarriorrc")
    if path is None or not os.path.exists(path):
        if os.path.exists(old_path):
            path = old_path
        else:
            path = os.path.join(BaseDirectory.save_config_path('bugwarrior'), 'bugwarriorrc')
    config.readfp(
        codecs.open(
            path,
            "r",
            "utf-8",
        )
    )
    config.interactive = False  # TODO: make this a command-line option
    validate_config(config, main_section)

    return config


def get_taskrc_path(conf, main_section):
    path = '~/.taskrc'
    if conf.has_option(main_section, 'taskrc'):
        path = conf.get(main_section, 'taskrc')
    return os.path.normpath(
        os.path.expanduser(path)
    )


# This needs to be imported here and not above to avoid a circular-import.
from bugwarrior.services import SERVICES
