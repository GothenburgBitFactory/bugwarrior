import os
import json
from six.moves import configparser

from bugwarrior import data

from .base import ConfigTest


class TestData(ConfigTest):
    def setUp(self):
        super(TestData, self).setUp()
        config = configparser.RawConfigParser()
        config.add_section('general')
        self.data = data.BugwarriorData(self.lists_path)

    def assert0600(self):
        permissions = oct(os.stat(self.data.datafile).st_mode & 0o777)
        # python2 -> 0600, python3 -> 0o600
        self.assertIn(permissions, ['0600', '0o600'])

    def test_get_set(self):
        # "touch" data file.
        with open(self.data.datafile, 'w+') as handle:
            json.dump({'old': 'stuff'}, handle)

        self.data.set('key', 'value')

        self.assertEqual(self.data.get('key'), 'value')
        self.assertEqual(
            self.data.get_data(), {'old': 'stuff', 'key': 'value'})
        self.assert0600()

    def test_set_first_time(self):
        self.data.set('key', 'value')

        self.assertEqual(self.data.get('key'), 'value')
        self.assert0600()

    def test_path_attribute(self):
        self.assertEqual(self.data.path, self.lists_path)
