from bugwarrior.collect import TaskConstructor

from .base import make_issue


class TestTemplates:
    arbitrary_default_description = 'Construct Library on Terminus'
    arbitrary_issue = {'project': 'end_of_empire', 'priority': 'H'}

    def get_issue(self, templates=None, add_tags=None):
        templates = {} if templates is None else templates
        overrides = {f'{key}_template': value for key, value in templates.items()}
        if add_tags:
            overrides['add_tags'] = add_tags

        issue = make_issue(config_overrides=overrides)
        issue.to_taskwarrior = lambda: self.arbitrary_issue
        issue.get_default_description = lambda: self.arbitrary_default_description
        return issue

    def test_default_taskwarrior_record(self):
        issue = self.get_issue({})

        record = TaskConstructor(issue).get_taskwarrior_record()
        expected_record = self.arbitrary_issue.copy()
        expected_record.update(
            {'description': self.arbitrary_default_description, 'tags': []}
        )

        assert record == expected_record

    def test_override_description(self):
        description_template = "{{ priority }} - {{ description }}"

        issue = self.get_issue({'description': description_template})

        record = TaskConstructor(issue).get_taskwarrior_record()
        expected_record = self.arbitrary_issue.copy()
        expected_record.update(
            {
                'description': '%s - %s'
                % (
                    self.arbitrary_issue['priority'],
                    self.arbitrary_default_description,
                ),
                'tags': [],
            }
        )

        assert record == expected_record

    def test_override_project(self):
        project_template = "wat_{{ project|upper }}"

        issue = self.get_issue({'project': project_template})

        record = TaskConstructor(issue).get_taskwarrior_record()
        expected_record = self.arbitrary_issue.copy()
        expected_record.update(
            {
                'description': self.arbitrary_default_description,
                'project': 'wat_%s' % self.arbitrary_issue['project'].upper(),
                'tags': [],
            }
        )

        assert record == expected_record

    def test_tag_templates(self):
        issue = self.get_issue(add_tags=['one', '{{ project }}'])

        record = TaskConstructor(issue).get_taskwarrior_record()
        expected_record = self.arbitrary_issue.copy()
        expected_record.update(
            {
                'description': self.arbitrary_default_description,
                'tags': ['one', self.arbitrary_issue['project']],
            }
        )

        assert record == expected_record
