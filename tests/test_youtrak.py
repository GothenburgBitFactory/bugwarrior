from future import standard_library
standard_library.install_aliases()
from builtins import next
from six.moves import configparser
import responses

from bugwarrior.services import ServiceConfig
from bugwarrior.services.youtrack import YoutrackService

from .base import ConfigTest, ServiceTest, AbstractServiceTest


class TestYoutrackService(ConfigTest):
    def setUp(self):
        super(TestYoutrackService, self).setUp()
        self.config = configparser.RawConfigParser()
        self.config.add_section('general')
        self.config.add_section('myservice')
        self.config.set('myservice', 'youtrack.login', 'foobar')
        self.config.set('myservice', 'youtrack.password', 'XXXXXX')
    def test_get_keyring_service(self):
        self.config.set('myservice', 'youtrack.host', 'youtrack.example.com')
        service_config = ServiceConfig(
            YoutrackService.CONFIG_PREFIX, self.config, 'myservice')
        self.assertEqual(
            YoutrackService.get_keyring_service(service_config),
            'youtrack://foobar@youtrack.example.com')


class TestYoutrackIssue(AbstractServiceTest, ServiceTest):
    maxDiff = None
    SERVICE_CONFIG = {
        'youtrack.host': 'youtrack.example.com',
        'youtrack.login': 'arbitrary_login',
        'youtrack.password': 'arbitrary_password',
        'youtrack.anonymous': True,
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
        super(TestYoutrackIssue, self).setUp()
        self.service = self.get_mock_service(YoutrackService)

    def test_to_taskwarrior(self):
        self.service.import_tags = True
        issue = self.service.get_issue_for_record(self.arbitrary_issue, self.arbitrary_extra)

        expected_output = {
            'project': 'TEST',
            'priority': self.service.default_priority,
            'tags': [u'bug', u'new_feature'],
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
                u'(bw)Is#TEST-1 - Hello World .. https://youtrack.example.com:443/issue/TEST-1',
            'project': 'TEST',
            'priority': self.service.default_priority,
            'tags': [u'bug', u'new_feature'],
            'youtrackissue': 'TEST-1',
            'youtracksummary': 'Hello World',
            'youtrackurl': 'https://youtrack.example.com:443/issue/TEST-1',
            'youtrackproject': 'TEST',
            'youtracknumber': 1,
        }

        self.assertEqual(issue.get_taskwarrior_record(), expected)
