import mock
import shutil
import os.path
import tempfile
import unittest

import responses

from bugwarrior import config


class AbstractServiceTest(object):
    """ Ensures that certain test methods are implemented for each service. """
    def test_to_taskwarrior(self):
        """ Test Service.to_taskwarrior(). """
        raise NotImplementedError

    def test_issues(self):
        """
        Test Service.issues().

        - When the API is accessed via requests, use the responses library to
        mock requests.
        - When the API is accessed via a third party library, substitute a fake
        implementation class for it.
        """
        raise NotImplementedError


def set_up_config(klass):
    klass.old_environ = os.environ.copy()
    klass.tempdir = tempfile.mkdtemp(prefix='bugwarrior')

    # Create temporary config files.
    taskrc = os.path.join(klass.tempdir, '.taskrc')
    lists_path = os.path.join(klass.tempdir, 'lists')
    os.mkdir(lists_path)
    with open(taskrc, 'w+') as fout:
        fout.write('data.location=%s\n' % lists_path)

    # Configure environment.
    os.environ['HOME'] = klass.tempdir
    os.environ.pop(config.BUGWARRIORRC, None)
    os.environ.pop('TASKRC', None)
    os.environ.pop('XDG_CONFIG_HOME', None)
    os.environ.pop('XDG_CONFIG_DIRS', None)


def tear_down_config(klass):
    shutil.rmtree(klass.tempdir, ignore_errors=True)
    os.environ = klass.old_environ


class ConfigTest(unittest.TestCase):
    """
    Creates config files, configures the environment, and cleans up afterwards.
    """
    @classmethod
    def setUpClass(cls):
        set_up_config(cls)

    @classmethod
    def tearDownClass(cls):
        tear_down_config(cls)


class ServiceTest(ConfigTest):
    GENERAL_CONFIG = {
        'annotation_length': 100,
        'description_length': 100,
    }
    SERVICE_CONFIG = {
    }

    def get_mock_service(
        self, service, section='unspecified',
        config_overrides=None, general_overrides=None
    ):
        options = {
            'general': self.GENERAL_CONFIG.copy(),
            section: self.SERVICE_CONFIG.copy(),
        }
        if config_overrides:
            options[section].update(config_overrides)
        if general_overrides:
            options['general'].update(general_overrides)

        def has_option(section, name):
            try:
                return options[section][name]
            except KeyError:
                return False

        def get_option(section, name):
            return options[section][name]

        def get_int(section, name):
            return int(get_option(section, name))

        config = mock.Mock()
        config.has_option = mock.Mock(side_effect=has_option)
        config.get = mock.Mock(side_effect=get_option)
        config.getint = mock.Mock(side_effect=get_int)

        service = service(config, 'general', section)

        return service

    @staticmethod
    def add_response(url, **kwargs):
        responses.add(responses.GET, url, match_querystring=True, **kwargs)
