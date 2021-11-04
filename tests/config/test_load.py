# coding: utf-8
import os
from unittest import TestCase

from bugwarrior.config import load

from ..base import ConfigTest


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
        self.assertEqual(load.get_config_path(), rc)

    def test_legacy(self):
        """
        Falls back on .bugwarriorrc if it exists
        """
        rc = self.create('.bugwarriorrc')
        self.assertEqual(load.get_config_path(), rc)

    def test_xdg_first(self):
        """
        If both files above exist, the one in $XDG_CONFIG_HOME takes precedence
        """
        self.create('.bugwarriorrc')
        rc = self.create('.config/bugwarrior/bugwarriorrc')
        self.assertEqual(load.get_config_path(), rc)

    def test_no_file(self):
        """
        If no bugwarriorrc exist anywhere, the path to the prefered one is
        returned.
        """
        self.assertEqual(
            load.get_config_path(),
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
        self.assertEqual(load.get_config_path(), rc)

    def test_BUGWARRIORRC_empty(self):
        """
        If $BUGWARRIORRC is set but emty, it is not used and the default file
        is used instead.
        """
        os.environ['BUGWARRIORRC'] = ''
        rc = self.create('.config/bugwarrior/bugwarriorrc')
        self.assertEqual(load.get_config_path(), rc)


class TestBugwarriorConfigParser(TestCase):
    def setUp(self):
        self.config = load.BugwarriorConfigParser()
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


class TestLoggingPath(TestCase):
    def setUp(self):
        self.config = load.BugwarriorConfigParser()
        self.config.add_section('general')
        self.config.set('general', 'log.level', 'INFO')
        self.config.set('general', 'log.file', None)
        self.dir = os.getcwd()
        os.chdir(os.path.expanduser('~'))

    def test_log_stdout(self):
        self.assertIsNone(load.fix_logging_path(self.config, 'general'))

    def test_log_relative_path(self):
        self.config.set('general', 'log.file', 'bugwarrior.log')
        self.assertEqual(
            load.fix_logging_path(self.config, 'general'),
            'bugwarrior.log',
        )

    def test_log_absolute_path(self):
        filename = os.path.join(os.path.expandvars('$HOME'), 'bugwarrior.log')
        self.config.set('general', 'log.file', filename)
        self.assertEqual(
            load.fix_logging_path(self.config, 'general'),
            'bugwarrior.log',
        )

    def test_log_userhome(self):
        self.config.set('general', 'log.file', '~/bugwarrior.log')
        self.assertEqual(
            load.fix_logging_path(self.config, 'general'),
            'bugwarrior.log',
        )

    def test_log_envvar(self):
        self.config.set('general', 'log.file', '$HOME/bugwarrior.log')
        self.assertEqual(
            load.fix_logging_path(self.config, 'general'),
            'bugwarrior.log',
        )

    def tearDown(self):
        os.chdir(self.dir)
