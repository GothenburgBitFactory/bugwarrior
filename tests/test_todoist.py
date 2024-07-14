from unittest import mock

from .base import AbstractServiceTest, ServiceTest
from bugwarrior.services.todoist import TodoistService, TodoistClient

from todoist_api_python.api import Task, Project


class TestTodoistIssue(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        "service": "todoist",
        "token": "TESTTOKEN",
    }

    test_record = Task(
        content="TEST",
        assignee_id=None,
        assigner_id=None,
        comment_count=0,
        is_completed=False,
        created_at=None,
        creator_id=None,
        description="Testing",
        due=None,
        duration=0,
        id="123456789",
        labels=None,
        order=0,
        parent_id=None,
        priority=1,
        project_id="123456789",
        section_id=None,
        url="https://todoist.com/app/task/123456789",
    )
    test_extra = {
        "project": "TESTPROJECT",
        "assignee": None,
    }
    test_project = Project(
        color=None,
        comment_count=0,
        id="123456789",
        is_favorite=False,
        is_inbox_project=False,
        is_shared=False,
        is_team_inbox=False,
        can_assign_tasks=False,
        name="TESTPROJECT",
        order=0,
        parent_id=None,
        url="https://todoist.com/app/project/123456789",
        view_style=None,
    )

    def setUp(self):
        super().setUp()

        self.service = self.get_mock_service(TodoistService)
        self.service.client = mock.MagicMock(spec=TodoistClient)
        self.service.client.get_issues = mock.MagicMock(
            return_value=[self.test_record, self.test_extra]
        )

    def test_to_taskwarrior(self):
        issue = self.service.get_issue_for_record(self.test_record, self.test_extra)

        expected = {
            "due": None,
            "status": "pending",
            "priority": "H",
            "project": "TESTPROJECT",
            "tags": [],
            issue.ASSIGNEE: None,
            issue.CONTENT: "TEST",
            issue.DESCRIPTION: "Testing",
            issue.ID: "123456789",
            issue.SYNC_ID: None,
            issue.URL: "https://todoist.com/app/task/123456789",
        }

        actual = issue.to_taskwarrior()

        self.assertEqual(actual, expected)

    def test_issues(self):
        self.service.client.get_projects.return_value = [self.test_project]
        self.service.client.get_issues.return_value = [self.test_record]
        issue = next(self.service.issues())

        expected = {
            "description": "(bw)Is#123456789"
            + " - TEST"
            + " .. https://todoist.com/app/task/123456789",
            "due": None,
            "status": "pending",
            "priority": "H",
            "project": "TESTPROJECT",
            "tags": [],
            issue.ASSIGNEE: None,
            issue.CONTENT: "TEST",
            issue.DESCRIPTION: "Testing",
            issue.ID: "123456789",
            issue.SYNC_ID: None,
            issue.URL: "https://todoist.com/app/task/123456789",
        }

        self.assertEqual(issue.get_taskwarrior_record(), expected)
