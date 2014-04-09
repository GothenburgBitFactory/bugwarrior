import mock

from bugwarrior.services.bz import BugzillaService

from .base import ServiceTest


class TestBugzillaService(ServiceTest):
    SERVICE_CONFIG = {
        'bugzilla.base_uri': 'http://one.com/',
        'bugzilla.username': 'hello',
        'bugzilla.password': 'there',
    }

    def setUp(self):
        with mock.patch('bugzilla.Bugzilla'):
            self.service = self.get_mock_service(BugzillaService)

    def test_to_taskwarrior(self):
        arbitrary_record = {
            'component': 'Something',
            'priority': 'urgent',
            'summary': 'This is the issue summary'
        }
        arbitrary_extra = {
            'url': 'http://path/to/issue/',
            'annotations': [
                'Two',
            ],
        }

        issue = self.service.get_issue_for_record(
            arbitrary_record,
            arbitrary_extra,
        )

        expected_output = {
            'project': arbitrary_record['component'],
            'priority': issue.PRIORITY_MAP[arbitrary_record['priority']],
            'annotations': arbitrary_extra['annotations'],

            issue.URL: arbitrary_extra['url'],
            issue.SUMMARY: arbitrary_record['summary'],
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)
