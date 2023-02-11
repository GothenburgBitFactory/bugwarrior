import os
import json

from bugwarrior.config import data, schema

from ..base import ConfigTest


class TestData(ConfigTest):
    def setUp(self):
        super().setUp()
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


class TestGetDataPath(ConfigTest):

    def setUp(self):
        super().setUp()
        rawconfig = {}
        rawconfig['general'] = {'targets': ['my_service']}
        rawconfig['my_service'] = {
            'service': 'github',
            'login': 'ralphbean',
            'token': 'abc123',
            'username': 'ralphbean',
        }
        self.config = schema.validate_config(
            rawconfig, 'general', 'configpath')

    def assertDataPath(self, expected_datapath):
        self.assertEqual(expected_datapath,
                         data.get_data_path(self.config['general'].taskrc))

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
