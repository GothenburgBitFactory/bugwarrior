import responses

from bugwarrior.services.youtrack import YoutrackService

from .base import ConfigTest, ServiceTest, AbstractServiceTest


class TestYoutrackService(ConfigTest):
    def setUp(self):
        super().setUp()
        self.config = {
            'general': {'targets': ['myservice']},
            'myservice': {
                'service': 'youtrack',
                'login': 'foobar',
                'token': 'XXXXXX',
            },
        }

    def test_get_keyring_service(self):
        self.config['myservice']['host'] = 'youtrack.example.com'
        service_config = self.validate()['myservice']
        self.assertEqual(
            YoutrackService.get_keyring_service(service_config),
            'youtrack://foobar@youtrack.example.com')


class TestYoutrackIssue(AbstractServiceTest, ServiceTest):
    maxDiff = None
    SERVICE_CONFIG = {
        'service': 'youtrack',
        'host': 'youtrack.example.com',
        'login': 'arbitrary_login',
        'token': 'arbitrary_token',
        'anonymous': True,
    }

    arbitrary_issue = {
        "id": "2-1",
        "$type": "Issue",
        "numberInProject": 1,
        "summary": "Hello World",
        "project": {
            "shortName": "TEST",
            "$type": "Project"
        },
        "tags": [
            {
                "$type": "IssueTag",
                "name": "bug"
            },
            {
                "$type": "IssueTag",
                "name": "New Feature"
            }
        ]
    }
    arbitrary_extra = {
    }

    def setUp(self):
        super().setUp()
        self.service = self.get_mock_service(YoutrackService)

    def test_to_taskwarrior(self):
        self.service.import_tags = True
        issue = self.service.get_issue_for_record(self.arbitrary_issue, self.arbitrary_extra)

        expected_output = {
            'project': 'TEST',
            'priority': self.service.config.default_priority,
            'tags': ['bug', 'new_feature'],
            issue.ISSUE: 'TEST-1',
            issue.SUMMARY: 'Hello World',
            issue.URL: 'https://youtrack.example.com:443/issue/TEST-1',
            issue.PROJECT: 'TEST',
            issue.NUMBER: 1,
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

    @responses.activate
    def test_issues(self):
        self.add_response(
            'https://youtrack.example.com:443/api/issues?query=for%3Ame+%23Unresolved&max=100&fields=id,summary,project(shortName),numberInProject,tags(name)',
            json=[self.arbitrary_issue])

        issue = next(self.service.issues())

        expected = {
            'description':
                '(bw)Is#TEST-1 - Hello World .. https://youtrack.example.com:443/issue/TEST-1',
            'project': 'TEST',
            'priority': self.service.config.default_priority,
            'tags': ['bug', 'new_feature'],
            'youtrackissue': 'TEST-1',
            'youtracksummary': 'Hello World',
            'youtrackurl': 'https://youtrack.example.com:443/issue/TEST-1',
            'youtrackproject': 'TEST',
            'youtracknumber': 1,
        }

        self.assertEqual(issue.get_taskwarrior_record(), expected)
