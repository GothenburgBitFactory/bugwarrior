from builtins import next
from builtins import object
import datetime
import unittest

import mock
import pypandoc
import pytz

from bugwarrior.services.activecollab import (
    ActiveCollabService
)

from .base import ServiceTest, AbstractServiceTest


class FakeActiveCollabLib(object):
    def __init__(self, arbitrary_issue):
        self.arbitrary_issue = arbitrary_issue

    def get_my_tasks(self):
        return {'arbitrary_key': {'assignments': {
            self.arbitrary_issue['task_id']: self.arbitrary_issue}}}

    def get_assignment_labels(self):
        return []

    def get_comments(self, *args):
        return []


class TestActiveCollabIssues(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        'activecollab.url': 'hello',
        'activecollab.key': 'howdy',
        'activecollab.user_id': '2',
        'activecollab.projects': '1:one, 2:two'
    }

    arbitrary_due_on = (
        datetime.datetime.now() - datetime.timedelta(hours=1)
    ).replace(tzinfo=pytz.UTC)
    arbitrary_created_on = (
        datetime.datetime.now() - datetime.timedelta(hours=2)
    ).replace(tzinfo=pytz.UTC)

    try:
        _body = pypandoc.convert('<p>Ticket Body</p>', 'md', format='html')
    except OSError:
        raise unittest.SkipTest('Pandoc is not installed.')
    arbitrary_issue = {
        'priority': 0,
        'project': 'something',
        'due_on': {
            'formatted_date': arbitrary_due_on.isoformat(),
        },
        'permalink': 'http://wherever/',
        'task_id': 10,
        'project_name': 'something',
        'project_id': 10,
        'id': 30,
        'type': 'issue',
        'created_on': {
            'formatted_date': arbitrary_created_on.isoformat(),
        },
        'created_by_name': 'Tester',
        'body': _body.rstrip(),
        'name': 'Anonymous',
        'milestone': 'Sprint 1',
        'estimated_time': 1,
        'tracked_time': 10,
        'label': 'ON_HOLD',
        'assignee_id': 2,
        'label_id': 1,
    }

    def setUp(self):
        super(TestActiveCollabIssues, self).setUp()
        self.maxDiff = None
        with mock.patch('pyac.library.activeCollab.call_api'):
            self.service = self.get_mock_service(ActiveCollabService)

    def get_mock_service(self, *args, **kwargs):
        service = super(TestActiveCollabIssues, self).get_mock_service(
            *args, **kwargs)
        service.activecollab = FakeActiveCollabLib(self.arbitrary_issue)
        return service

    def test_to_taskwarrior(self):
        arbitrary_extra = {
            'annotations': ['an annotation'],
        }

        issue = self.service.get_issue_for_record(
            self.arbitrary_issue, arbitrary_extra)

        expected_output = {
            'project': self.arbitrary_issue['project'],
            'due': self.arbitrary_due_on,
            'priority': 'M',
            'annotations': arbitrary_extra['annotations'],
            issue.PERMALINK: self.arbitrary_issue['permalink'],
            issue.PROJECT_ID: self.arbitrary_issue['project_id'],
            issue.PROJECT_NAME: self.arbitrary_issue['project_name'],
            issue.TYPE: self.arbitrary_issue['type'],
            issue.CREATED_ON: self.arbitrary_created_on,
            issue.CREATED_BY_NAME: self.arbitrary_issue['created_by_name'],
            issue.BODY: self.arbitrary_issue['body'],
            issue.NAME: self.arbitrary_issue['name'],
            issue.FOREIGN_ID: self.arbitrary_issue['id'],
            issue.TASK_ID: self.arbitrary_issue['task_id'],
            issue.ESTIMATED_TIME: self.arbitrary_issue['estimated_time'],
            issue.TRACKED_TIME: self.arbitrary_issue['tracked_time'],
            issue.MILESTONE: self.arbitrary_issue['milestone'],
            issue.LABEL: self.arbitrary_issue['label'],
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

    def test_issues(self):
        issue = next(self.service.issues())

        expected = {
            'acbody': u'Ticket Body',
            'accreatedbyname': 'Tester',
            'accreatedon': self.arbitrary_created_on,
            'acestimatedtime': 1,
            'acid': 30,
            'aclabel': None,
            'acmilestone': 'Sprint 1',
            'acname': 'Anonymous',
            'acpermalink': 'http://wherever/',
            'acprojectid': 10,
            'acprojectname': 'something',
            'actaskid': 10,
            'actrackedtime': 10,
            'actype': 'issue',
            'annotations': [],
            'description': '(bw)Is#30 - Anonymous .. http://wherever/',
            'due': self.arbitrary_due_on,
            'priority': 'M',
            'project': 'something',
            'tags': []}

        self.assertEqual(issue.get_taskwarrior_record(), expected)
