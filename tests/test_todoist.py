from unittest import mock
from .base import AbstractServiceTest, ServiceTest

from datetime import datetime

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.todoist import TodoistService, TodoistClient

# The latest todoist_api_python does not support python 3.8
# only run test for python 3.9 and higher.
import sys
if sys.version_info >= (3, 9):

    from todoist_api_python.models import Task, Project, Section, Collaborator
    from todoist_api_python.models import Due, Deadline, Duration, ApiDate

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
            section_id="4444444444444444",
            parent_id=None,
            labels=["TESTLABEL"],
            priority=4,
            due=Due(
                date=datetime(year=2025, month=7, day=1),
                string="",
                lang="en",
                is_recurring=False,
            ),
            deadline=Deadline(
                date=datetime(year=2025, month=7, day=31),
                lang="en",
            ),
            duration=Duration(
                amount=15,
                unit="minute",
            ),
            is_collapsed=False,
            order=1,
            assignee_id="5555555555555555",
            assigner_id="6666666666666666",
            completed_at=None,
            creator_id="333333",
            created_at=datetime(year=2025, month=7, day=1, hour=4, minute=30, second=0),
            updated_at=datetime(year=2025, month=7, day=2, hour=8, minute=0, second=0),
        )

        test_extra = {
            "project": "TESTPROJECT",
            "section": "TESTSECTION",
            "assignee": "TESTUSER1 <testuser1@example.com>",
            "assigner": "TESTUSER2 <testuser2@example.com>",
            "duration": "15 minute",
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
            created_at=datetime(year=2025, month=7, day=1, hour=4, minute=30, second=0),
            updated_at=datetime(year=2025, month=7, day=2, hour=8, minute=0, second=0),
        )

        test_section = Section(
            id="4444444444444444",
            name="TESTSECTION",
            project_id="2222222222222222",
            is_collapsed=False,
            order=1,
        )

        test_user1 = Collaborator(
            id="5555555555555555",
            name="TESTUSER1",
            email="testuser1@example.com"
        )

        test_user2 = Collaborator(
            id="6666666666666666",
            name="TESTUSER2",
            email="testuser2@example.com"
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
                "due": datetime(year=2025, month=7, day=31),
                "entry": datetime(year=2025, month=7, day=1, hour=4, minute=30, second=0),
                "status": "pending",
                "priority": "H",
                "project": "TESTPROJECT",
                "scheduled": datetime(year=2025, month=7, day=1),
                "status": "pending",
                "tags": ["TESTLABEL"],
                issue.ASSIGNEE: "TESTUSER1 <testuser1@example.com>",
                issue.ASSIGNER: "TESTUSER2 <testuser2@example.com>",
                issue.CONTENT: "TESTTASK",
                issue.DESCRIPTION: "TESTTASKDESCRIPTION",
                issue.DURATION: "15 minute",
                issue.ID: "1111111111111111",
                issue.SECTION: "TESTSECTION",
                issue.URL: "https://app.todoist.com/app/task/testtask-1111111111111111",
            }

            actual = issue.to_taskwarrior()

            self.assertEqual(actual, expected)

        def test_issues(self):
            self.service.client.get_projects.return_value = [self.test_project]
            self.service.client.get_sections.return_value = [self.test_section]
            self.service.client.get_users.return_value = [self.test_user1, self.test_user2]
            self.service.client.get_issues.return_value = [[self.test_record]]
            issue = next(self.service.issues())

            expected = {
                "description": "(bw)Is#1111111111111111"
                + " - TESTTASK"
                + " .. https://app.todoist.com/app/task/testtask-1111111111111111",
                "due": datetime(year=2025, month=7, day=31),
                "entry": datetime(year=2025, month=7, day=1, hour=4, minute=30, second=0),
                "status": "pending",
                "priority": "H",
                "project": "TESTPROJECT",
                "scheduled": datetime(year=2025, month=7, day=1),
                "tags": ["TESTLABEL"],
                issue.ASSIGNEE: "TESTUSER1 <testuser1@example.com>",
                issue.ASSIGNER: "TESTUSER2 <testuser2@example.com>",
                issue.CONTENT: "TESTTASK",
                issue.DESCRIPTION: "TESTTASKDESCRIPTION",
                issue.DURATION: "15 minute",
                issue.ID: "1111111111111111",
                issue.SECTION: "TESTSECTION",
                issue.URL: "https://app.todoist.com/app/task/testtask-1111111111111111",
            }

            self.assertEqual(TaskConstructor(issue).get_taskwarrior_record(), expected)
