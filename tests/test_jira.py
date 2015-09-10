import mock

from bugwarrior.services.jira import JiraService

from .base import ServiceTest


class TestJiraIssue(ServiceTest):
    SERVICE_CONFIG = {
        'jira.username': 'one',
        'jira.base_uri': 'two',
        'jira.password': 'three',
    }

    def setUp(self):
        with mock.patch('jira.client.JIRA._get_json'):
            self.service = self.get_mock_service(JiraService)

    def test_to_taskwarrior(self):
        arbitrary_project = 'DONUT'
        arbitrary_id = '10'
        arbitrary_url = 'http://one'
        arbitrary_summary = 'lkjaldsfjaldf'
        arbitrary_estimation = 3600
        arbitrary_record = {
            'fields': {
                'priority': 'Blocker',
                'summary': arbitrary_summary,
                'timeestimate': arbitrary_estimation,
            },
            'key': '%s-%s' % (arbitrary_project, arbitrary_id, ),
        }
        arbitrary_extra = {
            'jira_version': 5,
            'annotations': ['an annotation'],
        }

        issue = self.service.get_issue_for_record(
            arbitrary_record, arbitrary_extra
        )

        expected_output = {
            'project': arbitrary_project,
            'priority': (
                issue.PRIORITY_MAP[arbitrary_record['fields']['priority']]
            ),
            'annotations': arbitrary_extra['annotations'],
            'tags': [],

            issue.URL: arbitrary_url,
            issue.FOREIGN_ID: arbitrary_record['key'],
            issue.SUMMARY: arbitrary_summary,
            issue.DESCRIPTION: None,
            issue.ESTIMATE: arbitrary_estimation / 60 / 60,
        }

        def get_url(*args):
            return arbitrary_url

        with mock.patch.object(issue, 'get_url', side_effect=get_url):
            actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)
