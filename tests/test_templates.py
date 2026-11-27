import pytest

from bugwarrior.config.validation import TemplateError

from .base import DumbIssue, DumbService, DumbTask, DumbUdas
from .services.base import get_mock_service

DEFAULT_DESCRIPTION = "Construct Library on Terminus"


@pytest.fixture
def task():
    return DumbTask(
        project="end_of_empire",
        priority="H",
        udas=DumbUdas(url="http://example.com", type="issue"),
    )


@pytest.fixture
def expected():
    return {
        "project": "end_of_empire",
        "priority": "H",
        "description": DEFAULT_DESCRIPTION,
        "tags": [],
        "dumburl": "http://example.com",
        "dumbtype": "issue",
    }


@pytest.fixture
def synchronize(monkeypatch, task):
    """
    Return a callable mapping a record with the given templates applied.

    The mapped task and the default description are fixed, so that each test
    only sees what the templates changed.
    """
    monkeypatch.setattr(DumbIssue, "to_taskwarrior", lambda self: task)
    monkeypatch.setattr(
        DumbIssue, "get_default_description", lambda self: DEFAULT_DESCRIPTION
    )

    def run(templates=None, add_tags=None, extra=None):
        overrides = {
            f"{field}_template": template
            for field, template in (templates or {}).items()
        }
        if add_tags:
            overrides["add_tags"] = add_tags

        service = get_mock_service(DumbService, overrides)
        return service.get_task_for_record({}, extra).to_task_data()

    return run


class TestTemplates:
    def test_default_taskwarrior_record(self, synchronize, expected):
        assert synchronize() == expected

    def test_override_description(self, synchronize, expected):
        actual = synchronize({"description": "{{ priority }} - {{ description }}"})

        expected["description"] = f"H - {DEFAULT_DESCRIPTION}"
        assert actual == expected

    def test_override_project(self, synchronize, expected):
        actual = synchronize({"project": "wat_{{ project|upper }}"})

        expected["project"] = "wat_END_OF_EMPIRE"
        assert actual == expected

    def test_computed_description_does_not_hide_the_default(
        self, synchronize, expected
    ):
        """
        A service's "extra" data must not hide the default description.

        Templates can read "extra" keys, and those keys have no prefix, unlike
        UDAs. So an "extra" key named "description" must not change what
        "{{ description }}" renders.
        """
        actual = synchronize(
            {"description": "{{ description }}"},
            extra={"description": "raw body from the service"},
        )

        assert actual["description"] == DEFAULT_DESCRIPTION

    def test_tag_templates(self, synchronize, expected):
        actual = synchronize(add_tags=["one", "{{ project }}"])

        expected["tags"] = ["one", "end_of_empire"]
        assert actual == expected


class TestInvalidTemplates:
    """
    A template which cannot produce a valid value is a configuration error.

    A template always renders a string, so a template aimed at a field which
    holds anything else can never work. The error names the template and the
    field, rather than showing the raw pydantic message.
    """

    def test_value_outside_the_field_type_is_reported(self, synchronize):
        with pytest.raises(TemplateError) as excinfo:
            synchronize({"priority": "X"})

        message = str(excinfo.value)
        assert "priority_template = X" in message
        assert "rendered 'X'" in message
        # the target is named, so a user with several services knows which
        assert message.startswith("[unspecified]")

    def test_list_field_is_reported(self, synchronize):
        with pytest.raises(TemplateError, match="tags_template"):
            synchronize({"tags": "one"})
