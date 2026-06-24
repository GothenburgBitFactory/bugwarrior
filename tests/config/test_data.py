import json
import os

from bugwarrior.config import data, schema

from ..base import ConfigTest


class TestData(ConfigTest):
    def setUp(self):
        super().setUp()
        self.data = data.BugwarriorData(self.lists_path)

    def assert0600(self):
        permissions = oct(os.stat(self.data._datafile).st_mode & 0o777)
        # python2 -> 0600, python3 -> 0o600
        assert permissions in ['0600', '0o600']

    def test_get_set(self):
        # "touch" data file.
        with open(self.data._datafile, 'w+') as handle:
            json.dump({'old': 'stuff'}, handle)

        self.data.set('key', 'value')

        assert self.data.get('key') == 'value'
        assert self.data.get_data() == {'old': 'stuff', 'key': 'value'}
        self.assert0600()

    def test_set_first_time(self):
        self.data.set('key', 'value')

        assert self.data.get('key') == 'value'
        self.assert0600()

    def test_path_attribute(self):
        assert self.data.path == self.lists_path


class TestGetDataPath(ConfigTest):
    def setUp(self):
        super().setUp()
        self.main_config = schema.MainSectionConfig(targets=[])

    def assertDataPath(self, expected_datapath):
        assert expected_datapath == data.get_data_path(self.main_config.taskrc)

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
        assert 'TASKDATA' not in os.environ
        self.assertDataPath(self.lists_path)

    def test_unassigned(self):
        """
        When data path is not assigned, use default location.
        """
        # Empty taskrc.
        with open(self.taskrc, 'w'):
            pass

        assert 'TASKDATA' not in os.environ

        self.assertDataPath(os.path.expanduser('~/.task'))
