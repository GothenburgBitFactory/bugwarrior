import logging
import os
import pathlib
import typing
from unittest import TestCase, mock

from click.testing import CliRunner

from bugwarrior import command
from bugwarrior.config.load import BugwarriorConfigParser

from .base import ConfigTest, DumbConfig, DumbIssue, DumbService, register_services


class SecondaryConfig(DumbConfig):
    service: typing.Literal['secondary'] = 'secondary'
    KEYRING_SERVICE = 'secondary://'


class SecondaryIssue(DumbIssue):
    """
    A second fake issue with a distinct UNIQUE_KEY.

    Multi-service tests need two services whose unique keys differ, mirroring
    real services (e.g. GitHub vs Bugzilla); otherwise the close-stale-tasks
    logic cannot tell their tasks apart.
    """

    URL = 'secondaryurl'
    TYPE = 'secondarytype'

    UDAS = {
        URL: {'type': 'string', 'label': 'Secondary URL'},
        TYPE: {'type': 'string', 'label': 'Secondary Type'},
    }
    UNIQUE_KEY = (URL,)


class SecondaryService(DumbService):
    CONFIG_SCHEMA = SecondaryConfig
    ISSUE_CLASS = SecondaryIssue


def yields_one(target_specific_url=False):
    def issues(self):
        record = {
            'title': 'Hallo',
            'url': 'https://example.com',
            'number': 10,
            'labels': [],
        }

        if target_specific_url:
            record['url'] = f'https://example.com/{self.config.target}'

        extra = {'project': 'one', 'type': 'issue', 'annotations': []}
        yield self.get_issue_for_record(record, extra)

    return issues


def yields_none(self):
    return iter([])


def raises(self):
    raise Exception('message')


def fake_service(issues, base=DumbService):
    """
    Build a fake service class whose issues() is the given function.
    """
    return type('FakeService', (base,), {'issues': issues})


