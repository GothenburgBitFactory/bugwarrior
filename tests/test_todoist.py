from unittest import mock
from .base import AbstractServiceTest, ServiceTest

from datetime import datetime

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.todoist import TodoistService, TodoistClient

# The latest todoist_api_python does not support python 3.8
# only run test for python 3.9 and higher.
import sys
if sys.version_info >= (3, 9):

    from todoist_api_python.models import Task, Due, Project, ApiDate

    class TestTodoistIssue(AbstractServiceTest, ServiceTest):
        SERVICE_CONFIG = {
            "service": "todoist",
            "token": "TESTTOKEN",
        }

        test_record = Task(
            id="1111111111111111",
            content="TESTTASK",
            description="TESTTASKDESCRIPTION",
            project_id="2222222222222222",
            section_id=None,
            parent_id=None,
            labels=[],
            priority=1,
            due=Due(
                date=datetime(year=2025, month=7, day=1),
                string="",
                lang="en",
                is_recurring=False,
            ),
            deadline=None,
            duration=None,
            is_collapsed=False,
            order=1,
            assignee_id=None,
            assigner_id=None,
            completed_at=None,
            creator_id="333333",
            created_at=ApiDate(),
            updated_at=ApiDate(),
        )

        test_extra = {
            "project": "TESTPROJECT",
            "section": None,
            "assignee": None,
            "duration": None,
        }

        test_project = Project(
            id="2222222222222222",
            name="TESTPROJECT",
            description="TESTPROJECTDESCRIPTION",
            order=1,
            color="",
            is_collapsed=False,
            is_shared=False,
            is_favorite=False,
            is_archived=False,
            can_assign_tasks=False,
            view_style="list",
            created_at=ApiDate(),
            updated_at=ApiDate(),
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
                "scheduled": datetime(year=2025, month=7, day=1),
                "status": "pending",
                "tags": [],
                issue.ASSIGNEE: None,
                issue.CONTENT: "TESTTASK",
                issue.DESCRIPTION: "TESTTASKDESCRIPTION",
                issue.DURATION: None,
                issue.ID: "1111111111111111",
                issue.SECTION: None,
                issue.URL: "https://app.todoist.com/app/task/testtask-1111111111111111",
            }

            actual = issue.to_taskwarrior()

            self.assertEqual(actual, expected)

        def test_issues(self):
            self.service.client.get_projects.return_value = [self.test_project]
            self.service.client.get_issues.return_value = [[self.test_record]]
            issue = next(self.service.issues())

            expected = {
                "description": "(bw)Is#1111111111111111"
                + " - TESTTASK"
                + " .. https://app.todoist.com/app/task/testtask-1111111111111111",
                "due": None,
                "status": "pending",
                "priority": "H",
                "project": "TESTPROJECT",
                "scheduled": datetime(year=2025, month=7, day=1),
                "tags": [],
                issue.ASSIGNEE: None,
                issue.CONTENT: "TESTTASK",
                issue.DESCRIPTION: "TESTTASKDESCRIPTION",
                issue.DURATION: None,
                issue.ID: "1111111111111111",
                issue.SECTION: None,
                issue.URL: "https://app.todoist.com/app/task/testtask-1111111111111111",
            }

            self.assertEqual(TaskConstructor(issue).get_taskwarrior_record(), expected)
