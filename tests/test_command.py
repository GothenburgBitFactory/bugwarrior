import logging
import pathlib
import typing
from unittest import mock

from click.testing import CliRunner
import pytest

from bugwarrior import command
from bugwarrior.config.load import BugwarriorConfigParser

from .base import DumbConfig, DumbIssue, DumbService, register_services


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
    raise RuntimeError('message')


def fake_service(issues, base=DumbService):
    """
    Build a fake service class whose issues() is the given function.
    """
    return type('FakeService', (base,), {'issues': issues})


@pytest.fixture
def runner():
    return CliRunner()


class TestPull:
    @pytest.fixture
    def write_rc(self, tmp_path):
        """
        Return a factory writing a configparser object to the bugwarriorrc path.
        """

        def write(conf):
            rcfile = tmp_path / '.config' / 'bugwarrior' / 'bugwarriorrc'
            rcfile.parent.mkdir(parents=True, exist_ok=True)
            with rcfile.open('w') as configfile:
                conf.write(configfile)
            return rcfile

        return write

    @pytest.fixture
    def config(self, config_environment, write_rc):
        config = BugwarriorConfigParser()

        config['general'] = {
            'targets': 'my_service',
            'static_fields': 'project, priority',
            'taskrc': str(config_environment.taskrc),
        }
        config['my_service'] = {'service': 'test'}

        write_rc(config)
        return config

    def test_success(self, runner, config, caplog):
        """
        A normal `bugwarrior pull` invocation.
        """
        with (
            register_services({'test': fake_service(yields_one())}),
            caplog.at_level(logging.INFO),
        ):
            runner.invoke(command.cli, args=('pull', '--debug'))

        logs = [rec.message for rec in caplog.records]

        assert 'Adding 1 tasks' in logs
        assert 'Updating 0 tasks' in logs
        assert 'Closing 0 tasks' in logs

    def test_failure(self, runner, config, caplog):
        """
        A broken `bugwarrior pull` invocation.
        """
        with (
            register_services({'test': fake_service(raises)}),
            caplog.at_level(logging.ERROR),
        ):
            runner.invoke(command.cli, args=('pull', '--debug'))

        assert caplog.records != []
        assert len(caplog.records) == 2
        assert caplog.records[0].message == "Worker for [my_service] failed"
        assert (
            caplog.records[1].message == "Aborted [my_service] due to critical error."
        )

    def test_partial_failure_survival(self, runner, config, caplog, write_rc):
        """
        One service is broken but the other succeeds.

        Synchronization should work for succeeding services even if one service
        fails.  See https://github.com/ralphbean/bugwarrior/issues/279.
        """
        config['general']['targets'] = 'my_service,my_broken_service'
        config['my_broken_service'] = {'service': 'secondary'}
        write_rc(config)

        with (
            register_services(
                {
                    'test': fake_service(yields_none),
                    'secondary': fake_service(raises, base=SecondaryService),
                }
            ),
            caplog.at_level(logging.INFO),
        ):
            runner.invoke(command.cli, args=('pull', '--debug'))

        logs = [rec.message for rec in caplog.records]
        assert 'Aborted [my_broken_service] due to critical error.' in logs
        assert 'Adding 0 tasks' in logs

    def test_partial_failure_database_integrity(self, runner, config, caplog, write_rc):
        """
        When a service fails and is terminated, don't close existing tasks.

        See https://github.com/ralphbean/bugwarrior/issues/821.
        """
        config['general']['targets'] = 'my_service,my_broken_service'
        config['my_broken_service'] = {'service': 'secondary'}
        write_rc(config)

        # Add a task to each service.
        both_working = {
            'test': fake_service(yields_one(target_specific_url=True)),
            'secondary': fake_service(
                yields_one(target_specific_url=True), base=SecondaryService
            ),
        }
        with register_services(both_working), caplog.at_level(logging.DEBUG):
            runner.invoke(command.cli, args=('pull', '--debug'))
        logs = [rec.message for rec in caplog.records]
        assert 'Adding 2 tasks' in logs

        # Break the secondary service and run pull again.
        secondary_broken = {
            'test': fake_service(yields_one(target_specific_url=True)),
            'secondary': fake_service(raises, base=SecondaryService),
        }
        with register_services(secondary_broken), caplog.at_level(logging.INFO):
            runner.invoke(command.cli, args=('pull', '--debug'))
        logs = [rec.message for rec in caplog.records]

        # Make sure my_broken_service failed while my_service succeeded.
        assert 'Aborted [my_broken_service] due to critical error.' in logs
        assert 'Aborted my_service due to critical error.' not in logs

        # Assert that issues weren't closed or marked complete.
        assert 'Closing 1 tasks' not in logs
        assert 'Completing task' not in logs

    @mock.patch('bugwarrior.command.FileLock')
    def test_locked_repository(
        self, file_lock, runner, config, config_environment, caplog
    ):
        """
        A locked task repository should abort the pull.
        """
        lockfile_path = config_environment.lists_path / 'bugwarrior.lockfile'
        file_lock.return_value.__enter__.side_effect = command.Timeout(
            str(lockfile_path)
        )

        with (
            register_services({'test': DumbService}),
            caplog.at_level(logging.CRITICAL),
        ):
            result = runner.invoke(command.cli, args=('pull', '--debug'))

        assert result.exit_code == 1
        file_lock.assert_called_once_with(str(lockfile_path), timeout=10)
        logs = [rec.message for rec in caplog.records]
        assert any('Your taskrc repository is currently locked.' in log for log in logs)

    def test_legacy_cli(self, runner, config, caplog):
        """
        Test that invoking the subcommand function directly still works.

        Also test that it logs a deprecation warning.
        """
        with (
            register_services({'test': fake_service(yields_one())}),
            caplog.at_level(logging.INFO),
        ):
            runner.invoke(command.pull, args=('--debug'))

        logs = [rec.message for rec in caplog.records]

        assert 'Adding 1 tasks' in logs
        assert 'Updating 0 tasks' in logs
        assert 'Closing 0 tasks' in logs


class TestIni2Toml:
    def test_bugwarriorrc(self, runner):
        basedir = pathlib.Path(__file__).parent
        result = runner.invoke(
            command.cli, args=('ini2toml', str(basedir / 'config/example-bugwarriorrc'))
        )

        assert result.exit_code == 0

        with open(basedir / 'config/example-bugwarrior.toml', 'r') as f:
            assert result.stdout == f.read()
