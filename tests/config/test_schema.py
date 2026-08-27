import importlib
from importlib.metadata import entry_points
from pathlib import Path
import re

import pydantic
from pydantic import TypeAdapter
import pytest

from bugwarrior.config import schema

from ..base import DumbConfig, validate


class TestExpandedPath:
    adapter = TypeAdapter(schema.ExpandedPath)

    @pytest.fixture
    def log(self, monkeypatch):
        monkeypatch.chdir(Path.home())
        return Path("./bugwarrior.log").absolute()

    def test_log(self, log):
        assert self.adapter.validate_python(str(log)) == log

    def test_log_userhome(self, log):
        assert self.adapter.validate_python("~/bugwarrior.log") == log

    def test_log_envvar(self, log):
        assert self.adapter.validate_python("$HOME/bugwarrior.log") == log


class TestConfigList:
    adapter = TypeAdapter(schema.ConfigList)

    def test_configlist(self):
        assert self.adapter.validate_python("project_bar,project_baz") == [
            "project_bar",
            "project_baz",
        ]

    def test_configlist_jinja(self):
        assert self.adapter.validate_python(
            "work, jira, {{jirastatus|lower|replace(' ','_')}}"
        ) == ["work", "jira", "{{jirastatus|lower|replace(' ','_')}}"]


class TestTaskrcPath:
    @pytest.fixture
    def config(self):
        return {"general": {"targets": []}}

    def test_default_factory_default(self, config, config_environment):
        config = validate(config)
        assert config.main.taskrc == config_environment.taskrc

    def test_default_factory_env_override(
        self, config, config_environment, tmp_path, monkeypatch
    ):
        override = tmp_path / "override_taskrc"
        override.write_text(f"data.location={config_environment.lists_path}\n")
        monkeypatch.setenv("TASKRC", str(override))

        config = validate(config)
        assert config.main.taskrc == override

    def test_default_factory_xdg_config_home(
        self, config, config_environment, tmp_path
    ):
        config_environment.taskrc.unlink()

        dot_config_task = tmp_path / ".config" / "task"
        dot_config_task.mkdir(parents=True)
        taskrc = dot_config_task / "taskrc"
        taskrc.write_text(f"data.location={config_environment.lists_path}\n")

        config = validate(config)
        assert config.main.taskrc == taskrc

    def test_default_factory_dot_config_taskrc(
        self, config, config_environment, tmp_path, monkeypatch
    ):
        """Taskrc is still found if XDG_CONFIG_HOME is unset."""
        config_environment.taskrc.unlink()

        dot_config_task = tmp_path / ".config" / "task"
        dot_config_task.mkdir(parents=True)
        taskrc = dot_config_task / "taskrc"
        taskrc.write_text(f"data.location={config_environment.lists_path}\n")
        monkeypatch.delenv("XDG_CONFIG_HOME")

        config = validate(config)
        assert config.main.taskrc == taskrc

    def test_no_taskrc_file_found(self, config, config_environment):
        config_environment.taskrc.unlink()

        with pytest.raises(OSError, match=r"Unable to find taskrc file\."):
            validate(config)


class TestUnsupportedOption:
    adapter = TypeAdapter(schema.UnsupportedOption[str])

    def test_unsupportedoption_falsey(self):
        assert self.adapter.validate_python("") == ""

    def test_unsupportedoption_truthy(self):
        with pytest.raises(pydantic.ValidationError):
            self.adapter.validate_python("foo")


class TestComputeTemplates:
    def test_template(self):
        raw_values = {"templates": {}, "project_template": "foo"}
        computed_values = DumbConfig.compute_templates(raw_values)
        assert computed_values["templates"] == {"project": "foo"}

    def test_empty_template(self):
        """
        Respect setting field templates to an empty string.

        This should not be ignored but should make the corresponding task field
        an empty string.

        https://github.com/ralphbean/bugwarrior/issues/970
        """
        raw_values = {"templates": {}, "project_template": ""}
        computed_values = DumbConfig.compute_templates(raw_values)
        assert computed_values["templates"] == {"project": ""}


class TestServices:
    @pytest.mark.parametrize(
        "entry_point",
        [pytest.param(e, id=e.name) for e in entry_points(group="bugwarrior.service")],
    )
    def test_common_configuration_options(self, entry_point):
        """
        Cheaply check that each service at least references all of the common
        configuration options, if for no other reason than to throw a
        validation error if they are not supported.
        """
        service_file = importlib.import_module(entry_point.module).__file__
        with open(service_file, "r") as f:
            service_code = f.read()

        for option in ["only_if_assigned", "also_unassigned"]:
            assert re.search(option, service_code) is not None, (
                f"\
Service should support common configuration option self.config.{option}"
            )

        # get_priority() makes use of the default_priority option
        assert (
            re.search("default_priority", service_code)
            or re.search("get_priority", service_code)
        ) is not None, (
            "\
Service should support self.config.default_priority or use self.get_priority()"
        )
