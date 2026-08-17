from datetime import datetime, timedelta, timezone
from unittest import mock

import pytest
import responses

from bugwarrior.services.redmine import RedMineService

SERVICE_CLASS = RedMineService

SERVICE_CONFIG = {
    'service': 'redmine',
    'url': 'https://something',
    'key': 'something_else',
    'issue_limit': '100',
}


CREATED = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(1)
UPDATED = datetime.now(timezone.utc).replace(microsecond=0)


@pytest.fixture
def record():
    return {
        "assigned_to": {"id": 35546, "name": "Adam Coddington"},
        "author": {"id": 35546, "name": "Adam Coddington"},
        "created_on": CREATED.isoformat(),
        "due_on": "2016-12-30T16:40:29Z",
        "description": "This is a test issue.",
        "done_ratio": 0,
        "id": 363901,
        "priority": {"id": 4, "name": "High"},
        "project": {"id": 27375, "name": "Boiled Cabbage - Yum"},
        "status": {"id": 1, "name": "New"},
        "subject": "Biscuits",
        "tracker": {"id": 4, "name": "Task"},
        "updated_on": UPDATED.isoformat(),
    }


class TestRedmineHours:
    """
    Redmine reports spent and estimated work as a number of hours.

    Those land in duration UDAs, and Taskwarrior is picky about the format it
    accepts, so a zero is as important to cover as a fraction.
    See https://github.com/GothenburgBitFactory/bugwarrior/pull/967.
    """

    @pytest.mark.parametrize(
        ('hours', 'expected'),
        [
            (3.5, 'PT3H30M'),
            (0.0, 'PT0S'),  # a logged zero is not the same as nothing logged
            (2, 'PT2H'),  # a whole number of hours arrives as an int
            (None, None),  # Redmine omits the field or returns null
        ],
    )
    def test_hours_become_durations(self, service, record, hours, expected):
        record['spent_hours'] = hours
        record['estimated_hours'] = hours

        task_data = service.get_issue_for_record(record).to_taskwarrior()

        data = task_data.to_taskwarrior_data()
        assert data['redminespenthours'] == expected
        assert data['redmineestimatedhours'] == expected

    def test_absent_hours_are_empty(self, service, record):
        data = service.get_issue_for_record(record).to_taskwarrior()

        task_data = data.to_taskwarrior_data()
        assert task_data['redminespenthours'] is None
        assert task_data['redmineestimatedhours'] is None


class TestRedmineIssue:
    def test_to_taskwarrior(self, service, record):
        arbitrary_url = 'http://lkjlj.com'

        issue = service.get_issue_for_record(record)

        expected_output = {
            'annotations': [],
            'project': issue.get_project_name(),
            'priority': 'H',
            'redmineduedate': None,
            'redmineassignedto': record['assigned_to']['name'],
            'redmineauthor': record['author']['name'],
            'redminecategory': None,
            'redminedescription': record['description'],
            'redmineestimatedhours': None,
            'redminestatus': 'New',
            'redmineurl': arbitrary_url,
            'redminesubject': record['subject'],
            'redminetracker': 'Task',
            'redminecreatedon': CREATED,
            'redmineupdatedon': UPDATED,
            'redmineid': record['id'],
            'redmineprojectname': 'Boiled Cabbage - Yum',
            'redminespenthours': None,
            'redminestartdate': None,
        }

        def get_url(*args):
            return arbitrary_url

        with mock.patch.object(issue, 'get_issue_url', side_effect=get_url):
            actual_output = issue.to_taskwarrior().to_taskwarrior_data()

        assert actual_output == expected_output

    @responses.activate
    def test_issues(self, service, record):
        responses.get(
            'https://something/issues.json?limit=100', json={'issues': [record]}
        )

        task = next(service.issues())

        expected = {
            'annotations': [],
            'redmineduedate': None,
            'description': '(bw)Is#363901 - Biscuits .. https://something/issues/363901',
            'priority': 'H',
            'project': 'boiledcabbageyum',
            'redmineid': 363901,
            'redmineprojectname': 'Boiled Cabbage - Yum',
            'redminespenthours': None,
            'redminestartdate': None,
            'redmineassignedto': 'Adam Coddington',
            'redmineauthor': 'Adam Coddington',
            'redminecategory': None,
            'redminedescription': record['description'],
            'redmineestimatedhours': None,
            'redminestatus': 'New',
            'redminesubject': 'Biscuits',
            'redminetracker': 'Task',
            'redminecreatedon': CREATED,
            'redmineupdatedon': UPDATED,
            'redmineurl': 'https://something/issues/363901',
        }

        assert task.to_taskwarrior_data() == expected
