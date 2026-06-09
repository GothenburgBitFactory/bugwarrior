import contextlib
import os.path
import shutil
import tempfile
import typing
import unittest
import unittest.mock

import pytest

from bugwarrior import config, services
from bugwarrior.config import validation
from bugwarrior.config.load import format_config


class DumbConfig(config.ServiceConfig):
    service: typing.Literal["test"] = "test"
    KEYRING_SERVICE = 'test://'

    import_labels_as_tags: bool = False
    label_template: str = "{{label}}"


class DumbIssue(services.Issue):
    URL = "dumburl"
    TYPE = "dumbtype"

    UDAS = {
        URL: {"type": "string", "label": "Dumb URL"},
        TYPE: {"type": "string", "label": "Dumb Type"},
    }
    UNIQUE_KEY = (URL,)
    PRIORITY_MAP: dict = {}

    def get_default_description(self):
        return self.build_default_description(
            title=self.record.get("title", ""),
            url=self.record.get("url", ""),
            number=self.record.get("number", ""),
        )

    def to_taskwarrior(self):
        return {
            "project": self.extra.get("project"),
            "priority": self.config.default_priority,
            "annotations": self.extra.get("annotations", []),
            "tags": self.get_tags_from_labels(self.record.get("labels", [])),
            self.URL: self.record.get("url", ""),
            self.TYPE: self.extra.get("type", "issue"),
        }


class DumbService(services.Service):
    API_VERSION = services.LATEST_API_VERSION
    ISSUE_CLASS = DumbIssue
    CONFIG_SCHEMA = DumbConfig

    def issues(self):
        raise NotImplementedError


#: Modules that import get_service by name and must be patched together so the
#: fake service resolves consistently across config loading, collection, and db.
_GET_SERVICE_MODULES = (
    'bugwarrior.config.schema',
    'bugwarrior.config.validation',
    'bugwarrior.config',
    'bugwarrior.db',
    'bugwarrior.collect',
)


@contextlib.contextmanager
def register_services(mapping=None):
    """
    Make fake services resolvable via get_service for the duration of a block.

    Patches get_service in every module that imports it so that orchestration
    code (config loading, collection, db) resolves the given name-to-class
    mapping instead of the real entry points. Defaults to mapping the "test"
    service to DumbService.
    """
    mapping = mapping or {'test': DumbService}

    def fake_get_service(name):
        try:
            return mapping[name]
        except KeyError:
            raise ValueError(
                f"Configured service '{name}' not found. "
                "Is it installed? Or misspelled?"
            )

    with contextlib.ExitStack() as stack:
        for module in _GET_SERVICE_MODULES:
            stack.enter_context(
                unittest.mock.patch(f'{module}.get_service', fake_get_service)
            )
        yield mapping


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

    def enter_context(self, cm):
        """Enter a context manager for the duration of the test.

        Backport of unittest.TestCase.enterContext, which is only available on
        Python 3.11+ (we still support 3.10).
        """
        value = cm.__enter__()
        self.addCleanup(cm.__exit__, None, None, None)
        return value

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
