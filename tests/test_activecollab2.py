import datetime

import pytz

from bugwarrior.services.activecollab2 import ActiveCollab2Service

from .base import ServiceTest


class TestActiveCollab2Issue(ServiceTest):
    SERVICE_CONFIG = {
        'activecollab2.url': 'hello',
        'activecollab2.key': 'howdy',
        'activecollab2.user_id': 'hola',
        'activecollab2.projects': '1:one, 2:two'
    }

    def setUp(self):
        self.service = self.get_mock_service(ActiveCollab2Service)

    def test_to_taskwarrior(self):
        arbitrary_due_on = (
            datetime.datetime.now() - datetime.timedelta(hours=1)
        ).replace(tzinfo=pytz.UTC)
        arbitrary_created_on = (
            datetime.datetime.now() - datetime.timedelta(hours=2)
        ).replace(tzinfo=pytz.UTC)
        arbitrary_issue = {
            'project': 'something',
            'priority': 2,
            'due_on': arbitrary_due_on.isoformat(),
            'permalink': 'http://wherever/',
            'ticket_id': 10,
            'project_id': 20,
            'type': 'issue',
            'created_on': arbitrary_created_on.isoformat(),
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
            issue.TICKET_ID: arbitrary_issue['ticket_id'],
            issue.PROJECT_ID: arbitrary_issue['project_id'],
            issue.TYPE: arbitrary_issue['type'],
            issue.CREATED_ON: arbitrary_created_on,
            issue.CREATED_BY_ID: arbitrary_issue['created_by_id'],
            issue.BODY: arbitrary_issue['body'],
            issue.NAME: arbitrary_issue['name'],
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)
