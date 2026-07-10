import pytest

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.trac import TracService

from .base import get_mock_service

SERVICE_CONFIG = {
    'service': 'trac',
    'base_uri': 'ljlkajsdfl.com',
    'username': 'something',
    'password': 'somepwd',
}


@pytest.fixture
def record():
    return {
        'url': 'http://some/url.com/',
        'summary': 'Some Summary',
        'number': 204,
        'priority': 'critical',
        'component': 'testcomponent',
    }


@pytest.fixture
def extra():
    return {'annotations': ['alpha', 'beta'], 'project': 'some project'}


class FakeTracTicket:
    @staticmethod
    def changeLog(issuenumber):
        return []


class FakeTracServer:
    ticket = FakeTracTicket()


class FakeTracLib:
    server = FakeTracServer()

    def __init__(self, record):
        self.record = record

    @staticmethod
    def query_tickets(query):
        return ['something']

    def get_ticket(self, ticket):
        return (1, None, None, self.record)


class TestTracIssue:
    @pytest.fixture
    def service(self, record):
        service = get_mock_service(TracService, SERVICE_CONFIG)
        service.trac = FakeTracLib(record)
        return service

    def test_to_taskwarrior(self, service, record, extra):
        issue = service.get_issue_for_record(record, extra)

        expected_output = {
            'project': extra['project'],
            'priority': issue.PRIORITY_MAP[record['priority']],
            'annotations': extra['annotations'],
            issue.URL: record['url'],
            issue.SUMMARY: record['summary'],
            issue.NUMBER: record['number'],
            issue.COMPONENT: record['component'],
        }
        actual_output = issue.to_taskwarrior()

        assert actual_output == expected_output

    def test_issues(self, service):
        issue = next(service.issues())

        expected = {
            'annotations': [],
            'description': '(bw)Is#1 - Some Summary .. https://ljlkajsdfl.com/ticket/1',
            'priority': 'H',
            'project': 'unspecified',
            'tags': [],
            'tracnumber': 1,
            'tracsummary': 'Some Summary',
            'tracurl': 'https://ljlkajsdfl.com/ticket/1',
            'traccomponent': 'testcomponent',
        }

        assert TaskConstructor(issue).get_taskwarrior_record() == expected
