import abc
import shutil
import os.path
import tempfile
import unittest

import pytest
import responses

from bugwarrior import config
from bugwarrior.config import data, schema


class AbstractServiceTest(abc.ABC):
    """ Ensures that certain test methods are implemented for each service. """
    @abc.abstractmethod
    def test_to_taskwarrior(self):
        """ Test Service.to_taskwarrior(). """
        raise NotImplementedError

    @abc.abstractmethod
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

    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog):
        self.caplog = caplog

    def validate(self):
        conf = schema.validate_config(self.config, 'general', 'configpath')
        conf['general'].data = data.BugwarriorData(self.lists_path)
        conf['general'].interactive = False
        return conf

    def assertValidationError(self, expected):

        with self.assertRaises(SystemExit):
            self.validate()

        # Only one message should be logged.
        self.assertEqual(len(self.caplog.records), 1)

        self.assertIn(expected, self.caplog.records[0].message)


class ServiceTest(ConfigTest):
    GENERAL_CONFIG = {
        'interactive': False,
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
            'general': {**self.GENERAL_CONFIG, 'targets': section},
            section: self.SERVICE_CONFIG.copy(),
        }
        if config_overrides:
            options[section].update(config_overrides)
        if general_overrides:
            options['general'].update(general_overrides)

        service_config = service_class.CONFIG_SCHEMA(**options[section])
        main_config = schema.MainSectionConfig(**options['general'])
        main_config.data = data.BugwarriorData(self.lists_path)

        return service_class(service_config, main_config, section)

    @staticmethod
    def add_response(url, method='GET', **kwargs):
        responses.add(responses.Response(
            url=url,
            method=method,
            match_querystring=True,
            **kwargs
        ))
