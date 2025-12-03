import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pydantic
from pydantic_core import PydanticCustomError

from bugwarrior.config.schema import (
    ExpandedPath,
    LoggingPath,
    TaskrcPath,
    _validate_file_exists,
    get_default_taskrc,
)


class TestExpandedPath(unittest.TestCase):
    def test_expands_home_directory(self):
        class Model(pydantic.BaseModel):
            path: ExpandedPath

        model = Model(path='~/test.txt')
        self.assertNotIn('~', str(model.path))
        self.assertIn('test.txt', str(model.path))
        self.assertIsInstance(model.path, Path)

    def test_expands_env_var(self):
        os.environ['TEST_VAR'] = '/tmp/test'

        class Model(pydantic.BaseModel):
            path: ExpandedPath

        model = Model(path='$TEST_VAR/file.txt')
        self.assertEqual(str(model.path), '/tmp/test/file.txt')
        self.assertIsInstance(model.path, Path)
        del os.environ['TEST_VAR']


class TestLoggingPath(unittest.TestCase):
    def test_returns_relative_path(self):
        class Model(pydantic.BaseModel):
            path: LoggingPath

        model = Model(path='bugwarrior.log')
        self.assertIsInstance(model.path, Path)
        self.assertFalse(model.path.is_absolute())

    def test_produces_string_path(self):
        class Model(pydantic.BaseModel):
            path: LoggingPath

        model = Model(path='bugwarrior.log')
        self.assertEqual(str(model.path), 'bugwarrior.log')


class TestTaskrcPath(unittest.TestCase):
    def test_rejects_nonexistent_file(self):
        with self.assertRaises(Exception):
            _validate_file_exists(Path('/nonexistent/path/taskrc'))

    def test_expands_and_validates(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b'test')
            tmp_path = tmp.name

        try:

            class Model(pydantic.BaseModel):
                path: TaskrcPath

            model = Model(path=tmp_path)
            self.assertEqual(model.path, Path(tmp_path).resolve())
            self.assertIsInstance(model.path, Path)
        finally:
            Path(tmp_path).unlink()


class TestGetDefaultTaskrc(unittest.TestCase):
    def test_taskrc_env_var_set_and_file_exists(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b'test')
            tmp_path = tmp.name

        try:
            with patch.dict(os.environ, {'TASKRC': tmp_path}):
                result = get_default_taskrc()
                self.assertEqual(result, Path(tmp_path).resolve())
        finally:
            Path(tmp_path).unlink()

    def test_taskrc_env_var_set_but_file_not_exists(self):
        with patch.dict(os.environ, {'TASKRC': '/nonexistent/taskrc'}):
            with self.assertRaises(PydanticCustomError):
                get_default_taskrc()

    def test_home_taskrc_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_home = Path(tmpdir)
            taskrc = fake_home / '.taskrc'
            taskrc.write_text('test')

            with patch.dict(os.environ, {'TASKRC': ''}, clear=False):
                os.environ.pop('TASKRC', None)
                with patch.object(Path, 'home', return_value=fake_home):
                    result = get_default_taskrc()
                    self.assertEqual(result, taskrc)

    def test_xdg_config_home_set_and_taskrc_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_home = Path(tmpdir) / 'home'
            fake_home.mkdir()
            xdg_config = Path(tmpdir) / 'xdg_config'
            xdg_taskrc = xdg_config / 'task' / 'taskrc'
            xdg_taskrc.parent.mkdir(parents=True)
            xdg_taskrc.write_text('test')

            env = {'XDG_CONFIG_HOME': str(xdg_config)}
            with patch.dict(os.environ, env, clear=False):
                os.environ.pop('TASKRC', None)
                with patch.object(Path, 'home', return_value=fake_home):
                    result = get_default_taskrc()
                    self.assertEqual(result, xdg_taskrc)

    def test_xdg_config_home_set_but_taskrc_not_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_home = Path(tmpdir) / 'home'
            fake_home.mkdir()
            xdg_config = Path(tmpdir) / 'xdg_config'
            xdg_config.mkdir()

            env = {'XDG_CONFIG_HOME': str(xdg_config)}
            with patch.dict(os.environ, env, clear=False):
                os.environ.pop('TASKRC', None)
                with patch.object(Path, 'home', return_value=fake_home):
                    with self.assertRaises(OSError) as ctx:
                        get_default_taskrc()
                    self.assertIn("Unable to find taskrc", str(ctx.exception))

    def test_dotconfig_taskrc_exists_when_xdg_not_set(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_home = Path(tmpdir)
            dotconfig_taskrc = fake_home / '.config' / 'task' / 'taskrc'
            dotconfig_taskrc.parent.mkdir(parents=True)
            dotconfig_taskrc.write_text('test')

            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop('TASKRC', None)
                os.environ.pop('XDG_CONFIG_HOME', None)
                with patch.object(Path, 'home', return_value=fake_home):
                    result = get_default_taskrc()
                    self.assertEqual(result, dotconfig_taskrc)

    def test_no_taskrc_found_anywhere(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_home = Path(tmpdir)

            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop('TASKRC', None)
                os.environ.pop('XDG_CONFIG_HOME', None)
                with patch.object(Path, 'home', return_value=fake_home):
                    with self.assertRaises(OSError) as ctx:
                        get_default_taskrc()
                    self.assertIn("Unable to find taskrc", str(ctx.exception))
