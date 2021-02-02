import os
import configparser
import logging
from unittest import mock

from click.testing import CliRunner
import pytest

from bugwarrior import command

from .base import ConfigTest


class TestPull(ConfigTest):

    def setUp(self):
        super().setUp()

        self.runner = CliRunner()
        self.config = configparser.RawConfigParser()

        self.config.add_section('general')
        self.config.set('general', 'targets', 'my_service')
        self.config.set('general', 'static_fields', 'project, priority')
        self.config.add_section('my_service')
        self.config.set('my_service', 'service', 'github')
        self.config.set('my_service', 'github.login', 'ralphbean')
        self.config.set('my_service', 'github.password', 'abc123')
        self.config.set('my_service', 'github.username', 'ralphbean')

    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog):
        self.caplog = caplog

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
        'bugwarrior.services.github.GithubService.issues',
        lambda self: []
    )
    def test_success(self):
        """
        A normal bugwarrior-pull invocation.
        """
        self.write_rc(self.config)

        with self.caplog.at_level(logging.ERROR):
            self.runner.invoke(command.pull)

        self.assertEqual(self.caplog.records, [])

    @mock.patch(
        'bugwarrior.services.github.GithubService.issues',
        lambda self: (_ for _ in ()).throw(Exception('message'))
    )
    def test_failure(self):
        """
        A broken bugwarrior-pull invocation.
        """
        self.write_rc(self.config)

        with self.caplog.at_level(logging.ERROR):
            self.runner.invoke(command.pull)

        self.assertNotEqual(self.caplog.records, [])
        self.assertEqual(len(self.caplog.records), 1)
        self.assertEqual(self.caplog.records[0].message,
                         "Aborted (critical error in target 'my_service')")

    @mock.patch(
        'bugwarrior.services.github.GithubService.issues',
        lambda self: []
    )
    @mock.patch(
        'bugwarrior.services.bz.BugzillaService.issues',
        lambda self: (_ for _ in ()).throw(Exception('message'))
    )
    def test_partial_failure(self):
        """
        One service is broken but the other succeeds.
        """
        self.config.set('general', 'targets', 'my_service,my_broken_service')
        self.config.add_section('my_broken_service')
        self.config.set('my_broken_service', 'service', 'bugzilla')
        self.config.set(
            'my_broken_service', 'bugzilla.base_uri', 'bugzilla.redhat.com')
        self.config.set(
            'my_broken_service', 'bugzilla.username', 'rbean@redhat.com')

        self.write_rc(self.config)

        with self.caplog.at_level(logging.ERROR):
            self.runner.invoke(command.pull)

        self.assertNotEqual(self.caplog.records, [])
        self.assertEqual(len(self.caplog.records), 1)
        self.assertEqual(
            self.caplog.records[0].message,
            "Aborted (critical error in target 'my_broken_service')")
