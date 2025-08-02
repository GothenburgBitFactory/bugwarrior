import importlib
import os
import re
import unittest

from importlib_metadata import entry_points

from bugwarrior.config import schema

from ..base import ConfigTest


class TestLoggingPath(unittest.TestCase):
    def setUp(self):
        self.dir = os.getcwd()
        os.chdir(os.path.expanduser('~'))

    def test_log_relative_path(self):
        self.assertEqual(
            schema.LoggingPath.validate('bugwarrior.log'),
            'bugwarrior.log',
        )

    def test_log_absolute_path(self):
        filename = os.path.join(os.path.expandvars('$HOME'), 'bugwarrior.log')
        self.assertEqual(
            schema.LoggingPath.validate(filename),
            'bugwarrior.log',
        )

    def test_log_userhome(self):
        self.assertEqual(
            schema.LoggingPath.validate('~/bugwarrior.log'),
            'bugwarrior.log',
        )

    def test_log_envvar(self):
        self.assertEqual(
            schema.LoggingPath.validate('$HOME/bugwarrior.log'),
            'bugwarrior.log',
        )

    def tearDown(self):
        os.chdir(self.dir)


class TestConfigList(unittest.TestCase):
    def test_configlist(self):
        self.assertEqual(
            schema.ConfigList.validate('project_bar,project_baz'),
            ['project_bar', 'project_baz']
        )

    def test_configlist_jinja(self):
        self.assertEqual(
            schema.ConfigList.validate(
                "work, jira, {{jirastatus|lower|replace(' ','_')}}"),
            ['work', 'jira', "{{jirastatus|lower|replace(' ','_')}}"]
        )


class TestTaskrcPath(ConfigTest):
    def setUp(self):
        super().setUp()
        self.config = {
            'general': {'targets': []},
        }

    def test_default_factory_default(self):
        config = self.validate()
        self.assertEqual(config['general'].taskrc,
                         os.path.join(self.tempdir, '.taskrc'))

    def test_default_factory_env_override(self):
        override = os.path.join(self.tempdir, 'override_taskrc')
        with open(override, 'w+') as fout:
            fout.write('data.location=%s\n' % self.lists_path)
        os.environ['TASKRC'] = override

        config = self.validate()
        self.assertEqual(config['general'].taskrc, override)

    def test_default_factory_xdg_config_home(self):
        os.remove(self.taskrc)

        dot_config_task = os.path.join(self.tempdir, '.config', 'task')
        os.makedirs(dot_config_task)
        taskrc = os.path.join(dot_config_task, 'taskrc')
        with open(taskrc, 'w+') as fout:
            fout.write('data.location=%s\n' % self.lists_path)

        config = self.validate()
        self.assertEqual(config['general'].taskrc, taskrc)

    def test_default_factory_dot_config_taskrc(self):
        """ Taskrc is still found if XDG_CONFIG_HOME is unset. """
        os.remove(self.taskrc)

        dot_config_task = os.path.join(self.tempdir, '.config', 'task')
        os.makedirs(dot_config_task)
        taskrc = os.path.join(dot_config_task, 'taskrc')
        with open(taskrc, 'w+') as fout:
            fout.write('data.location=%s\n' % self.lists_path)
        del os.environ['XDG_CONFIG_HOME']

        config = self.validate()
        self.assertEqual(config['general'].taskrc, taskrc)

    def test_no_taskrc_file_found(self):
        os.remove(self.taskrc)

        with self.assertRaisesRegex(OSError, r"Unable to find taskrc file\."):
            self.validate()


class TestUnsupportedOption(unittest.TestCase):
    def test_unsupportedoption_falsey(self):
        self.assertEqual(schema.UnsupportedOption.validate(''), '')

    def test_unsupportedoption_truthy(self):
        with self.assertRaises(ValueError):
            schema.UnsupportedOption.validate('foo')


