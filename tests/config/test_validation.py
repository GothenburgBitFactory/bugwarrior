from pathlib import Path

from bugwarrior.config import validation
from bugwarrior.config.load import format_config, parse_file

from ..base import ConfigTest


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
            formatted = format_config(self.config)
            validation.validate_config(formatted, 'general', 'configpath')

        self.assertEqual(len(self.caplog.records), 1)
        self.assertIn("No section: 'general'", self.caplog.records[0].message)

    def test_main_section_missing_targets_option(self):
        del self.config['general']['targets']

        self.assertValidationError("[general]\ntargets  <- Field required")

    def test_target_section_missing(self):
        del self.config['my_service']

        self.assertValidationError("[general] missing targets: my_service")

    def test_service_missing(self):
        del self.config['my_service']['service']

        self.assertValidationError("No option 'service' in section: 'my_service'")

    def test_extra_field(self):
        """Undeclared fields are forbidden."""
        self.config['my_service']['undeclared_field'] = 'extra'

        self.assertValidationError(
            '[my_service]\nundeclared_field = extra  <- unrecognized option'
        )

    def test_root_validator(self):
        del self.config['my_service']['username']

        self.assertValidationError(
            '[my_service]  <- Value error, section requires one of:\n    username\n    query'
        )

    def test_no_scheme_url_validator_default(self):
        conf = self.validate()
        service_config = next(
            service_config
            for service_config in conf.service_configs
            if service_config.target == "my_service"
        )
        self.assertEqual(service_config.host, 'github.com')

    def test_no_scheme_url_validator_set(self):
        self.config['my_service']['host'] = 'github.com'
        conf = self.validate()
        service_config = next(
            service_config
            for service_config in conf.service_configs
            if service_config.target == "my_service"
        )
        self.assertEqual(service_config.host, 'github.com')

    def test_no_scheme_url_validator_scheme(self):
        self.config['my_service']['host'] = 'https://github.com'
        self.assertValidationError(
            "host = https://github.com  <- URL should not include scheme ('https')"
        )

    def test_stripped_trailing_slash_url(self):
        self.config['my_kan']['url'] = 'https://kanboard.example.org/'
        conf = self.validate()
        service_config = next(
            service_config
            for service_config in conf.service_configs
            if service_config.target == "my_kan"
        )
        self.assertEqual(service_config.url, 'https://kanboard.example.org')

    def test_deprecated_filter_merge_requests(self):
        conf = self.validate()
        service_config = next(
            service_config
            for service_config in conf.service_configs
            if service_config.target == "my_gitlab"
        )
        self.assertEqual(service_config.include_merge_requests, True)

        self.config['my_gitlab']['filter_merge_requests'] = 'true'
        conf = self.validate()
        service_config = next(
            service_config
            for service_config in conf.service_configs
            if service_config.target == "my_gitlab"
        )
        self.assertEqual(service_config.include_merge_requests, False)

    def test_deprecated_filter_merge_requests_and_include_merge_requests(self):
        self.config['my_gitlab']['filter_merge_requests'] = 'true'
        self.config['my_gitlab']['include_merge_requests'] = 'true'
        self.assertValidationError(
            'filter_merge_requests and include_merge_requests are incompatible.'
        )

    def test_deprecated_project_name(self):
        """We're just testing that deprecation doesn't break validation."""
        self.config['general']['targets'] = [
            'my_service',
            'my_kan',
            'my_gitlab',
            'my_redmine',
        ]
        self.config['my_redmine'] = {
            'service': 'redmine',
            'url': 'https://example.com',
            'key': 'mykey',
        }
        self.validate()

        self.config['my_redmine']['project_name'] = 'myproject'
        self.validate()

    def test_flavors(self):
        self.config['flavor'] = {'myflavor': {'targets': ['my_service', 'my_gitlab']}}
        self.validate()

    def test_quoted_flavor_key_error(self):
        """Using ["flavor.myflavor"] instead of [flavor.myflavor] raises an error."""
        self.config['flavor.myflavor'] = {'targets': ['my_service']}
        self.assertValidationError(
            '["flavor.myflavor"]  <- Did you mean [flavor.myflavor]?'
        )

    def test_load_and_validate_example_toml(self):
        config_path = Path(__file__).parent / 'example-bugwarrior.toml'
        raw_config = parse_file(str(config_path))
        config = validation.validate_config(raw_config, 'general', str(config_path))

        self.assertEqual(
            {conf.__class__.__name__ for conf in config.service_configs},
            {
                'GithubConfig',
                'GitlabConfig',
                'GmailConfig',
                'JiraConfig',
                'KanboardConfig',
                'PhabricatorConfig',
                'PivotalTrackerConfig',
                'RedMineConfig',
                'TracConfig',
            },
        )

    def test_hooks_invalid_option(self):
        self.config['hooks'] = {'invalid_option': 'value'}
        self.assertValidationError(
            '[hooks]\ninvalid_option = value  <- unrecognized option'
        )

    def test_notifications_invalid_backend(self):
        self.config['notifications'] = {'backend': 'invalid_backend'}
        self.assertValidationError(
            "[notifications]\nbackend = invalid_backend  <- Input should be "
            "'gobject', 'growlnotify' or 'applescript'"
        )

    def test_service_and_hooks_errors_reported_together(self):
        del self.config['my_service']['service']
        self.config['hooks'] = {'invalid_option': 'value'}
        self.assertValidationError("No option 'service' in section: 'my_service'")
        self.assertValidationError(
            '[hooks]\ninvalid_option = value  <- unrecognized option'
        )
