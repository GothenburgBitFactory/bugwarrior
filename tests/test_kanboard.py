import datetime
from unittest import mock

from dateutil.tz.tz import tzutc

from bugwarrior.config import ServiceConfig
from bugwarrior.config.load import BugwarriorConfigParser
from bugwarrior.services.kanboard import KanboardService

from .base import AbstractServiceTest, ConfigTest, ServiceTest


class TestKanboardServiceConfig(ConfigTest):
    def setUp(self):
        super().setUp()
        self.config = BugwarriorConfigParser()
        self.config.add_section("general")
        self.config.add_section("kb")
        self.service_config = ServiceConfig(
            KanboardService.CONFIG_PREFIX, self.config, "kb"
        )

    @mock.patch("bugwarrior.services.kanboard.die")
    def test_validate_config_required_fields(self, die):
        self.config.set("kb", "kanboard.url", "http://example.com/")
        self.config.set("kb", "kanboard.username", "myuser")
        self.config.set("kb", "kanboard.password", "mypass")
        KanboardService.validate_config(self.service_config, "kb")
        die.assert_not_called()

    @mock.patch("bugwarrior.services.kanboard.die")
    def test_validate_config_no_url(self, die):
        self.config.set("kb", "kanboard.username", "myuser")
        self.config.set("kb", "kanboard.password", "mypass")
        KanboardService.validate_config(self.service_config, "kb")
        die.assert_called_with("[kb] has no 'kanboard.url'")

    @mock.patch("bugwarrior.services.kanboard.die")
    def test_validate_config_no_username(self, die):
        self.config.set("kb", "kanboard.url", "http://one.com/")
        self.config.set("kb", "kanboard.password", "mypass")
        KanboardService.validate_config(self.service_config, "kb")
        die.assert_called_with("[kb] has no 'kanboard.username'")

    @mock.patch("bugwarrior.services.kanboard.die")
    def test_validate_config_no_password(self, die):
        self.config.set("kb", "kanboard.url", "http://one.com/")
        self.config.set("kb", "kanboard.username", "myuser")
        KanboardService.validate_config(self.service_config, "kb")
        die.assert_called_with("[kb] has no 'kanboard.password'")

    def test_get_keyring_service(self):
        self.config.set("kb", "kanboard.url", "http://example.com/")
        self.config.set("kb", "kanboard.username", "myuser")
        self.assertEqual(
            KanboardService.get_keyring_service(self.service_config),
            "kanboard://myuser@example.com",
        )


class TestKanboardService(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        "kanboard.url": "http://example.com",
        "kanboard.username": "myuser",
        "kanboard.password": "mypass",
    }

    def setUp(self):
        super().setUp()
        with mock.patch("kanboard.Client"):
            self.service = self.get_mock_service(KanboardService)

    def get_mock_service(self, *args, **kwargs):
        service = super().get_mock_service(*args, **kwargs)
        service.client = mock.MagicMock()
        return service

    def test_annotations_zero_comments(self):
        task = {"id": 1, "nb_comments": 0}
        url = "ignore"

        annotations = self.service.annotations(task, url)

        self.assertListEqual(annotations, [])
        self.service.client.get_all_comments.assert_not_called()

    def test_annotations_some_comments(self):
        task = {"id": 1, "nb_comments": 2}
        url = "ignore"

        self.service.client.get_all_comments.return_value = [
            {"name": "a", "comment": "c1"},
            {"name": "b", "comment": "c2"},
        ]
        annotations = self.service.annotations(task, url)

        self.assertListEqual(annotations, ["@a - c1", "@b - c2"])
        self.service.client.get_all_comments.assert_called_once_with(task_id=1)

    def test_to_taskwarrior(self):
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
            "annotations": [
                "One",
                "Two",
            ],
            "tags": [
                "tag",
            ],
        }

        issue = self.service.get_issue_for_record(record, extra)

        expected_output = {
            "project": record["project_name"],
            "priority": issue.PRIORITY_MAP[record["priority"]],
            "annotations": extra["annotations"],
            "tags": extra["tags"],
            "due": None,
            "entry": datetime.datetime(2015, 6, 13, 20, 30, 46, tzinfo=tzutc()),
            issue.TASK_ID: int(record["id"]),
            issue.TASK_TITLE: record["title"],
            issue.TASK_DESCRIPTION: record["description"],
            issue.PROJECT_ID: int(record["project_id"]),
            issue.PROJECT_NAME: record["project_name"],
            issue.URL: extra["url"],
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

    def test_issues(self):
        # Setup the fake client
        self.service.client.get_my_projects_list.return_value = {"1": "project"}
        self.service.client.search_tasks.return_value = [
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
        self.service.client.get_task.return_value = {
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
        self.service.client.get_task_tags.return_value = {"1": "tag1", "2": "tag2"}

        issue = next(self.service.issues())

        # Check calls on the client
        self.service.client.get_my_projects_list.assert_called_once_with()
        self.service.client.search_tasks.assert_called_once_with(
            project_id="1", query=self.service.query
        )
        self.service.client.get_task.assert_called_once_with(task_id="3")
        self.service.client.get_task_tags.assert_called_once_with(task_id="3")

        expected = {
            "description": "(bw)Is#3 - T3 .. http://example.com?task_id=3&project_id=1",
            "due": None,
            "entry": datetime.datetime(2016, 4, 22, 22, 46, 4, tzinfo=tzutc()),
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

        self.assertEqual(issue.get_taskwarrior_record(), expected)