class TestPull(ConfigTest):
    def setUp(self):
        super().setUp()

        self.runner = CliRunner()
        self.config = BugwarriorConfigParser()

        self.config['general'] = {
            'targets': 'my_service',
            'static_fields': 'project, priority',
            'taskrc': self.taskrc,
        }
        self.config['my_service'] = {'service': 'test'}

        self.write_rc(self.config)

    def write_rc(self, conf):
        """
        Write configparser object to temporary bugwarriorrc path.
        """
        rcfile = os.path.join(self.tempdir, '.config/bugwarrior/bugwarriorrc')
        if not os.path.exists(os.path.dirname(rcfile)):
            os.makedirs(os.path.dirname(rcfile))
        with open(rcfile, 'w') as configfile:
            conf.write(configfile)
        return rcfile

    def test_success(self):
        """
        A normal `bugwarrior pull` invocation.
        """
        with (
            register_services({'test': fake_service(yields_one())}),
            self.caplog.at_level(logging.INFO),
        ):
            self.runner.invoke(command.cli, args=('pull', '--debug'))

        logs = [rec.message for rec in self.caplog.records]

        self.assertIn('Adding 1 tasks', logs)
        self.assertIn('Updating 0 tasks', logs)
        self.assertIn('Closing 0 tasks', logs)

    def test_failure(self):
        """
        A broken `bugwarrior pull` invocation.
        """
        with (
            register_services({'test': fake_service(raises)}),
            self.caplog.at_level(logging.ERROR),
        ):
            self.runner.invoke(command.cli, args=('pull', '--debug'))

        self.assertNotEqual(self.caplog.records, [])
        self.assertEqual(len(self.caplog.records), 2)
        self.assertEqual(
            self.caplog.records[0].message, "Worker for [my_service] failed: message"
        )
        self.assertEqual(
            self.caplog.records[1].message,
            "Aborted [my_service] due to critical error.",
        )

    def test_partial_failure_survival(self):
        """
        One service is broken but the other succeeds.

        Synchronization should work for succeeding services even if one service
        fails.  See https://github.com/ralphbean/bugwarrior/issues/279.
        """
        self.config['general']['targets'] = 'my_service,my_broken_service'
        self.config['my_broken_service'] = {'service': 'secondary'}
        self.write_rc(self.config)

        with (
            register_services(
                {
                    'test': fake_service(yields_none),
                    'secondary': fake_service(raises, base=SecondaryService),
                }
            ),
            self.caplog.at_level(logging.INFO),
        ):
            self.runner.invoke(command.cli, args=('pull', '--debug'))

        logs = [rec.message for rec in self.caplog.records]
        self.assertIn('Aborted [my_broken_service] due to critical error.', logs)
        self.assertIn('Adding 0 tasks', logs)

    def test_partial_failure_database_integrity(self):
        """
        When a service fails and is terminated, don't close existing tasks.

        See https://github.com/ralphbean/bugwarrior/issues/821.
        """
        self.config['general']['targets'] = 'my_service,my_broken_service'
        self.config['my_broken_service'] = {'service': 'secondary'}
        self.write_rc(self.config)

        # Add a task to each service.
        both_working = {
            'test': fake_service(yields_one(target_specific_url=True)),
            'secondary': fake_service(
                yields_one(target_specific_url=True), base=SecondaryService
            ),
        }
        with register_services(both_working), self.caplog.at_level(logging.DEBUG):
            self.runner.invoke(command.cli, args=('pull', '--debug'))
        logs = [rec.message for rec in self.caplog.records]
        self.assertIn('Adding 2 tasks', logs)

        # Break the secondary service and run pull again.
        secondary_broken = {
            'test': fake_service(yields_one(target_specific_url=True)),
            'secondary': fake_service(raises, base=SecondaryService),
        }
        with register_services(secondary_broken), self.caplog.at_level(logging.INFO):
            self.runner.invoke(command.cli, args=('pull', '--debug'))
        logs = [rec.message for rec in self.caplog.records]

        # Make sure my_broken_service failed while my_service succeeded.
        self.assertIn('Aborted [my_broken_service] due to critical error.', logs)
        self.assertNotIn('Aborted my_service due to critical error.', logs)

        # Assert that issues weren't closed or marked complete.
        self.assertNotIn('Closing 1 tasks', logs)
        self.assertNotIn('Completing task', logs)

    @mock.patch('bugwarrior.command.FileLock')
    def test_locked_repository(self, file_lock):
        """
        A locked task repository should abort the pull.
        """
        lockfile_path = pathlib.Path(self.lists_path) / 'bugwarrior.lockfile'
        file_lock.return_value.__enter__.side_effect = command.Timeout(
            str(lockfile_path)
        )

        with (
            register_services({'test': DumbService}),
            self.caplog.at_level(logging.CRITICAL),
        ):
            result = self.runner.invoke(command.cli, args=('pull', '--debug'))

        self.assertEqual(result.exit_code, 1)
        file_lock.assert_called_once_with(str(lockfile_path), timeout=10)
        logs = [rec.message for rec in self.caplog.records]
        self.assertTrue(
            any('Your taskrc repository is currently locked.' in log for log in logs)
        )

    def test_legacy_cli(self):
        """
        Test that invoking the subcommand function directly still works.

        Also test that it logs a deprecation warning.
        """
        with (
            register_services({'test': fake_service(yields_one())}),
            self.caplog.at_level(logging.INFO),
        ):
            self.runner.invoke(command.pull, args=('--debug'))

        logs = [rec.message for rec in self.caplog.records]

        self.assertIn('Adding 1 tasks', logs)
        self.assertIn('Updating 0 tasks', logs)
        self.assertIn('Closing 0 tasks', logs)


class TestIni2Toml(TestCase):
    def setUp(self):
        super().setUp()
        self.runner = CliRunner()

    def test_bugwarriorrc(self):
        basedir = pathlib.Path(__file__).parent
        result = self.runner.invoke(
            command.cli, args=('ini2toml', str(basedir / 'config/example-bugwarriorrc'))
        )

        self.assertEqual(result.exit_code, 0)

        self.maxDiff = None
        with open(basedir / 'config/example-bugwarrior.toml', 'r') as f:
            self.assertEqual(result.stdout, f.read())
