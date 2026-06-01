import abc
import os.path
import shutil
import tempfile
import typing
import unittest

import pytest
import responses

from bugwarrior import config, services
from bugwarrior.config import schema, validation
from bugwarrior.config.load import format_config


class DumbConfig(config.ServiceConfig):
    service: typing.Literal["test"] = "test"
    KEYRING_SERVICE = 'test://'

    import_labels_as_tags: bool = False
    label_template: str = "{{label}}"


class DumbIssue(services.Issue):
    UDAS: dict = {}
    UNIQUE_KEY: tuple[str, ...] = ("id",)
    PRIORITY_MAP: dict = {}

    def get_default_description(self):
        raise NotImplementedError

    def to_taskwarrior(self):
        raise NotImplementedError


class DumbService(services.Service):
    API_VERSION = 1.0
    ISSUE_CLASS = DumbIssue
    CONFIG_SCHEMA = DumbConfig

    def get_owner(self, _):
        raise NotImplementedError

    def issues(self):
        raise NotImplementedError


class AbstractServiceTest(abc.ABC):
    """Ensures that certain test methods are implemented for each service."""

    @abc.abstractmethod
    def test_to_taskwarrior(self):
        """Test Service.to_taskwarrior()."""
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
        os.environ['XDG_CONFIG_HOME'] = os.path.join(self.tempdir, '.config')
        os.environ.pop(config.BUGWARRIORRC, None)
        os.environ.pop('TASKRC', None)
        os.environ.pop('XDG_CONFIG_DIRS', None)

    def tearDown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)

        os.environ.clear()
        os.environ.update(self.old_environ)

    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog):
        self.caplog = caplog

    def validate(self) -> validation.Config:
        config = self.config.copy()
        config['general'] = config.get('general', {})
        formatted_config = format_config(config)
        return validation.validate_config(formatted_config, 'general', 'configpath')

    def assertValidationError(self, expected):
        with self.assertRaises(SystemExit):
            self.validate()

        # Only one message should be logged.
        self.assertEqual(len(self.caplog.records), 1)

        self.assertIn(expected, self.caplog.records[0].message)

        # We may want to use this assertion more than once per test.
        self.caplog.clear()


class ServiceTest(ConfigTest):
    GENERAL_CONFIG = {'annotation_length': 100, 'description_length': 100}
    SERVICE_CONFIG = {}

    @classmethod
    def setUpClass(cls):
        cls.maxDiff = None

    def get_mock_service(
        self,
        service_class,
        section='unspecified',
        config_overrides=None,
        general_overrides=None,
    ):
        options = {
            'general': {**self.GENERAL_CONFIG, 'targets': [section]},
            section: {**self.SERVICE_CONFIG.copy(), 'target': section},
        }
        if config_overrides:
            options[section].update(config_overrides)
        if general_overrides:
            options['general'].update(general_overrides)

        service_config = service_class.CONFIG_SCHEMA(**options[section])
        main_config = schema.MainSectionConfig(**options['general'])

        return service_class(service_config, main_config)

    @staticmethod
    def add_response(url, method='GET', **kwargs):
        responses.add(
            responses.Response(url=url, method=method, match_querystring=True, **kwargs)
        )
