import pytest

from bugwarrior.collect import TaskConstructor

from .base import make_issue

DEFAULT_DESCRIPTION = 'Construct Library on Terminus'


@pytest.fixture
def record():
    return {'project': 'end_of_empire', 'priority': 'H'}


@pytest.fixture
def get_issue(record):
    def get(templates=None, add_tags=None):
        templates = {} if templates is None else templates
        overrides = {f'{key}_template': value for key, value in templates.items()}
        if add_tags:
            overrides['add_tags'] = add_tags

        issue = make_issue(config_overrides=overrides)
        issue.to_taskwarrior = lambda: record
        issue.get_default_description = lambda: DEFAULT_DESCRIPTION
        return issue

    return get


class TestTemplates:
    def test_default_taskwarrior_record(self, get_issue, record):
        issue = get_issue({})

        actual = TaskConstructor(issue).get_taskwarrior_record()
        record.update({'description': DEFAULT_DESCRIPTION, 'tags': []})

        assert actual == record

    def test_override_description(self, get_issue, record):
        description_template = "{{ priority }} - {{ description }}"

        issue = get_issue({'description': description_template})

        actual = TaskConstructor(issue).get_taskwarrior_record()
        record.update(
            {
                'description': '%s - %s' % (record['priority'], DEFAULT_DESCRIPTION),
                'tags': [],
            }
        )

        assert actual == record

    def test_override_project(self, get_issue, record):
        project_template = "wat_{{ project|upper }}"

        issue = get_issue({'project': project_template})

        actual = TaskConstructor(issue).get_taskwarrior_record()
        record.update(
            {
                'description': DEFAULT_DESCRIPTION,
                'project': 'wat_%s' % record['project'].upper(),
                'tags': [],
            }
        )

        assert actual == record

    def test_tag_templates(self, get_issue, record):
        issue = get_issue(add_tags=['one', '{{ project }}'])

        actual = TaskConstructor(issue).get_taskwarrior_record()
        record.update(
            {'description': DEFAULT_DESCRIPTION, 'tags': ['one', record['project']]}
        )

        assert actual == record
