import pytest

from bugwarrior.services.phab import PhabricatorService

from .base import get_mock_service

SERVICE_CONFIG = {'service': 'phabricator', 'host': 'https://phabricator.example.com'}


class TestPhabricatorIssue:
    arbitrary_issue = {
        "id": 42,
        "uri": "https://phabricator.example.com/arbitrary_username/project/issues/3",
        "title": "A phine phabricator issue",
    }
    arbitrary_extra = {'type': 'issue', 'project': 'PHROJECT', 'annotations': []}

    @pytest.fixture
    def service(self):
        return get_mock_service(PhabricatorService, SERVICE_CONFIG)

    def test_to_taskwarrior(self, service):
        service.import_labels_as_tags = True
        issue = service.get_issue_for_record(self.arbitrary_issue, self.arbitrary_extra)

        expected_output = {
            issue.URL: self.arbitrary_issue['uri'],
            issue.TYPE: self.arbitrary_extra['type'],
            issue.TITLE: self.arbitrary_issue['title'],
            issue.OBJECT_NAME: '3',
            'project': 'PHROJECT',
            'priority': 'M',
            'annotations': [],
        }
        actual_output = issue.to_taskwarrior()

        assert actual_output == expected_output

    @pytest.mark.skip(reason='The phabricator library is hard to mock.')
    def test_issues(self):
        pass
