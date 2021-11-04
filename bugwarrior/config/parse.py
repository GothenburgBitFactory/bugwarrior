import configparser
import logging
import os
import re
import six
import sys

log = logging.getLogger(__name__)


def asbool(some_value):
    """ Cast config values to boolean. """
    return six.text_type(some_value).lower() in [
        'y', 'yes', 't', 'true', '1', 'on'
    ]


def aslist(value):
    """ Cast config values to lists of strings """
    return [item.strip() for item in re.split(",(?![^{]*})", value.strip())]


def asint(value):
    """ Cast config values to int, or None for empty strings."""
    if value == '':
        return None
    return int(value)


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


def get_taskrc_path(conf, main_section):
    path = os.getenv('TASKRC', '~/.taskrc')
    if conf.has_option(main_section, 'taskrc'):
        path = conf.get(main_section, 'taskrc')
    return os.path.normpath(
        os.path.expanduser(path)
    )


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
            value = self.config_parser.get(
                self.service_target, self._get_key(key))
            if to_type:
                return to_type(value)
            return value
        except configparser.NoSectionError:
            return default
        except configparser.NoOptionError:
            return default

    def _get_key(self, key):
        return '%s.%s' % (self.config_prefix, key)
