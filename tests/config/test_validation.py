from pathlib import Path
import typing

import pydantic
import pytest

from bugwarrior import config
from bugwarrior.config import validation
from bugwarrior.config.load import format_config, parse_file

from ..base import ConfigTest, DumbConfig, DumbService, register_services


class ValidationConfig(DumbConfig):
    """
    A richer fake config exercising the generic validators under test.
    """

    host: config.NoSchemeUrl = "example.com"
    url: config.StrippedTrailingSlashUrl = "https://example.org"
    username: str = ""
    query: str = ""

    _DEPRECATE_FILTER_MERGE_REQUESTS = True
    _DEPRECATE_PROJECT_NAME = True
    filter_merge_requests: typing.Union[bool, typing.Literal["Undefined"]] = "Undefined"
    include_merge_requests: typing.Union[bool, typing.Literal["Undefined"]] = (
        "Undefined"
    )
    project_name: str = ""

    @pydantic.model_validator(mode="after")
    def require_username_or_query(self) -> "ValidationConfig":
        if not self.username and not self.query:
            raise ValueError("section requires one of:\n    username\n    query")
        return self


class ValidationService(DumbService):
    CONFIG_SCHEMA = ValidationConfig


class TestValidation(ConfigTest):
    def setUp(self):
        super().setUp()
        self.enterContext(register_services({"test": ValidationService}))
        self.config = {
            "general": {"targets": ["my_service"]},
            "my_service": {"service": "test", "username": "ralph"},
        }

    def test_valid(self):
        self.validate()

    def test_main_section_required(self):
        del self.config['general']

        with pytest.raises(SystemExit):
            formatted = format_config(self.config)
            validation.validate_config(formatted, 'general', 'configpath')

        assert len(self.caplog.records) == 1
        assert "No section: 'general'" in self.caplog.records[0].message

    def test_main_section_missing_targets_option(self):
        del self.config['general']['targets']

        self.assertValidationError("[general]\ntargets  <- Field required")

    def test_target_section_missing(self):
        del self.config['my_service']

        self.assertValidationError(
            "[general]\ntargets = ['my_service']  <- No [my_service] section found"
        )

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
        service_config = self.validate().service_configs[0]
        assert service_config.host == 'example.com'

    def test_no_scheme_url_validator_set(self):
        self.config['my_service']['host'] = 'example.com'
        service_config = self.validate().service_configs[0]
        assert service_config.host == 'example.com'

    def test_no_scheme_url_validator_scheme(self):
        self.config['my_service']['host'] = 'https://example.com'
        self.assertValidationError(
            "host = https://example.com  <- URL should not include scheme ('https')"
        )

    def test_stripped_trailing_slash_url(self):
        self.config['my_service']['url'] = 'https://example.org/'
        service_config = self.validate().service_configs[0]
        assert service_config.url == 'https://example.org'

    def test_deprecated_filter_merge_requests(self):
        service_config = self.validate().service_configs[0]
        assert service_config.include_merge_requests is True

        self.config['my_service']['filter_merge_requests'] = 'true'
        service_config = self.validate().service_configs[0]
        assert service_config.include_merge_requests is False

    def test_deprecated_filter_merge_requests_and_include_merge_requests(self):
        self.config['my_service']['filter_merge_requests'] = 'true'
        self.config['my_service']['include_merge_requests'] = 'true'
        self.assertValidationError(
            'filter_merge_requests and include_merge_requests are incompatible.'
        )

    def test_deprecated_project_name(self):
        """We're just testing that deprecation doesn't break validation."""
        self.config['my_service']['project_name'] = 'myproject'
        self.validate()

    def test_flavors(self):
        self.config['flavor'] = {'myflavor': {'targets': ['my_service']}}
        self.validate()

    def test_quoted_flavor_key_error(self):
        """Using ["flavor.myflavor"] instead of [flavor.myflavor] raises an error."""
        self.config['flavor.myflavor'] = {'targets': ['my_service']}
        self.assertValidationError(
            '["flavor.myflavor"]  <- Did you mean [flavor.myflavor]?'
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


class TestExampleFiles(ConfigTest):
    """
    Validates the shipped example configs against the real services.

    Separate from TestValidation so it does not register the fake services.
    """

    def test_load_and_validate_example_files(self):
        example_dir = Path(__file__).parent
        config_files = [
            example_dir / 'example-bugwarrior.toml',
            example_dir / 'example-bugwarriorrc',
        ]
        expected_by_flavor = {
            'general': {
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
            'myflavor': {'GitlabConfig', 'JiraConfig', 'GithubConfig'},
        }
        for config_path in config_files:
            for main_section, expected_configs in expected_by_flavor.items():
                with self.subTest(config=config_path.name, main_section=main_section):
                    formatted_config = parse_file(str(config_path))

                    config = validation.validate_config(
                        formatted_config, main_section, str(config_path)
                    )
                    assert {
                        conf.__class__.__name__ for conf in config.service_configs
                    } == expected_configs
