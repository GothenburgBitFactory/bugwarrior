import responses

from bugwarrior.services.youtrack import YoutrackService

from .base import ConfigTest, ServiceTest, AbstractServiceTest


class TestYoutrackService(ConfigTest):
    def setUp(self):
        super().setUp()
        self.config = {}
        self.config['general'] = {'targets': ['myservice']}
        self.config['myservice'] = {
            'service': 'youtrack',
            'login': 'foobar',
            'password': 'XXXXXX',
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
        'password': 'arbitrary_password',
        'anonymous': True,
    }
    arbitrary_issue = {
        "id": "TEST-1",
        "field": [
            {
                "name": "projectShortName",
                "value": "TEST"
            },
            {
                "name": "numberInProject",
                "value": "1"
            },
            {
                "name": "summary",
                "value": "Hello World"
            },
        ],
        "tag": [
            {
                "value": "bug",
            },
            {
                "value": "New Feature",
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
            'https://youtrack.example.com:443/rest/issue?filter=for%3Ame+%23Unresolved&max=100',
            json={'issue': [self.arbitrary_issue]})

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
