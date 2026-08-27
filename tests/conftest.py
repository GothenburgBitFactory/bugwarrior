import dataclasses
import pathlib

import pytest

from bugwarrior import config

from .base import validate


@dataclasses.dataclass
class ConfigEnvironment:
    """Temporary taskwarrior configuration created for each test."""

    taskrc: pathlib.Path
    lists_path: pathlib.Path


@pytest.fixture(autouse=True)
def config_environment(tmp_path, monkeypatch):
    """
    Isolate every test from the user's real taskwarrior environment.

    Creates a temporary taskrc and data location and points HOME and
    XDG_CONFIG_HOME at the temporary directory. Request this fixture by
    name to access the generated paths.
    """
    lists_path = tmp_path / "lists"
    lists_path.mkdir()
    taskrc = tmp_path / ".taskrc"
    taskrc.write_text(f"data.location={lists_path}\n")

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
    monkeypatch.delenv(config.BUGWARRIORRC, raising=False)
    monkeypatch.delenv("TASKRC", raising=False)
    monkeypatch.delenv("XDG_CONFIG_DIRS", raising=False)

    return ConfigEnvironment(taskrc=taskrc, lists_path=lists_path)


@pytest.fixture
def assert_validation_error(caplog):
    """
    Return a callable asserting that a config fails validation.

    The callable validates the given config dictionary, expecting a fatal
    exit with a single log record containing the expected message.
    """

    def check(config, expected):
        with pytest.raises(SystemExit):
            validate(config)

        # Only one message should be logged.
        assert len(caplog.records) == 1

        assert expected in caplog.records[0].message

        # We may want to use this assertion more than once per test.
        caplog.clear()

    return check
