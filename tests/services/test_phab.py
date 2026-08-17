import pytest

from bugwarrior.services.phab import PhabricatorService

SERVICE_CLASS = PhabricatorService

SERVICE_CONFIG = {'service': 'phabricator', 'host': 'https://phabricator.example.com'}


@pytest.fixture
def record():
    return {
        'id': 42,
        'uri': 'https://phabricator.example.com/arbitrary_username/project/issues/3',
        'title': 'A phine phabricator issue',
    }


@pytest.fixture
def extra():
    return {'type': 'issue', 'project': 'PHROJECT', 'annotations': []}


class TestPhabricatorIssue:
    def test_to_taskwarrior(self, service, record, extra):
        service.import_labels_as_tags = True
        issue = service.get_issue_for_record(record, extra)

        expected_output = {
            'phabricatorurl': record['uri'],
            'phabricatortype': extra['type'],
            'phabricatortitle': record['title'],
            'phabricatorid': '3',
            'project': 'PHROJECT',
            'priority': 'M',
            'annotations': [],
        }
        actual_output = issue.to_taskwarrior().to_taskwarrior_data()

        assert actual_output == expected_output

    @pytest.mark.skip(reason='The phabricator library is hard to mock.')
    def test_issues(self):
        pass
