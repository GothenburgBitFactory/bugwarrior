from __future__ import unicode_literals

import unittest
import os
from tempfile import mkdtemp
from shutil import rmtree
from mock import patch

import bugwarrior.config as config


import xdg

class TestGetConfigPath(unittest.TestCase):

    def setUp(self):
        self.tmpdir = mkdtemp()
        self.old_environ = os.environ.copy()
        self.old_xdg_config_home = xdg.BaseDirectory.xdg_config_home
        self.old_xdg_config_dirs = xdg.BaseDirectory.xdg_config_dirs
        os.environ['HOME'] = self.tmpdir
        if config.BUGWARRIORRC in os.environ:
            del os.environ[config.BUGWARRIORRC]
        xdg.BaseDirectory.xdg_config_home = os.path.join(self.tmpdir, '.config')
        xdg.BaseDirectory.xdg_config_dirs = [xdg.BaseDirectory.xdg_config_home]

    def tearDown(self):
        rmtree(self.tmpdir)
        os.environ = self.old_environ
        xdg.BaseDirectory.xdg_config_home = self.old_xdg_config_home
        xdg.BaseDirectory.xdg_config_dirs = self.old_xdg_config_dirs

    def create(self, path):
        """
        Create an empty file in the temporary directory, return the full path.
        """
        fpath = os.path.join(self.tmpdir, path)
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
            os.path.join(self.tmpdir, '.config/bugwarrior/bugwarriorrc'))

    def test_env(self):
        """
        If $BUGWARRIORRC is set, it takes precedence over everything else (even
        if the file doesn't exist).
        """
        rc = os.path.join(self.tmpdir, 'my-bugwarriorc')
        os.environ['BUGWARRIORRC'] = rc
        self.create('.bugwarriorrc')
        self.create('.config/bugwarrior/bugwarriorrc')
        self.assertEquals(config.get_config_path(), rc)


