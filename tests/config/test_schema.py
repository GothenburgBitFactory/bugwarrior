import os
import unittest

from bugwarrior.config import schema, load

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


class TestValidation(ConfigTest):
    def setUp(self):
        super().setUp()
        self.config = load.BugwarriorConfigParser()
        self.config.add_section('general')
        self.config.set('general', 'targets', 'my_service, my_kan, my_gitlab')
        self.config.add_section('my_service')
        self.config.set('my_service', 'service', 'github')
        self.config.set('my_service', 'github.login', 'ralph')
        self.config.set('my_service', 'github.username', 'ralph')
        self.config.set('my_service', 'github.password', 'abc123')
        self.config.add_section('my_kan')
        self.config.set('my_kan', 'service', 'kanboard')
        self.config.set(
            'my_kan', 'kanboard.url', 'https://kanboard.example.org')
        self.config.set('my_kan', 'kanboard.username', 'ralph')
        self.config.set('my_kan', 'kanboard.password', 'abc123')
        self.config.add_section('my_gitlab')
        self.config.set('my_gitlab', 'service', 'gitlab')
        self.config.set('my_gitlab', 'gitlab.host', 'my-git.org')
        self.config.set('my_gitlab', 'gitlab.login', 'arbitrary_login')
        self.config.set('my_gitlab', 'gitlab.token', 'arbitrary_token')

    def test_valid(self):
        self.validate()

    def test_main_section_required(self):
        self.config.remove_section('general')

        self.assertValidationError("No section: 'general'")

    def test_main_section_missing_targets_option(self):
        self.config.remove_option('general', 'targets')

        self.assertValidationError("No option 'targets' in section: 'general'")

    def test_target_section_missing(self):
        self.config.remove_section('my_service')

        self.assertValidationError("No section: 'my_service'")

    def test_service_missing(self):
        self.config.remove_option('my_service', 'service')

        self.assertValidationError(
            "No option 'service' in section: 'my_service'")

    def test_missing_prefix(self):
        # set improperly scoped field
        self.config.set('my_service', 'also_unassigned', 'True')

        self.assertValidationError(
            "[my_service]\nalso_unassigned  <- "
            "expected prefix 'github': did you mean 'github.also_unassigned'?")

    def test_wrong_prefix(self):
        # set improperly scoped field
        self.config.set('my_service', 'fake.also_unassigned', 'True')

        self.assertValidationError(
            "[my_service]\nfake.also_unassigned  <- "
            "expected prefix 'github': did you mean 'github.also_unassigned'?")

    def test_extra_field(self):
        """ Undeclared fields are forbidden. """
        self.config.set('my_service', 'github.undeclared_field', 'extra')

        self.assertValidationError(
            '[my_service]\n'
            'github.undeclared_field  <- unrecognized option')

    def test_root_validator(self):
        self.config.remove_option('my_service', 'github.password')

        self.assertValidationError(
            '[my_service]  <- section requires one of:'
            '\ngithub.token\ngithub.password')

    def test_no_scheme_url_validator_default(self):
        conf = self.validate()
        self.assertEqual(conf['my_service'].host, 'github.com')

    def test_no_scheme_url_validator_set(self):
        self.config.set('my_service', 'github.host', 'github.com')
        conf = self.validate()
        self.assertEqual(conf['my_service'].host, 'github.com')

    def test_no_scheme_url_validator_scheme(self):
        self.config.set('my_service', 'github.host', 'https://github.com')
        self.assertValidationError(
            "github.host  <- URL should not include scheme ('https')")

    def test_stripped_trailing_slash_url(self):
        self.config.set(
            'my_kan', 'kanboard.url', 'https://kanboard.example.org/')
        conf = self.validate()
        self.assertEqual(conf['my_kan'].url, 'https://kanboard.example.org')

    def test_deprecated_filter_merge_requests(self):
        conf = self.validate()
        self.assertEqual(conf['my_gitlab'].include_merge_requests, True)

        self.config.set('my_gitlab', 'gitlab.filter_merge_requests', 'true')
        conf = self.validate()
        self.assertEqual(conf['my_gitlab'].include_merge_requests, False)

    def test_deprecated_filter_merge_requests_and_include_merge_requests(self):
        self.config.set('my_gitlab', 'gitlab.filter_merge_requests', 'true')
        self.config.set('my_gitlab', 'gitlab.include_merge_requests', 'true')
        self.assertValidationError(
            '[my_gitlab]  <- filter_merge_requests and include_merge_requests are incompatible.')

    def test_deprecated_project_name(self):
        """ We're just testing that deprecation doesn't break validation. """
        self.config.set('general', 'targets', 'my_service, my_kan, my_gitlab, my_redmine')
        self.config.add_section('my_redmine')
        self.config.set('my_redmine', 'service', 'redmine')
        self.config.set('my_redmine', 'redmine.url', 'https://example.com')
        self.config.set('my_redmine', 'redmine.key', 'mykey')
        self.validate()

        self.config.set('my_redmine', 'redmine.project_name', 'myproject')
        self.validate()
