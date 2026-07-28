import json
import os
from pathlib import Path

import pytest

from bugwarrior.config import data, schema


def assert_0600(bw_data):
    permissions = oct(os.stat(bw_data._datafile).st_mode & 0o777)
    assert permissions == "0o600"


class TestData:
    @pytest.fixture
    def bw_data(self, config_environment):
        return data.BugwarriorData(config_environment.lists_path)

    def test_get_set(self, bw_data):
        # "touch" data file.
        with open(bw_data._datafile, "w+") as handle:
            json.dump({"old": "stuff"}, handle)

        bw_data.set("key", "value")

        assert bw_data.get("key") == "value"
        assert bw_data.get_data() == {"old": "stuff", "key": "value"}
        assert_0600(bw_data)

    def test_set_first_time(self, bw_data):
        bw_data.set("key", "value")

        assert bw_data.get("key") == "value"
        assert_0600(bw_data)

    def test_path_attribute(self, bw_data, config_environment):
        assert bw_data.path == config_environment.lists_path


class TestGetDataPath:
    @pytest.fixture
    def main_config(self):
        return schema.MainSectionConfig(targets=[])

    def assert_data_path(self, main_config, expected_datapath):
        assert str(expected_datapath) == data.get_data_path(main_config.taskrc)

    def test_TASKDATA(self, main_config, monkeypatch, tmp_path):
        """
        TASKDATA should be respected, even when taskrc's data.location is set.
        """
        datapath = tmp_path / "data"
        monkeypatch.setenv("TASKDATA", str(datapath))
        self.assert_data_path(main_config, datapath)

    def test_taskrc_datalocation(self, main_config, config_environment):
        """
        When TASKDATA is not set, data.location in taskrc should be respected.
        """
        assert "TASKDATA" not in os.environ
        self.assert_data_path(main_config, config_environment.lists_path)

    def test_unassigned(self, main_config, config_environment):
        """
        When data path is not assigned, use default location.
        """
        # Empty taskrc.
        config_environment.taskrc.write_text("")

        assert "TASKDATA" not in os.environ

        self.assert_data_path(main_config, Path.home() / ".task")
