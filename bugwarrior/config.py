import twiggy
from twiggy import log
from twiggy.levels import name2level

import os
import optparse
import sys

from ConfigParser import ConfigParser


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
            log.warning("URLs will not be shortened with bit.ly")

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

    validate_config(config)

    return config
