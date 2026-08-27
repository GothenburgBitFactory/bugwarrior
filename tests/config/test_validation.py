from pathlib import Path
import typing

import pydantic
import pytest

from bugwarrior import config
from bugwarrior.config import validation
from bugwarrior.config.load import format_config, parse_file

from ..base import DumbConfig, DumbService, register_services, validate


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
    filter_merge_requests: bool | typing.Literal["Undefined"] = "Undefined"
    include_merge_requests: bool | typing.Literal["Undefined"] = "Undefined"
    project_name: str = ""

    @pydantic.model_validator(mode="after")
    def require_username_or_query(self) -> "ValidationConfig":
        if not self.username and not self.query:
            raise ValueError("section requires one of:\n    username\n    query")
        return self


class ValidationService(DumbService):
    CONFIG_SCHEMA = ValidationConfig


class TestValidation:
    @pytest.fixture(autouse=True)
    def registered_services(self):
        with register_services({"test": ValidationService}):
            yield

    @pytest.fixture
    def config(self):
        return {
            "general": {"targets": ["my_service"]},
            "my_service": {"service": "test", "username": "ralph"},
        }

    def test_valid(self, config):
        validate(config)

    def test_main_section_required(self, config, caplog):
        del config["general"]

        formatted = format_config(config)
        with pytest.raises(SystemExit):
            validation.validate_config(formatted, "general", "configpath")

        assert len(caplog.records) == 1
        assert "No section: 'general'" in caplog.records[0].message

    def test_main_section_missing_targets_option(self, config, assert_validation_error):
        del config["general"]["targets"]

        assert_validation_error(config, "[general]\ntargets  <- Field required")

    def test_target_section_missing(self, config, assert_validation_error):
        del config["my_service"]

        assert_validation_error(
            config,
            "[general]\ntargets = ['my_service']  <- No [my_service] section found",
        )

    def test_service_missing(self, config, assert_validation_error):
        del config["my_service"]["service"]

        assert_validation_error(config, "No option 'service' in section: 'my_service'")

    def test_extra_field(self, config, assert_validation_error):
        """Undeclared fields are forbidden."""
        config["my_service"]["undeclared_field"] = "extra"

        assert_validation_error(
            config, "[my_service]\nundeclared_field = extra  <- unrecognized option"
        )

    def test_root_validator(self, config, assert_validation_error):
        del config["my_service"]["username"]

        assert_validation_error(
            config,
            "[my_service]  <- Value error, section requires one of:\n    username\n    query",
        )

    def test_no_scheme_url_validator_default(self, config):
        service_config = validate(config).service_configs[0]
        assert service_config.host == "example.com"

    def test_no_scheme_url_validator_set(self, config):
        config["my_service"]["host"] = "example.com"
        service_config = validate(config).service_configs[0]
        assert service_config.host == "example.com"

    def test_no_scheme_url_validator_scheme(self, config, assert_validation_error):
        config["my_service"]["host"] = "https://example.com"
        assert_validation_error(
            config,
            "host = https://example.com  <- URL should not include scheme ('https')",
        )

    def test_stripped_trailing_slash_url(self, config):
        config["my_service"]["url"] = "https://example.org/"
        service_config = validate(config).service_configs[0]
        assert service_config.url == "https://example.org"

    def test_deprecated_filter_merge_requests(self, config):
        service_config = validate(config).service_configs[0]
        assert service_config.include_merge_requests is True

        config["my_service"]["filter_merge_requests"] = "true"
        service_config = validate(config).service_configs[0]
        assert service_config.include_merge_requests is False

    def test_deprecated_filter_merge_requests_and_include_merge_requests(
        self, config, assert_validation_error
    ):
        config["my_service"]["filter_merge_requests"] = "true"
        config["my_service"]["include_merge_requests"] = "true"
        assert_validation_error(
            config, "filter_merge_requests and include_merge_requests are incompatible."
        )

    def test_deprecated_project_name(self, config):
        """We're just testing that deprecation doesn't break validation."""
        config["my_service"]["project_name"] = "myproject"
        validate(config)

    def test_flavors(self, config):
        config["flavor"] = {"myflavor": {"targets": ["my_service"]}}
        validate(config)

    def test_quoted_flavor_key_error(self, config, assert_validation_error):
        """Using ["flavor.myflavor"] instead of [flavor.myflavor] raises an error."""
        config["flavor.myflavor"] = {"targets": ["my_service"]}
        assert_validation_error(
            config, '["flavor.myflavor"]  <- Did you mean [flavor.myflavor]?'
        )

    def test_hooks_invalid_option(self, config, assert_validation_error):
        config["hooks"] = {"invalid_option": "value"}
        assert_validation_error(
            config, "[hooks]\ninvalid_option = value  <- unrecognized option"
        )

    def test_notifications_invalid_backend(self, config, assert_validation_error):
        config["notifications"] = {"backend": "invalid_backend"}
        assert_validation_error(
            config,
            "[notifications]\nbackend = invalid_backend  <- Input should be "
            "'gobject', 'growlnotify' or 'applescript'",
        )

    def test_service_and_hooks_errors_reported_together(
        self, config, assert_validation_error
    ):
        del config["my_service"]["service"]
        config["hooks"] = {"invalid_option": "value"}
        assert_validation_error(config, "No option 'service' in section: 'my_service'")
        assert_validation_error(
            config, "[hooks]\ninvalid_option = value  <- unrecognized option"
        )


class TestExampleFiles:
    """
    Validates the shipped example configs against the real services.

    Separate from TestValidation so it does not register the fake services.
    """

    @pytest.mark.parametrize(
        "config_name", ["example-bugwarrior.toml", "example-bugwarriorrc"]
    )
    @pytest.mark.parametrize(
        ("main_section", "expected_configs"),
        [
            (
                "general",
                {
                    "GithubConfig",
                    "GitlabConfig",
                    "GmailConfig",
                    "JiraConfig",
                    "KanboardConfig",
                    "PhabricatorConfig",
                    "PivotalTrackerConfig",
                    "RedMineConfig",
                    "TracConfig",
                },
            ),
            ("myflavor", {"GitlabConfig", "JiraConfig", "GithubConfig"}),
        ],
    )
    def test_load_and_validate_example_files(
        self, config_name, main_section, expected_configs
    ):
        config_path = Path(__file__).parent / config_name
        formatted_config = parse_file(str(config_path))

        config = validation.validate_config(
            formatted_config, main_section, str(config_path)
        )
        assert {
            conf.__class__.__name__ for conf in config.service_configs
        } == expected_configs
