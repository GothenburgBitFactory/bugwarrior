from datetime import datetime
from unittest import mock

import pytest
from todoist_api_python.models import (
    Collaborator,
    Deadline,
    Due,
    Duration,
    Project,
    Section,
    Task,
)

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.todoist import TodoistClient, TodoistService

from .base import get_mock_service

SERVICE_CONFIG = {"service": "todoist", "token": "TESTTOKEN"}


@pytest.fixture
def record():
    return TodoistClient.task_to_dict(
        Task(
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
            deadline=Deadline(date=datetime(year=2025, month=7, day=31), lang="en"),
            duration=Duration(amount=15, unit="minute"),
            is_collapsed=False,
            order=1,
            assignee_id="5555555555555555",
            assigner_id="6666666666666666",
            completed_at=None,
            creator_id="333333",
            created_at=datetime(year=2025, month=7, day=1, hour=4, minute=30, second=0),
            updated_at=datetime(year=2025, month=7, day=2, hour=8, minute=0, second=0),
        )
    )


@pytest.fixture
def extra():
    return {
        "project": "TESTPROJECT",
        "section": "TESTSECTION",
        "assignee": "TESTUSER1 <testuser1@example.com>",
        "assigner": "TESTUSER2 <testuser2@example.com>",
        "duration": "15 minute",
    }


@pytest.fixture
def project():
    return Project(
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


@pytest.fixture
def section():
    return Section(
        id="4444444444444444",
        name="TESTSECTION",
        project_id="2222222222222222",
        is_collapsed=False,
        order=1,
    )


@pytest.fixture
def users():
    return [
        Collaborator(
            id="5555555555555555", name="TESTUSER1", email="testuser1@example.com"
        ),
        Collaborator(
            id="6666666666666666", name="TESTUSER2", email="testuser2@example.com"
        ),
    ]


class TestTodoistIssue:
    @pytest.fixture
    def service(self):
        service = get_mock_service(TodoistService, SERVICE_CONFIG)
        service.client = mock.MagicMock(spec=TodoistClient)
        return service

    def test_to_taskwarrior(self, service, record, extra):
        issue = service.get_issue_for_record(record, extra)

        expected = {
            "annotations": [],
            "due": datetime(year=2025, month=7, day=1),
            "entry": datetime(year=2025, month=7, day=1, hour=4, minute=30, second=0),
            "priority": "H",
            "project": "TESTPROJECT",
            "scheduled": None,
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
            issue.PARENT_ID: None,
        }

        actual = issue.to_taskwarrior()

        assert actual == expected

    def test_to_taskwarrior_with_labels(self, record, extra):
        # Test lables when `import_labels_as_tags` is enabled
        overrides = {"import_labels_as_tags": "True"}
        service = get_mock_service(TodoistService, {**SERVICE_CONFIG, **overrides})
        issue = service.get_issue_for_record(record, extra)
        actual = issue.to_taskwarrior()
        assert actual.get("tags") == ["TESTLABEL"]

    def test_to_taskwarrior_task_with_low_priority(self, service, record, extra):
        # Test with priority set to lowest (1 in the API, which is P4 on the Todoist UI)
        record["priority"] = 1
        issue = service.get_issue_for_record(record, extra)
        actual = issue.to_taskwarrior()
        assert actual.get("priority") is None

    def test_to_taskwarrior_subtask(self, service, record, extra):
        # subtasks have a parent id
        record["parent_id"] = "1212121212121212"
        issue = service.get_issue_for_record(record, extra)
        actual = issue.to_taskwarrior()
        assert actual.get("todoistparentid") == "1212121212121212"
        assert (
            issue.get_default_description() == "(bw)Subtask ##1111111111111111"
            " - TESTTASK .."
            " https://app.todoist.com/app/task/testtask-1111111111111111"
        )

    def test_issues(self, service, record, project, section, users):
        service.client.get_projects.return_value = [project]
        service.client.get_sections.return_value = [section]
        service.client.get_users.return_value = users
        service.client.get_issues.return_value = [record]
        issue = next(service.issues())

        expected = {
            "annotations": [],
            "description": "(bw)#1111111111111111"
            + " - TESTTASK"
            + " .. https://app.todoist.com/app/task/testtask-1111111111111111",
            "due": datetime(year=2025, month=7, day=1),
            "entry": datetime(year=2025, month=7, day=1, hour=4, minute=30, second=0),
            "status": "pending",
            "priority": "H",
            "project": "TESTPROJECT",
            "scheduled": None,
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
            issue.PARENT_ID: None,
        }

        assert TaskConstructor(issue).get_taskwarrior_record() == expected
