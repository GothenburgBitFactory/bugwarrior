import os
import optparse
import sys

from ConfigParser import ConfigParser


def parse_args():
    p = optparse.OptionParser()
    p.add_option('-f', '--config', default='~/.bugwarriorrc')
    return p.parse_args()


def load_config():
    opts, args = parse_args()

    config = ConfigParser()
    config.read(os.path.expanduser(opts.config))

    if not config.has_section('bitly'):
        print "Config file missing a 'bitly' section."
        sys.exit(1)

    if not config.has_section('github'):
        print "Config file missing a 'github' section."
        sys.exit(1)

    # TODO -- more validation here

    return config
