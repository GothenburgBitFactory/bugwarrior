from datetime import UTC, datetime

import pytest
import responses

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.teamwork_projects import TeamworkService

SERVICE_CLASS = TeamworkService

SERVICE_CONFIG = {
    'service': 'teamwork_projects',
    'host': 'https://test.teamwork_projects.com',
    'token': 'arbitrary_token',
}


@pytest.fixture
def record():
    return {
        "todo-items": [
            {
                "id": 5,
                "comments-count": 2,
                "description": "This issue is meant for testing",
                "content": "This is a test issue",
                "project-id": 1,
                "project-name": "Test Project",
                "status": "new",
                "company-name": "Test Company",
                "company-id": 1,
                "creator-id": 1,
                "creator-firstname": "Greg",
                "creator-lastname": "McCoy",
                "updater-id": 0,
                "updater-firstname": "",
                "updater-lastname": "",
                "completed": False,
                "start-date": "",
                "due-date": "2019-12-12T10:06:31Z",
                "created-on": "2018-12-12T10:06:31Z",
                "last-changed-on": "2019-01-16T11:00:44Z",
                "priority": "high",
                "parentTaskId": "",
                "userFollowingComments": True,
                "userFollowingChanges": True,
                "DLM": 0,
                "responsible-party-ids": ["5"],
            }
        ]
    }


@pytest.fixture
def extra():
    return {
        "host": "https://test.teamwork_projects.com",
        "annotations": [("Greg McCoy", "Test comment"), ("Bob Test", "testing")],
    }


@pytest.fixture
def comments():
    return {
        "comments": [
            {
                "project-id": "999",
                "author-lastname": "User",
                "datetime": "2014-03-31T13:03:29Z",
                "author_id": "999",
                "id": "999",
                "company-name": "Test Company",
                "last-changed-on": "",
                "company-id": "999",
                "project-name": "demo",
                "body": "A test comment",
                "commentNo": "1",
                "author-firstname": "Demo",
                "comment-link": "tasks/436523?c=93",
                "author-id": "999",
            }
        ]
    }


class TestTeamworkIssue:
    @pytest.fixture
    def service(self, make_service):
        # The HTTP mock must be active while the service is constructed since
        # construction hits the authentication endpoint.
        with responses.mock:
            responses.get(
                'https://test.teamwork_projects.com/authenticate.json',
                json={
                    'account': {'userId': 5, 'firstname': 'Greg', 'lastname': 'McCoy'}
                },
            )
            return make_service()

    @responses.activate
    def test_to_taskwarrior(self, service, record, extra):
        issue = service.get_issue_for_record(record["todo-items"][0], extra)
        data = record["todo-items"][0]
        expected_data = {
            'project': data["project-name"],
            'priority': "H",
            'due': datetime(2019, 12, 12, 10, 6, 31, tzinfo=UTC),
            'entry': datetime(2018, 12, 12, 10, 6, 31, tzinfo=UTC),
            'end': "",
            'modified': datetime(2019, 1, 16, 11, 0, 44, tzinfo=UTC),
            issue.URL: "https://test.teamwork_projects.com/#/tasks/5",
            issue.TITLE: data["content"],
            issue.DESCRIPTION_LONG: data["description"],
            issue.PROJECT_ID: int(data["project-id"]),
            issue.STATUS: "Open",
            issue.ID: int(data["id"]),
            "annotations": [('Greg McCoy', 'Test comment'), ('Bob Test', 'testing')],
        }
        actual_output = issue.to_taskwarrior()
        assert actual_output == expected_data

    @responses.activate
    def test_issues(self, service, record, comments):
        responses.get(
            'https://test.teamwork_projects.com/tasks/5/comments.json', json=comments
        )
        responses.get('https://test.teamwork_projects.com/tasks.json', json=record)
        issue = next(service.issues())
        data = record["todo-items"][0]
        expected_data = {
            'project': data["project-name"],
            'priority': "H",
            'due': datetime(2019, 12, 12, 10, 6, 31, tzinfo=UTC),
            'entry': datetime(2018, 12, 12, 10, 6, 31, tzinfo=UTC),
            'end': "",
            'modified': datetime(2019, 1, 16, 11, 0, 44, tzinfo=UTC),
            'description': '(bw)Is#5 - This is a test issue .. https://test.teamwork_projects.com/#/tasks/5',
            issue.URL: "https://test.teamwork_projects.com/#/tasks/5",
            issue.TITLE: data["content"],
            issue.DESCRIPTION_LONG: data["description"],
            issue.PROJECT_ID: int(data["project-id"]),
            issue.STATUS: "Open",
            issue.ID: int(data["id"]),
            "annotations": ['@Demo User - A test comment'],
            "tags": [],
        }
        assert TaskConstructor(issue).get_taskwarrior_record() == expected_data
