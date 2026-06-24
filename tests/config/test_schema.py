import importlib
from importlib.metadata import entry_points
import os
from pathlib import Path
import re
import unittest

import pydantic
from pydantic import TypeAdapter
import pytest

from bugwarrior.config import schema

from ..base import ConfigTest, DumbConfig


class TestExpandedPath(unittest.TestCase):
    def setUp(self):
        self.adapter = TypeAdapter(schema.ExpandedPath)
        self.dir = os.getcwd()
        os.chdir(os.path.expanduser('~'))
        self.log = Path('./bugwarrior.log').absolute()

    def test_log(self):
        filename = os.path.join(os.path.expandvars('$HOME'), self.log)
        assert self.adapter.validate_python(filename) == self.log

    def test_log_userhome(self):
        assert self.adapter.validate_python('~/bugwarrior.log') == self.log

    def test_log_envvar(self):
        assert self.adapter.validate_python('$HOME/bugwarrior.log') == self.log

    def tearDown(self):
        os.chdir(self.dir)


class TestConfigList:
    adapter = TypeAdapter(schema.ConfigList)

    def test_configlist(self):
        assert self.adapter.validate_python('project_bar,project_baz') == [
            'project_bar',
            'project_baz',
        ]

    def test_configlist_jinja(self):
        assert self.adapter.validate_python(
            "work, jira, {{jirastatus|lower|replace(' ','_')}}"
        ) == ['work', 'jira', "{{jirastatus|lower|replace(' ','_')}}"]


class TestTaskrcPath(ConfigTest):
    def setUp(self):
        super().setUp()
        self.config = {'general': {'targets': []}}

    def test_default_factory_default(self):
        config = self.validate()
        assert str(config.main.taskrc) == os.path.join(self.tempdir, '.taskrc')

    def test_default_factory_env_override(self):
        override = os.path.join(self.tempdir, 'override_taskrc')
        with open(override, 'w+') as fout:
            fout.write('data.location=%s\n' % self.lists_path)
        os.environ['TASKRC'] = override

        config = self.validate()
        assert str(config.main.taskrc) == override

    def test_default_factory_xdg_config_home(self):
        os.remove(self.taskrc)

        dot_config_task = os.path.join(self.tempdir, '.config', 'task')
        os.makedirs(dot_config_task)
        taskrc = os.path.join(dot_config_task, 'taskrc')
        with open(taskrc, 'w+') as fout:
            fout.write('data.location=%s\n' % self.lists_path)

        config = self.validate()
        assert str(config.main.taskrc) == taskrc

    def test_default_factory_dot_config_taskrc(self):
        """Taskrc is still found if XDG_CONFIG_HOME is unset."""
        os.remove(self.taskrc)

        dot_config_task = os.path.join(self.tempdir, '.config', 'task')
        os.makedirs(dot_config_task)
        taskrc = os.path.join(dot_config_task, 'taskrc')
        with open(taskrc, 'w+') as fout:
            fout.write('data.location=%s\n' % self.lists_path)
        del os.environ['XDG_CONFIG_HOME']

        config = self.validate()
        assert str(config.main.taskrc) == taskrc

    def test_no_taskrc_file_found(self):
        os.remove(self.taskrc)

        with pytest.raises(OSError, match=r"Unable to find taskrc file\."):
            self.validate()


class TestUnsupportedOption:
    adapter = TypeAdapter(schema.UnsupportedOption[str])

    def test_unsupportedoption_falsey(self):
        assert self.adapter.validate_python('') == ''

    def test_unsupportedoption_truthy(self):
        with pytest.raises(pydantic.ValidationError):
            self.adapter.validate_python('foo')


class TestComputeTemplates:
    def test_template(self):
        raw_values = {'templates': {}, 'project_template': 'foo'}
        computed_values = DumbConfig.compute_templates(raw_values)
        assert computed_values['templates'] == {'project': 'foo'}

    def test_empty_template(self):
        """
        Respect setting field templates to an empty string.

        This should not be ignored but should make the corresponding task field
        an empty string.

        https://github.com/ralphbean/bugwarrior/issues/970
        """
        raw_values = {'templates': {}, 'project_template': ''}
        computed_values = DumbConfig.compute_templates(raw_values)
        assert computed_values['templates'] == {'project': ''}


class TestServices(unittest.TestCase):
    def test_common_configuration_options(self):
        """
        Cheaply check that each service at least references all of the common
        configuration options, if for no other reason than to throw a
        validation error if they are not supported.
        """
        for e in entry_points(group='bugwarrior.service'):
            with self.subTest(service=e.name):
                service_file = importlib.import_module(e.module).__file__
                with open(service_file, 'r') as f:
                    service_code = f.read()
                for option in ['only_if_assigned', 'also_unassigned']:
                    with self.subTest(option=option):
                        assert re.search(option, service_code) is not None, (
                            f'\
Service should support common configuration option self.config.{option}'
                        )

                # get_priority() makes use of the default_priority option
                with self.subTest(option='default_priority'):
                    assert (
                        re.search('default_priority', service_code)
                        or re.search('get_priority', service_code)
                    ) is not None, (
                        '\
Service should support self.config.default_priority or use self.get_priority()'
                    )
