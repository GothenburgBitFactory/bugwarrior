import datetime
import mock
import pypandoc
import pytz

from bugwarrior.services.activecollab import (
    ActiveCollabService
)

from .base import ServiceTest


class TestActiveCollabIssue(ServiceTest):
    SERVICE_CONFIG = {
        'activecollab.url': 'hello',
        'activecollab.key': 'howdy',
        'activecollab.user_id': '2',
        'activecollab.projects': '1:one, 2:two'
    }

    def setUp(self):
        self.maxDiff = None
        with mock.patch(
            'pyac.library.activeCollab.call_api'
        ):
            self.service = self.get_mock_service(ActiveCollabService)

    def test_to_taskwarrior(self):
        arbitrary_due_on = (
            datetime.datetime.now() - datetime.timedelta(hours=1)
        ).replace(tzinfo=pytz.UTC)
        arbitrary_created_on = (
            datetime.datetime.now() - datetime.timedelta(hours=2)
        ).replace(tzinfo=pytz.UTC)
        arbitrary_extra = {
            'annotations': ['an annotation'],
        }
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
            'body': pypandoc.convert('<p>Ticket Body</p>', 'md',
                                     format='html').rstrip(),
            'name': 'Anonymous',
            'milestone': 'Sprint 1',
            'estimated_time': 1,
            'tracked_time': 10,
            'label': 'ON_HOLD',
        }

        issue = self.service.get_issue_for_record(
            arbitrary_issue, arbitrary_extra
        )

        expected_output = {
            'project': arbitrary_issue['project'],
            'due': arbitrary_due_on,
            'priority': 'M',
            'annotations': arbitrary_extra['annotations'],
            issue.PERMALINK: arbitrary_issue['permalink'],
            issue.PROJECT_ID: arbitrary_issue['project_id'],
            issue.PROJECT_NAME: arbitrary_issue['project_name'],
            issue.TYPE: arbitrary_issue['type'],
            issue.CREATED_ON: arbitrary_created_on,
            issue.CREATED_BY_NAME: arbitrary_issue['created_by_name'],
            issue.BODY: arbitrary_issue['body'],
            issue.NAME: arbitrary_issue['name'],
            issue.FOREIGN_ID: arbitrary_issue['id'],
            issue.TASK_ID: arbitrary_issue['task_id'],
            issue.ESTIMATED_TIME: arbitrary_issue['estimated_time'],
            issue.TRACKED_TIME: arbitrary_issue['tracked_time'],
            issue.MILESTONE: arbitrary_issue['milestone'],
            issue.LABEL: arbitrary_issue['label'],
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)
