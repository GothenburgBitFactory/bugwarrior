# coding: utf-8
from __future__ import unicode_literals

import os
from six.moves import configparser
from unittest import TestCase

import bugwarrior.config as config

from .base import ConfigTest


class TestGetConfigPath(ConfigTest):

    def create(self, path):
        """
        Create an empty file in the temporary directory, return the full path.
        """
        fpath = os.path.join(self.tempdir, path)
        if not os.path.exists(os.path.dirname(fpath)):
            os.makedirs(os.path.dirname(fpath))
        open(fpath, 'a').close()
        return fpath

    def test_default(self):
        """
        If it exists, use the file at $XDG_CONFIG_HOME/bugwarrior/bugwarriorrc
        """
        rc = self.create('.config/bugwarrior/bugwarriorrc')
        self.assertEquals(config.get_config_path(), rc)

    def test_legacy(self):
        """
        Falls back on .bugwarriorrc if it exists
        """
        rc = self.create('.bugwarriorrc')
        self.assertEquals(config.get_config_path(), rc)

    def test_xdg_first(self):
        """
        If both files above exist, the one in $XDG_CONFIG_HOME takes precedence
        """
        self.create('.bugwarriorrc')
        rc = self.create('.config/bugwarrior/bugwarriorrc')
        self.assertEquals(config.get_config_path(), rc)

    def test_no_file(self):
        """
        If no bugwarriorrc exist anywhere, the path to the prefered one is
        returned.
        """
        self.assertEquals(
            config.get_config_path(),
            os.path.join(self.tempdir, '.config/bugwarrior/bugwarriorrc'))

    def test_BUGWARRIORRC(self):
        """
        If $BUGWARRIORRC is set, it takes precedence over everything else (even
        if the file doesn't exist).
        """
        rc = os.path.join(self.tempdir, 'my-bugwarriorc')
        os.environ['BUGWARRIORRC'] = rc
        self.create('.bugwarriorrc')
        self.create('.config/bugwarrior/bugwarriorrc')
        self.assertEquals(config.get_config_path(), rc)

    def test_BUGWARRIORRC_empty(self):
        """
        If $BUGWARRIORRC is set but emty, it is not used and the default file
        is used instead.
        """
        os.environ['BUGWARRIORRC'] = ''
        rc = self.create('.config/bugwarrior/bugwarriorrc')
        self.assertEquals(config.get_config_path(), rc)


class TestGetDataPath(ConfigTest):

    def setUp(self):
        super(TestGetDataPath, self).setUp()
        self.config = configparser.RawConfigParser()
        self.config.add_section('general')

    def assertDataPath(self, expected_datapath):
        self.assertEqual(
            expected_datapath, config.get_data_path(self.config, 'general'))

    def test_TASKDATA(self):
        """
        TASKDATA should be respected, even when taskrc's data.location is set.
        """
        datapath = os.environ['TASKDATA'] = os.path.join(self.tempdir, 'data')
        self.assertDataPath(datapath)

    def test_taskrc_datalocation(self):
        """
        When TASKDATA is not set, data.location in taskrc should be respected.
        """
        self.assertTrue('TASKDATA' not in os.environ)
        self.assertDataPath(self.lists_path)

    def test_unassigned(self):
        """
        When data path is not assigned, use default location.
        """
        # Empty taskrc.
        with open(self.taskrc, 'w'):
            pass

        self.assertTrue('TASKDATA' not in os.environ)

        self.assertDataPath(os.path.expanduser('~/.task'))


class TestOracleEval(TestCase):

    def test_echo(self):
        self.assertEqual(config.oracle_eval("echo fööbår"), "fööbår")


class TestBugwarriorConfigParser(TestCase):
    def setUp(self):
        self.config = config.BugwarriorConfigParser()
        self.config.add_section('general')
        self.config.set('general', 'someint', '4')
        self.config.set('general', 'somenone', '')
        self.config.set('general', 'somechar', 'somestring')

    def test_getint(self):
        self.assertEqual(self.config.getint('general', 'someint'), 4)

    def test_getint_none(self):
        self.assertEqual(self.config.getint('general', 'somenone'), None)

    def test_getint_valueerror(self):
        with self.assertRaises(ValueError):
            self.config.getint('general', 'somechar')


class TestServiceConfig(TestCase):
    def setUp(self):
        self.target = 'someservice'

        self.config = config.BugwarriorConfigParser()
        self.config.add_section(self.target)
        self.config.set(self.target, 'someprefix.someint', '4')
        self.config.set(self.target, 'someprefix.somenone', '')
        self.config.set(self.target, 'someprefix.somechar', 'somestring')
        self.config.set(self.target, 'someprefix.somebool', 'true')

        self.service_config = config.ServiceConfig(
            'someprefix', self.config, self.target)

    def test_configparser_proxy(self):
        """
        Methods not defined in ServiceConfig should be proxied to configparser.
        """
        self.assertTrue(
            self.service_config.has_option(self.target, 'someprefix.someint'))

    def test__contains__(self):
        self.assertTrue('someint' in self.service_config)

    def test_get(self):
        self.assertEqual(self.service_config.get('someint'), '4')

    def test_get_default(self):
        self.assertEqual(
            self.service_config.get('someoption', default='somedefault'),
            'somedefault'
        )

    def test_get_default_none(self):
        self.assertIsNone(self.service_config.get('someoption'))

    def test_get_to_type(self):
        self.assertIs(
            self.service_config.get('somebool', to_type=config.asbool),
            True
        )


class TestLoggingPath(TestCase):
    def setUp(self):
        self.config = config.BugwarriorConfigParser(allow_no_value=True)
        self.config.add_section('general')
        self.config.set('general', 'log.level', 'INFO')
        self.config.set('general', 'log.file', None)
        self.dir = os.getcwd()
        os.chdir(os.path.expanduser('~'))

    def test_log_stdout(self):
        self.assertIsNone(config.fix_logging_path(self.config, 'general'))

    def test_log_relative_path(self):
        self.config.set('general', 'log.file', 'bugwarrior.log')
        self.assertEqual(
            config.fix_logging_path(self.config, 'general'),
            'bugwarrior.log',
        )

    def test_log_absolute_path(self):
        filename = os.path.join(os.path.expandvars('$HOME'), 'bugwarrior.log')
        self.config.set('general', 'log.file', filename)
        self.assertEqual(
            config.fix_logging_path(self.config, 'general'),
            'bugwarrior.log',
        )

    def test_log_userhome(self):
        self.config.set('general', 'log.file', '~/bugwarrior.log')
        self.assertEqual(
            config.fix_logging_path(self.config, 'general'),
            'bugwarrior.log',
        )

    def test_log_envvar(self):
        self.config.set('general', 'log.file', '$HOME/bugwarrior.log')
        self.assertEqual(
            config.fix_logging_path(self.config, 'general'),
            'bugwarrior.log',
        )

    def tearDown(self):
        os.chdir(self.dir)
