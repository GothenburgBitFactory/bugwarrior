import datetime
import unittest

import pytz

from bugwarrior.services.phab import PhabricatorService

from .base import ServiceTest, AbstractServiceTest


class TestPhabricatorIssue(AbstractServiceTest, ServiceTest):
    maxDiff = None
    SERVICE_CONFIG = {
        'phabricator.host': 'phabricator.example.com',
    }

    def setUp(self):
        super(TestPhabricatorIssue, self).setUp()
        self.service = self.get_mock_service(PhabricatorService)
        self.arbitrary_created = (
            datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        ).replace(tzinfo=pytz.UTC, microsecond=0)
        self.arbitrary_updated = datetime.datetime.utcnow().replace(
            tzinfo=pytz.UTC, microsecond=0)
        self.arbitrary_duedate = (
            datetime.datetime.combine(datetime.date.today(),
                                      datetime.datetime.min.time())
        ).replace(tzinfo=pytz.UTC)
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
            self.arbitrary_issue,
            self.arbitrary_extra
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
