import os
import logging
from unittest import mock

from click.testing import CliRunner
import pytest

from bugwarrior import command
from bugwarrior.config.load import BugwarriorConfigParser

from .base import ConfigTest
from .test_github import ARBITRARY_ISSUE, ARBITRARY_EXTRA


def fake_github_issues(self):
    for issue in [self.get_issue_for_record(ARBITRARY_ISSUE, ARBITRARY_EXTRA)]:
        yield issue


def fake_bz_issues(self):
    for issue in [{
            'annotations': [],
            'bugzillabugid': 1234567,
            'bugzillastatus': 'NEW',
            'bugzillasummary': 'This is the issue summary',
            'bugzillaurl': u'https://http://one.com//show_bug.cgi?id=1234567',
            'bugzillaproduct': 'Product',
            'bugzillacomponent': 'Something',
            'description': u'(bw)Is#1234567 - This is the issue summary .. https://http://one.com//show_bug.cgi?id=1234567',
            'priority': 'H',
            'project': 'Something',
            'tags': []}]:
        yield issue


class TestPull(ConfigTest):

    def setUp(self):
        super().setUp()

        self.runner = CliRunner()
        self.config = BugwarriorConfigParser()

        self.config.add_section('general')
        self.config.set('general', 'targets', 'my_service')
        self.config.set('general', 'static_fields', 'project, priority')
        self.config.add_section('my_service')
        self.config.set('my_service', 'service', 'github')
        self.config.set('my_service', 'github.login', 'ralphbean')
        self.config.set('my_service', 'github.password', 'abc123')
        self.config.set('my_service', 'github.username', 'ralphbean')

        self.write_rc(self.config)

    def write_rc(self, config):
        """
        Write configparser object to temporary bugwarriorrc path.
        """
        rcfile = os.path.join(self.tempdir, '.config/bugwarrior/bugwarriorrc')
        if not os.path.exists(os.path.dirname(rcfile)):
            os.makedirs(os.path.dirname(rcfile))
        with open(rcfile, 'w') as configfile:
            config.write(configfile)
        return rcfile

    @mock.patch(
        'bugwarrior.services.github.GithubService.issues', fake_github_issues)
    def test_success(self):
        """
        A normal bugwarrior-pull invocation.
        """
        with self.caplog.at_level(logging.INFO):
            self.runner.invoke(command.pull)

        logs = [rec.message for rec in self.caplog.records]

        self.assertIn('Adding 1 tasks', logs)
        self.assertIn('Updating 0 tasks', logs)
        self.assertIn('Closing 0 tasks', logs)

    @mock.patch(
        'bugwarrior.services.github.GithubService.issues',
        lambda self: (_ for _ in ()).throw(Exception('message'))
    )
    def test_failure(self):
        """
        A broken bugwarrior-pull invocation.
        """
        with self.caplog.at_level(logging.ERROR):
            self.runner.invoke(command.pull)

        self.assertNotEqual(self.caplog.records, [])
        self.assertEqual(len(self.caplog.records), 1)
        self.assertEqual(self.caplog.records[0].message,
                         "Aborted my_service due to critical error.")

    @mock.patch(
        'bugwarrior.services.github.GithubService.issues',
        lambda self: []
    )
    @mock.patch(
        'bugwarrior.services.bz.BugzillaService.issues',
        lambda self: (_ for _ in ()).throw(Exception('message'))
    )
    def test_partial_failure_survival(self):
        """
        One service is broken but the other succeeds.

        Synchronization should work for succeeding services even if one service
        fails.  See https://github.com/ralphbean/bugwarrior/issues/279.
        """
        self.config.set('general', 'targets', 'my_service,my_broken_service')
        self.config.add_section('my_broken_service')
        self.config.set('my_broken_service', 'service', 'bugzilla')
        self.config.set(
            'my_broken_service', 'bugzilla.base_uri', 'bugzilla.redhat.com')
        self.config.set(
            'my_broken_service', 'bugzilla.username', 'rbean@redhat.com')

        self.write_rc(self.config)

        with self.caplog.at_level(logging.INFO):
            self.runner.invoke(command.pull)

        logs = [rec.message for rec in self.caplog.records]
        self.assertIn(
            'Aborted my_broken_service due to critical error.', logs)
        self.assertIn('Adding 0 tasks', logs)

    @mock.patch(
        'bugwarrior.services.github.GithubService.issues', fake_github_issues)
    @mock.patch('bugzilla.Bugzilla')
    def test_partial_failure_database_integrity(self, bugzillalib):
        """
        When a service fails and is terminated, don't close existing tasks.

        See https://github.com/ralphbean/bugwarrior/issues/821.
        """
        # Add the broken service to the configuration.
        self.config.set('general', 'targets', 'my_service,my_broken_service')
        self.config.add_section('my_broken_service')
        self.config.set('my_broken_service', 'service', 'bugzilla')
        self.config.set(
            'my_broken_service', 'bugzilla.base_uri', 'bugzilla.redhat.com')
        self.config.set(
            'my_broken_service', 'bugzilla.username', 'rbean@redhat.com')
        self.write_rc(self.config)

        # Add a task to each service.
        with self.caplog.at_level(logging.DEBUG):
            with mock.patch('bugwarrior.services.bz.BugzillaService.issues',
                            fake_bz_issues):
                self.runner.invoke(command.pull)
        logs = [rec.message for rec in self.caplog.records]
        self.assertIn('Adding 2 tasks', logs)

        # Break the service and run pull again.
        with self.caplog.at_level(logging.INFO):
            with mock.patch(
                'bugwarrior.services.bz.BugzillaService.issues',
                lambda self: (_ for _ in ()).throw(Exception('message'))
            ):
                self.runner.invoke(command.pull)
        logs = [rec.message for rec in self.caplog.records]

        # Make sure my_broken_service failed while my_service succeeded.
        self.assertIn('Aborted my_broken_service due to critical error.', logs)
        self.assertNotIn('Aborted my_service due to critical error.', logs)

        # Assert that issues weren't closed or marked complete.
        self.assertNotIn('Closing 1 tasks', logs)
        self.assertNotIn('Completing task', logs)
