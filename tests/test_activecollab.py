import datetime

import mock

from bugwarrior.services.activecollab3 import (
    ActiveCollab3Client,
    ActiveCollab3Service
)

from .base import ServiceTest


class TestActiveCollab3Issue(ServiceTest):
    SERVICE_CONFIG = {
        'activecollab3.url': 'hello',
        'activecollab3.key': 'howdy',
        'activecollab3.user_id': 'hola',
        'activecollab3.projects': '1:one, 2:two'
    }

    def setUp(self):
        with mock.patch(
            'bugwarrior.services.activecollab3.ActiveCollab3Client.call_api'
        ):
            self.service = self.get_mock_service(ActiveCollab3Service)

    def test_to_taskwarrior(self):
        arbitrary_due_on = (
            datetime.datetime.now() - datetime.timedelta(hours=1)
        )
        arbitrary_created_on = (
            datetime.datetime.now() - datetime.timedelta(hours=2)
        )
        arbitrary_issue = {
            'project': 'something',
            'priority': 2,
            'due_on': arbitrary_due_on.isoformat(),

            'permalink': 'http://wherever/',
            'task_id': 10,
            'project_id': 20,
            'id': '30',
            'type': 'issue',
            'created_on': {
                'mysql': arbitrary_created_on.isoformat()
            },
            'created_by_id': '10',
            'body': 'Ticket Body',
            'name': 'Anonymous',
        }

        issue = self.service.get_issue_for_record(arbitrary_issue)

        expected_output = {
            'project': arbitrary_issue['project'],
            'priority': issue.PRIORITY_MAP[arbitrary_issue['priority']],
            'due': arbitrary_due_on,

            issue.PERMALINK: arbitrary_issue['permalink'],
            issue.PROJECT_ID: arbitrary_issue['project_id'],
            issue.TYPE: arbitrary_issue['type'],
            issue.CREATED_ON: arbitrary_created_on,
            issue.CREATED_BY_ID: arbitrary_issue['created_by_id'],
            issue.BODY: arbitrary_issue['body'],
            issue.NAME: arbitrary_issue['name'],
            issue.FOREIGN_ID: arbitrary_issue['id'],
            issue.TASK_ID: arbitrary_issue['task_id'],
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)
