from __future__ import unicode_literals

import os

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
