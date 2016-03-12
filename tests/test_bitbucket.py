from bugwarrior.services.bitbucket import BitbucketService

from .base import ServiceTest


class TestBitbucketIssue(ServiceTest):
    SERVICE_CONFIG = {
        'bitbucket.login': 'something',
        'bitbucket.username': 'somename',
        'bitbucket.password': 'something else',
    }

    def setUp(self):
        self.service = self.get_mock_service(BitbucketService)

    def test_to_taskwarrior(self):
        arbitrary_issue = {
            'priority': 'trivial',
            'id': '100',
            'title': 'Some Title',
        }
        arbitrary_extra = {
            'url': 'http://hello-there.com/',
            'project': 'Something',
            'annotations': [
                'One',
            ]
        }

        issue = self.service.get_issue_for_record(
            arbitrary_issue, arbitrary_extra
        )

        expected_output = {
            'project': arbitrary_extra['project'],
            'priority': issue.PRIORITY_MAP[arbitrary_issue['priority']],
            'annotations': arbitrary_extra['annotations'],

            issue.URL: arbitrary_extra['url'],
            issue.FOREIGN_ID: arbitrary_issue['id'],
            issue.TITLE: arbitrary_issue['title'],
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)
