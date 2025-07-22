from unittest import mock
from .base import AbstractServiceTest, ServiceTest

import copy
from dataclasses import asdict
from datetime import datetime

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.todoist import TodoistService, TodoistClient

from todoist_api_python.models import Task, Project, Section, Collaborator
from todoist_api_python.models import Due, Deadline, Duration


class TestTodoistIssue(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        "service": "todoist",
        "token": "TESTTOKEN",
    }

    # Base test record
    test_record = TodoistClient.task_to_dict(Task(
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
    ))

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

    def test_to_taskwarrior(self):
        issue = self.service.get_issue_for_record(self.test_record, self.test_extra)

        expected = {
            "annotations": [],
            "due": datetime(year=2025, month=7, day=31),
            "entry": datetime(year=2025, month=7, day=1, hour=4, minute=30, second=0),
            "status": "pending",
            "priority": "H",
            "project": "TESTPROJECT",
            "scheduled": datetime(year=2025, month=7, day=1),
            "status": "pending",
            "tags": [],  # by default labels are not mapped to tags
            issue.ASSIGNEE: "TESTUSER1 <testuser1@example.com>",
            issue.ASSIGNER: "TESTUSER2 <testuser2@example.com>",
            issue.CONTENT: "TESTTASK",
            issue.DESCRIPTION: "TESTTASKDESCRIPTION",
            issue.DUE: datetime(year=2025, month=7, day=1),
            issue.DEADLINE: datetime(year=2025, month=7, day=31),
            issue.DURATION: "15 minute",
            issue.ID: "1111111111111111",
            issue.SECTION: "TESTSECTION",
            issue.URL: "https://app.todoist.com/app/task/testtask-1111111111111111",
        }

        actual = issue.to_taskwarrior()

        self.assertEqual(actual, expected)

    def test_to_taskwarrior_with_labels(self):
        # Test lables when `import_labels_as_tags` is enabled
        overrides = {
            "import_labels_as_tags": "True",
        }
        service = self.get_mock_service(TodoistService, config_overrides=overrides)
        issue = service.get_issue_for_record(self.test_record, self.test_extra)
        actual = issue.to_taskwarrior()
        self.assertEqual(actual.get("tags"),  ["TESTLABEL"])

    def test_to_taskwarrior_task_with_low_priority(self):
        # Test with priority set to lowest (1 in the API, which is P4 on the Todoist UI)
        test_record = copy.copy(self.test_record)
        test_record["priority"] = 1
        issue = self.service.get_issue_for_record(test_record, self.test_extra)
        actual = issue.to_taskwarrior()
        self.assertIs(actual.get("priority"), None)

    def test_to_taskwarrior_task_with_due_date_only_default_setting(self):
        # Test that when the "default" due date mapping is used and task has only a due date.
        # due->due, scheduled is None
        test_record = copy.copy(self.test_record)
        test_record["due"] = asdict(Due(
            date=datetime(year=2025, month=7, day=1),
            string="",
            lang="en",
            is_recurring=False,
        ))
        test_record["deadline"] = None
        issue = self.service.get_issue_for_record(test_record, self.test_extra)
        actual = issue.to_taskwarrior()
        self.assertEqual(actual["scheduled"], None)
        self.assertEqual(actual["due"], datetime(year=2025, month=7, day=1))

    def test_to_taskwarrior_task_with_due_and_deadline_default_setting(self):
        # Test that when the "default" due date mapping is used and task has both a due date
        # and a deadline. due->scheduled and deadline->due
        test_record = copy.copy(self.test_record)
        test_record["due"] = asdict(Due(
            date=datetime(year=2025, month=7, day=1),
            string="",
            lang="en",
            is_recurring=False,
        ))
        test_record["deadline"] = asdict(Deadline(
            date=datetime(year=2025, month=7, day=31),
            lang="en",
        ))
        issue = self.service.get_issue_for_record(test_record, self.test_extra)
        actual = issue.to_taskwarrior()
        self.assertEqual(actual.get("scheduled"), datetime(year=2025, month=7, day=1))
        self.assertEqual(actual.get("due"), datetime(year=2025, month=7, day=31))

    def test_to_taskwarrior_task_with_due_date_only_due_setting(self):
        # Test that when the "due" due date mapping is used and task has only a due date.
        # due->due, scheduled is None
        overrides = {
            "due_date_mapping": "always_due",
        }
        service = self.get_mock_service(TodoistService, config_overrides=overrides)
        test_record = copy.copy(self.test_record)
        test_record["due"] = asdict(Due(
            date=datetime(year=2025, month=7, day=1),
            string="",
            lang="en",
            is_recurring=False,
        ))
        test_record["deadline"] = None
        issue = service.get_issue_for_record(test_record, self.test_extra)
        actual = issue.to_taskwarrior()
        self.assertEqual(actual.get("scheduled"), None)
        self.assertEqual(actual.get("due"), datetime(year=2025, month=7, day=1))

    def test_to_taskwarrior_task_with_due_and_deadline_due_setting(self):
        # Test that when the "due" due date mapping is used and task has both a due date
        # and a deadline. due->due and deadline is None
        overrides = {
            "due_date_mapping": "always_due",
        }
        service = self.get_mock_service(TodoistService, config_overrides=overrides)
        test_record = copy.copy(self.test_record)
        test_record["due"] = asdict(Due(
            date=datetime(year=2025, month=7, day=1),
            string="",
            lang="en",
            is_recurring=False,
        ))
        test_record["deadline"] = asdict(Deadline(
            date=datetime(year=2025, month=7, day=31),
            lang="en",
        ))
        issue = service.get_issue_for_record(test_record, self.test_extra)
        actual = issue.to_taskwarrior()
        self.assertEqual(actual.get("scheduled"), None)
        self.assertEqual(actual.get("due"), datetime(year=2025, month=7, day=1))

    def test_to_taskwarrior_task_with_due_date_only_scheduled_setting(self):
        # Test that when the "scheduled" due date mapping is used and task has only a due date
        # due->scheduled and due is None
        overrides = {
            "due_date_mapping": "always_scheduled",
        }
        service = self.get_mock_service(TodoistService, config_overrides=overrides)
        test_record = copy.copy(self.test_record)
        test_record["due"] = asdict(Due(
            date=datetime(year=2025, month=7, day=1),
            string="",
            lang="en",
            is_recurring=False,
        ))
        test_record["deadline"] = None
        issue = service.get_issue_for_record(test_record, self.test_extra)
        actual = issue.to_taskwarrior()
        self.assertEqual(actual.get("scheduled"), datetime(year=2025, month=7, day=1))
        self.assertEqual(actual.get("due"), None)

    def test_to_taskwarrior_task_with_due_and_deadline_scheduled_setting(self):
        # Test that when the "due" due date mapping is used and task has both a due date
        # and a deadline due->due and deadline->None
        overrides = {
            "due_date_mapping": "always_scheduled",
        }
        service = self.get_mock_service(TodoistService, config_overrides=overrides)
        test_record = copy.copy(self.test_record)
        test_record["due"] = asdict(Due(
            date=datetime(year=2025, month=7, day=1),
            string="",
            lang="en",
            is_recurring=False,
        ))
        test_record["deadline"] = asdict(Deadline(
            date=datetime(year=2025, month=7, day=31),
            lang="en",
        ))
        issue = service.get_issue_for_record(test_record, self.test_extra)
        actual = issue.to_taskwarrior()
        self.assertEqual(actual.get("scheduled"), datetime(year=2025, month=7, day=1))
        self.assertEqual(actual.get("due"), datetime(year=2025, month=7, day=31))

    def test_issues(self):
        self.service.client.get_projects.return_value = [self.test_project]
        self.service.client.get_sections.return_value = [self.test_section]
        self.service.client.get_users.return_value = [self.test_user1, self.test_user2]
        self.service.client.get_issues.return_value = [self.test_record]
        issue = next(self.service.issues())

        expected = {
            "annotations": [],
            "description": "(bw)Is#1111111111111111"
            + " - TESTTASK"
            + " .. https://app.todoist.com/app/task/testtask-1111111111111111",
            "due": datetime(year=2025, month=7, day=31),
            "entry": datetime(year=2025, month=7, day=1, hour=4, minute=30, second=0),
            "status": "pending",
            "priority": "H",
            "project": "TESTPROJECT",
            "scheduled": datetime(year=2025, month=7, day=1),
            "tags": [],  # by default labels are not maped to tags
            issue.ASSIGNEE: "TESTUSER1 <testuser1@example.com>",
            issue.ASSIGNER: "TESTUSER2 <testuser2@example.com>",
            issue.CONTENT: "TESTTASK",
            issue.DESCRIPTION: "TESTTASKDESCRIPTION",
            issue.DUE: datetime(year=2025, month=7, day=1),
            issue.DEADLINE: datetime(year=2025, month=7, day=31),
            issue.DURATION: "15 minute",
            issue.ID: "1111111111111111",
            issue.SECTION: "TESTSECTION",
            issue.URL: "https://app.todoist.com/app/task/testtask-1111111111111111",
        }

        self.assertEqual(TaskConstructor(issue).get_taskwarrior_record(), expected)
