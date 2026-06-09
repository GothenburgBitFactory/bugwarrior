from datetime import date, datetime, timedelta, timezone
import unittest

from bugwarrior.services.phab import PhabricatorService

from .base import AbstractServiceTest, ServiceTest


class TestPhabricatorIssue(AbstractServiceTest, ServiceTest):
    maxDiff = None
    SERVICE_CONFIG = {
        'service': 'phabricator',
        'host': 'https://phabricator.example.com',
    }

    def setUp(self):
        super().setUp()
        self.service = self.get_mock_service(PhabricatorService)
        self.arbitrary_created = (
            datetime.now(timezone.utc) - timedelta(hours=1)
        ).replace(microsecond=0)
        self.arbitrary_updated = datetime.now(timezone.utc).replace(microsecond=0)
        self.arbitrary_duedate = datetime.combine(
            date.today(), datetime.min.time(), tzinfo=timezone.utc
        )
        self.arbitrary_issue = {
            "id": 42,
            "uri": "https://phabricator.example.com/arbitrary_username/project/issues/3",
            "title": "A phine phabricator issue",
        }
        self.arbitrary_extra = {
            'type': 'issue',
            'project': 'PHROJECT',
            'annotations': [],
        }

    def test_to_taskwarrior(self):
        self.service.import_labels_as_tags = True
        issue = self.service.get_issue_for_record(
            self.arbitrary_issue, self.arbitrary_extra
        )

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

        self.assertEqual(actual_output, expected_output)

    @unittest.skip('The phabricator library is hard to mock.')
    def test_issues(self):
        pass
