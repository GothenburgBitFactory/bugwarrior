from datetime import datetime, timezone
from unittest import mock

import pytest

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.kanboard import KanboardService

from ..base import validate
from .base import get_mock_service

SERVICE_CONFIG = {
    "service": "kanboard",
    "url": "http://example.com",
    "username": "myuser",
    "password": "mypass",
}


class TestKanboardServiceConfig:
    @pytest.fixture
    def config(self):
        return {"general": {"targets": ["kb"]}, "kb": {"service": "kanboard"}}

    def test_validate_config_required_fields(self, config):
        config["kb"].update(
            {"url": "http://example.com/", "username": "myuser", "password": "mypass"}
        )

        validate(config)

    def test_validate_config_no_url(self, config, assert_validation_error):
        config["kb"].update({"username": "myuser", "password": "mypass"})

        assert_validation_error(config, '[kb]\nurl  <- Field required')

    def test_validate_config_no_username(self, config, assert_validation_error):
        config["kb"].update({"url": "http://one.com/", "password": "mypass"})

        assert_validation_error(config, '[kb]\nusername  <- Field required')

    def test_validate_config_no_password(self, config, assert_validation_error):
        config["kb"].update({"url": "http://one.com/", "username": "myuser"})

        assert_validation_error(config, '[kb]\npassword  <- Field required')

    def test_keyring_service(self, config):
        config["kb"].update(
            {"url": "http://example.com/", "username": "myuser", "password": "mypass"}
        )
        service_config = validate(config).service_configs[0]
        assert service_config.keyring_service == "kanboard://myuser@example.com"


class TestKanboardService:
    @pytest.fixture
    def service(self):
        with mock.patch("bugwarrior.services.kanboard.Client"):
            service = get_mock_service(KanboardService, SERVICE_CONFIG)
        service.client = mock.MagicMock()
        return service

    def test_annotations_zero_comments(self, service):
        task = {"id": 1, "nb_comments": 0}
        url = "ignore"

        annotations = service.annotations(task, url)

        assert annotations == []
        service.client.get_all_comments.assert_not_called()

    def test_annotations_some_comments(self, service):
        task = {"id": 1, "nb_comments": 2}
        url = "ignore"

        service.client.get_all_comments.return_value = [
            {"name": "a", "comment": "c1"},
            {"name": "b", "comment": "c2"},
        ]
        annotations = service.annotations(task, url)

        assert annotations == ["@a - c1", "@b - c2"]
        service.client.get_all_comments.assert_called_once_with(task_id=1)

    def test_to_taskwarrior(self, service):
        record = {
            "project_id": "2",
            "project_name": "myproject",
            "priority": "2",
            "date_due": "0",
            "date_creation": "1434227446",
            "id": "1",
            "title": "mytitle",
            "description": "mydescription",
        }

        extra = {
            "url": "http://path/to/issue",
            "annotations": ["One", "Two"],
            "tags": ["tag"],
        }

        issue = service.get_issue_for_record(record, extra)

        expected_output = {
            "project": record["project_name"],
            "priority": issue.PRIORITY_MAP[record["priority"]],
            "annotations": extra["annotations"],
            "tags": extra["tags"],
            "due": None,
            "entry": datetime(2015, 6, 13, 20, 30, 46, tzinfo=timezone.utc),
            issue.TASK_ID: int(record["id"]),
            issue.TASK_TITLE: record["title"],
            issue.TASK_DESCRIPTION: record["description"],
            issue.PROJECT_ID: int(record["project_id"]),
            issue.PROJECT_NAME: record["project_name"],
            issue.URL: extra["url"],
        }
        actual_output = issue.to_taskwarrior()

        assert actual_output == expected_output

    def test_issues(self, service):
        # Setup the fake client
        service.client.get_my_projects_list.return_value = {"1": "project"}
        service.client.search_tasks.return_value = [
            {
                "nb_comments": "0",
                "nb_files": "0",
                "nb_subtasks": "0",
                "nb_completed_subtasks": "0",
                "nb_links": "0",
                "nb_external_links": "0",
                "id": "3",
                "reference": "",
                "title": "T3",
                "description": "D3",
                "date_creation": "1461365164",
                "date_modification": "1461365164",
                "date_due": "0",
                "color_id": "yellow",
                "project_id": "1",
                "project_name": "project",
                "column_id": "5",
                "swimlane_id": "0",
                "owner_id": "0",
                "creator_id": "0",
            }
        ]
        service.client.get_task.return_value = {
            "id": "3",
            "title": "Task #3",
            "description": "",
            "date_creation": "1409963206",
            "color_id": "blue",
            "project_id": "1",
            "column_id": "2",
            "owner_id": "1",
            "position": "1",
            "is_active": "1",
            "score": "0",
            "date_due": "0",
            "category_id": "0",
            "creator_id": "0",
            "date_modification": "1409963206",
            "reference": "",
            "time_spent": "0",
            "time_estimated": "0",
            "swimlane_id": "0",
            "date_moved": "1430875287",
            "recurrence_status": "0",
            "recurrence_trigger": "0",
            "recurrence_factor": "0",
            "recurrence_timeframe": "0",
            "recurrence_basedate": "0",
            "url": "http://example.com?task_id=3&project_id=1",
        }
        service.client.get_task_tags.return_value = {"1": "tag1", "2": "tag2"}

        issue = next(service.issues())

        # Check calls on the client
        service.client.get_my_projects_list.assert_called_once_with()
        service.client.search_tasks.assert_called_once_with(
            project_id="1", query=service.query
        )
        service.client.get_task.assert_called_once_with(task_id="3")
        service.client.get_task_tags.assert_called_once_with(task_id="3")

        expected = {
            "description": "(bw)Is#3 - T3 .. http://example.com?task_id=3&project_id=1",
            "due": None,
            "entry": datetime(2016, 4, 22, 22, 46, 4, tzinfo=timezone.utc),
            "annotations": [],
            "project": "project",
            "tags": ["tag1", "tag2"],
            "kanboardtaskid": 3,
            "kanboardurl": "http://example.com?task_id=3&project_id=1",
            "kanboardprojectid": 1,
            "kanboardprojectname": "project",
            "kanboardtaskdescription": "D3",
            "kanboardtasktitle": "T3",
            "priority": "M",  # default priority
        }

        assert TaskConstructor(issue).get_taskwarrior_record() == expected
