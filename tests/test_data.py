import os
import json
import ConfigParser

from bugwarrior import data

from .base import ConfigTest


class TestData(ConfigTest):
    def setUp(self):
        super(TestData, self).setUp()
        config = ConfigParser.RawConfigParser()
        config.add_section('general')
        self.data = data.BugwarriorData(config, 'general')

    def test_get_set(self):
        # "touch" data file.
        with open(self.data.datafile, 'w+') as handle:
            json.dump({'old': 'stuff'}, handle)

        self.data.set('key', 'value')

        self.assertEqual(self.data.get('key'), 'value')
        self.assertEqual(
            self.data.get_data(), {'old': 'stuff', 'key': 'value'})
        self.assertEqual(
            oct(os.stat(self.data.datafile).st_mode & 0777), '0600')

    def test_set_first_time(self):
        self.data.set('key', 'value')

        self.assertEqual(self.data.get('key'), 'value')
        self.assertEqual(
            oct(os.stat(self.data.datafile).st_mode & 0777), '0600')
