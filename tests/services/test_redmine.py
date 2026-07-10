from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

import pytest
import responses

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.redmine import RedMineService

SERVICE_CLASS = RedMineService

SERVICE_CONFIG = {
    'service': 'redmine',
    'url': 'https://something',
    'key': 'something_else',
    'issue_limit': '100',
}


@pytest.fixture
def data():
    created = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(1)
    updated = datetime.now(timezone.utc).replace(microsecond=0)
    record = {
        "assigned_to": {"id": 35546, "name": "Adam Coddington"},
        "author": {"id": 35546, "name": "Adam Coddington"},
        "created_on": created.isoformat(),
        "due_on": "2016-12-30T16:40:29Z",
        "description": "This is a test issue.",
        "done_ratio": 0,
        "id": 363901,
        "priority": {"id": 4, "name": "High"},
        "project": {"id": 27375, "name": "Boiled Cabbage - Yum"},
        "status": {"id": 1, "name": "New"},
        "subject": "Biscuits",
        "tracker": {"id": 4, "name": "Task"},
        "updated_on": updated.isoformat(),
    }
    return SimpleNamespace(created=created, updated=updated, record=record)


class TestRedmineIssue:
    def test_to_taskwarrior(self, service, data):
        arbitrary_url = 'http://lkjlj.com'

        issue = service.get_issue_for_record(data.record)

        expected_output = {
            'annotations': [],
            'project': issue.get_project_name(),
            'priority': 'H',
            issue.DUEDATE: None,
            issue.ASSIGNED_TO: data.record['assigned_to']['name'],
            issue.AUTHOR: data.record['author']['name'],
            issue.CATEGORY: None,
            issue.DESCRIPTION: data.record['description'],
            issue.ESTIMATED_HOURS: None,
            issue.STATUS: 'New',
            issue.URL: arbitrary_url,
            issue.SUBJECT: data.record['subject'],
            issue.TRACKER: 'Task',
            issue.CREATED_ON: data.created,
            issue.UPDATED_ON: data.updated,
            issue.ID: data.record['id'],
            issue.PROJECT_NAME: 'Boiled Cabbage - Yum',
            issue.SPENT_HOURS: None,
            issue.START_DATE: None,
        }

        def get_url(*args):
            return arbitrary_url

        with mock.patch.object(issue, 'get_issue_url', side_effect=get_url):
            actual_output = issue.to_taskwarrior()

        assert actual_output == expected_output

    @responses.activate
    def test_issues(self, service, data):
        responses.get(
            'https://something/issues.json?limit=100', json={'issues': [data.record]}
        )

        issue = next(service.issues())

        expected = {
            'annotations': [],
            issue.DUEDATE: None,
            'description': '(bw)Is#363901 - Biscuits .. https://something/issues/363901',
            'priority': 'H',
            'project': 'boiledcabbageyum',
            'redmineid': 363901,
            'redmineprojectname': 'Boiled Cabbage - Yum',
            issue.SPENT_HOURS: None,
            issue.START_DATE: None,
            'redmineassignedto': 'Adam Coddington',
            'redmineauthor': 'Adam Coddington',
            issue.CATEGORY: None,
            issue.DESCRIPTION: data.record['description'],
            issue.ESTIMATED_HOURS: None,
            issue.STATUS: 'New',
            'redminesubject': 'Biscuits',
            'redminetracker': 'Task',
            issue.CREATED_ON: data.created,
            issue.UPDATED_ON: data.updated,
            'redmineurl': 'https://something/issues/363901',
            'tags': [],
        }

        assert TaskConstructor(issue).get_taskwarrior_record() == expected
