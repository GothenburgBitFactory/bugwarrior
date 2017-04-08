from builtins import object
import mock
import shutil
import os.path
import tempfile
import unittest

import responses

from bugwarrior import config
from bugwarrior.data import BugwarriorData


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


class ConfigTest(unittest.TestCase):
    """
    Creates config files, configures the environment, and cleans up afterwards.
    """
    def setUp(self):
        self.old_environ = os.environ.copy()
        self.tempdir = tempfile.mkdtemp(prefix='bugwarrior')

        # Create temporary config files.
        self.taskrc = os.path.join(self.tempdir, '.taskrc')
        self.lists_path = os.path.join(self.tempdir, 'lists')
        os.mkdir(self.lists_path)
        with open(self.taskrc, 'w+') as fout:
            fout.write('data.location=%s\n' % self.lists_path)

        # Configure environment.
        os.environ['HOME'] = self.tempdir
        os.environ.pop(config.BUGWARRIORRC, None)
        os.environ.pop('TASKRC', None)
        os.environ.pop('XDG_CONFIG_HOME', None)
        os.environ.pop('XDG_CONFIG_DIRS', None)

    def tearDown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)
        os.environ = self.old_environ


class ServiceTest(ConfigTest):
    GENERAL_CONFIG = {
        'annotation_length': 100,
        'description_length': 100,
    }
    SERVICE_CONFIG = {
    }

    @classmethod
    def setUpClass(cls):
        cls.maxDiff = None

    def get_mock_service(
        self, service_class, section='unspecified',
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
        config.data = BugwarriorData(self.lists_path)

        service_instance = service_class(config, 'general', section)

        return service_instance

    @staticmethod
    def add_response(url, **kwargs):
        responses.add(responses.GET, url, match_querystring=True, **kwargs)
