from bugwarrior.services import Issue

from .base import ServiceTest


class TestTemplates(ServiceTest):
    def setUp(self):
        super(TestTemplates, self).setUp()
        self.arbitrary_default_description = 'Construct Library on Terminus'
        self.arbitrary_issue = {
            'project': 'end_of_empire',
            'priority': 'H',
        }

    def get_issue(
        self, templates=None, issue=None, description=None, add_tags=None
    ):
        templates = {} if templates is None else templates
        origin = {
            'annotation_length': 100,  # Arbitrary
            'default_priority': 'H',  # Arbitrary
            'description_length': 100,  # Arbitrary
            'templates': templates,
            'shorten': False,  # Arbitrary
            'add_tags': add_tags if add_tags else [],
        }

        issue = Issue({}, origin)
        issue.to_taskwarrior = lambda: (
            self.arbitrary_issue if description is None else description
        )
        issue.get_default_description = lambda: (
            self.arbitrary_default_description
            if description is None else description
        )
        return issue

    def test_default_taskwarrior_record(self):
        issue = self.get_issue({})

        record = issue.get_taskwarrior_record()
        expected_record = self.arbitrary_issue.copy()
        expected_record.update({
            'description': self.arbitrary_default_description,
            'tags': [],
        })

        self.assertEqual(record, expected_record)

    def test_override_description(self):
        description_template = "{{ priority }} - {{ description }}"

        issue = self.get_issue({
            'description': description_template
        })

        record = issue.get_taskwarrior_record()
        expected_record = self.arbitrary_issue.copy()
        expected_record.update({
            'description': '%s - %s' % (
                self.arbitrary_issue['priority'],
                self.arbitrary_default_description,
            ),
            'tags': [],
        })

        self.assertEqual(record, expected_record)

    def test_override_project(self):
        project_template = "wat_{{ project|upper }}"

        issue = self.get_issue({
            'project': project_template
        })

        record = issue.get_taskwarrior_record()
        expected_record = self.arbitrary_issue.copy()
        expected_record.update({
            'description': self.arbitrary_default_description,
            'project': 'wat_%s' % self.arbitrary_issue['project'].upper(),
            'tags': [],
        })

        self.assertEqual(record, expected_record)

    def test_tag_templates(self):
        issue = self.get_issue(add_tags=['one', '{{ project }}'])

        record = issue.get_taskwarrior_record()
        expected_record = self.arbitrary_issue.copy()
        expected_record.update({
            'description': self.arbitrary_default_description,
            'tags': ['one', self.arbitrary_issue['project']]
        })

        self.assertEqual(record, expected_record)
