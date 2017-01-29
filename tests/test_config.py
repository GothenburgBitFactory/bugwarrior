# coding: utf-8
from __future__ import unicode_literals

import os
import configparser
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
        os.environ['TASKDATA'] = ''
        self.assertDataPath(self.lists_path)

    def test_unassigned(self):
        """
        When data path is not assigned, use default location.
        """
        # Empty taskrc.
        with open(self.taskrc, 'w'):
            pass

        os.environ['TASKDATA'] = ''

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
