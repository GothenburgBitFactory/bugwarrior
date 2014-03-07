from bugwarrior.services.trac import TracService

from .base import ServiceTest


class TestTracIssue(ServiceTest):
    SERVICE_CONFIG = {
        'trac.base_uri': 'http://ljlkajsdfl.com',
        'trac.username': 'something',
        'trac.password': 'somepwd',
    }

    def setUp(self):
        self.service = self.get_mock_service(TracService)

    def test_to_taskwarrior(self):
        arbitrary_issue = {
            'url': 'http://some/url.com/',
            'summary': 'Some Summary',
            'number': 204,
            'priority': 'critical',
        }
        arbitrary_extra = {
            'annotations': [
                'alpha',
                'beta',
            ],
            'project': 'some project',
        }

        issue = self.service.get_issue_for_record(
            arbitrary_issue,
            arbitrary_extra,
        )

        expected_output = {
            'project': arbitrary_extra['project'],
            'priority': issue.PRIORITY_MAP[arbitrary_issue['priority']],
            'annotations': arbitrary_extra['annotations'],
            issue.URL: arbitrary_issue['url'],
            issue.SUMMARY: arbitrary_issue['summary'],
            issue.NUMBER: arbitrary_issue['number'],
        }
        actual_output = issue.to_taskwarrior()

        self.assertEquals(actual_output, expected_output)