class TestValidation(ConfigTest):
    def setUp(self):
        super().setUp()
        self.config = {
            'general': {'targets': ['my_service', 'my_kan', 'my_gitlab']},
            'my_service': {
                'service': 'github',
                'login': 'ralph',
                'username': 'ralph',
                'token': 'abc123',
            },
            'my_kan': {
                'service': 'kanboard',
                'url': 'https://kanboard.example.org',
                'username': 'ralph',
                'password': 'abc123',
            },
            'my_gitlab': {
                'service': 'gitlab',
                'host': 'my-git.org',
                'login': 'arbitrary_login',
                'token': 'arbitrary_token',
                'owned': 'false',
            },
        }

    def test_valid(self):
        self.validate()

    def test_main_section_required(self):
        del self.config['general']

        with self.assertRaises(SystemExit):
            schema.validate_config(self.config, 'general', 'configpath')

        self.assertEqual(len(self.caplog.records), 1)
        self.assertIn("No section: 'general'", self.caplog.records[0].message)

    def test_main_section_missing_targets_option(self):
        del self.config['general']['targets']

        self.assertValidationError("No option 'targets' in section: 'general'")

    def test_target_section_missing(self):
        del self.config['my_service']

        self.assertValidationError("No section: 'my_service'")

    def test_service_missing(self):
        del self.config['my_service']['service']

        self.assertValidationError(
            "No option 'service' in section: 'my_service'")

    def test_extra_field(self):
        """ Undeclared fields are forbidden. """
        self.config['my_service']['undeclared_field'] = 'extra'

        self.assertValidationError(
            '[my_service]\n'
            'undeclared_field  <- unrecognized option')

    def test_root_validator(self):
        del self.config['my_service']['username']

        self.assertValidationError(
            '[my_service]  <- '
            'section requires one of:\n    username\n    query')

    def test_no_scheme_url_validator_default(self):
        conf = self.validate()
        self.assertEqual(conf['my_service'].host, 'github.com')

    def test_no_scheme_url_validator_set(self):
        self.config['my_service']['host'] = 'github.com'
        conf = self.validate()
        self.assertEqual(conf['my_service'].host, 'github.com')

    def test_no_scheme_url_validator_scheme(self):
        self.config['my_service']['host'] = 'https://github.com'
        self.assertValidationError(
            "host  <- URL should not include scheme ('https')")

    def test_stripped_trailing_slash_url(self):
        self.config['my_kan']['url'] = 'https://kanboard.example.org/'
        conf = self.validate()
        self.assertEqual(conf['my_kan'].url, 'https://kanboard.example.org')

    def test_deprecated_filter_merge_requests(self):
        conf = self.validate()
        self.assertEqual(conf['my_gitlab'].include_merge_requests, True)

        self.config['my_gitlab']['filter_merge_requests'] = 'true'
        conf = self.validate()
        self.assertEqual(conf['my_gitlab'].include_merge_requests, False)

    def test_deprecated_filter_merge_requests_and_include_merge_requests(self):
        self.config['my_gitlab']['filter_merge_requests'] = 'true'
        self.config['my_gitlab']['include_merge_requests'] = 'true'
        self.assertValidationError(
            '[my_gitlab]  <- filter_merge_requests and include_merge_requests are incompatible.')

    def test_deprecated_project_name(self):
        """ We're just testing that deprecation doesn't break validation. """
        self.config['general']['targets'] = ['my_service', 'my_kan', 'my_gitlab', 'my_redmine']
        self.config['my_redmine'] = {
            'service': 'redmine',
            'url': 'https://example.com',
            'key': 'mykey',
        }
        self.validate()

        self.config['my_redmine']['project_name'] = 'myproject'
        self.validate()


class TestComputeTemplates(unittest.TestCase):
    def test_template(self):
        raw_values = {'templates': {}, 'project_template': 'foo'}
        computed_values = schema.ServiceConfig().compute_templates(raw_values)
        self.assertEqual(computed_values['templates'], {'project': 'foo'})

    def test_empty_template(self):
        """
        Respect setting field templates to an empty string.

        This should not be ignored but should make the corresponding task field
        an empty string.

        https://github.com/ralphbean/bugwarrior/issues/970
        """
        raw_values = {'templates': {}, 'project_template': ''}
        computed_values = schema.ServiceConfig().compute_templates(raw_values)
        self.assertEqual(computed_values['templates'], {'project': ''})


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
                        self.assertIsNotNone(
                            re.search(option, service_code),
                            msg=f'\
Service should support common configuration option self.config.{option}')

                # get_priority() makes use of the default_priority option
                with self.subTest(option='default_priority'):
                    self.assertIsNotNone(
                        re.search('default_priority', service_code) or
                        re.search('get_priority', service_code),
                        msg='\
Service should support self.config.default_priority or use self.get_priority()'
                    )
