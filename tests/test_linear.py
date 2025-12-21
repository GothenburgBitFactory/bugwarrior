from datetime import datetime, timezone
import json

import responses

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.linear import LinearService

from .base import AbstractServiceTest, ConfigTest, ServiceTest

RESPONSE = json.loads(
    """
{
    "data": {
        "issues": {
            "nodes": [
                {
                    "url": "https://linear.app/dustins-doings/issue/DUS-5/do-stuff",
                    "title": "DO STUFF",
                    "description": "Better get started",
                    "assignee": {
                        "email": "djmitche@gmail.com"
                    },
                    "creator": {
                        "email": "djmitche@gmail.com"
                    },
                    "createdAt": "2025-07-24T17:03:04.239Z",
                    "updatedAt": "2025-07-25T17:03:04.239Z",
                    "completedAt": "2025-07-26T17:03:04.239Z",
                    "project": {
                        "name": "PRJ"
                    },
                    "labels": {},
                    "state": {
                        "name": "Done"
                    },
                    "identifier": "DUS-5",
                    "team": {
                        "name": "Dustin's Doings"
                    }
                },
                {
                    "url": "https://linear.app/dustins-doings/issue/DUS-1/bugwarrior",
                    "title": "Interface Bugwarrior to Linear",
                    "description": "Make a PR",
                    "assignee": {
                        "email": "djmitche@gmail.com"
                    },
                    "creator": null,
                    "completedAt": null,
                    "updatedAt": "2025-07-24T17:08:33.286Z",
                    "createdAt": "2025-07-24T15:34:07.968Z",
                    "project": null,
                    "labels": {
                        "nodes": [
                            {
                                "name": "Improvement"
                            },
                            {
                                "name": "Feature"
                            }
                        ]
                    },
                    "state": {
                        "name": "Todo"
                    },
                    "identifier": "DUS-1",
                    "team": {
                        "name": "Dustin's Doings"
                    }
                }
            ]
        }
    }
}"""
)


class TestLinearServiceConfig(ConfigTest):
    def setUp(self):
        super().setUp()
        self.config = {
            "general": {"targets": ["linear"]},
            "linear": {"service": "linear"},
        }

    def test_validate_config(self):
        self.config["linear"].update(
            {"only_if_assigned": "foo@bar.com", "api_token": "abc123"}
        )

        self.validate()

    def test_validate_config_no_api_token(self):
        self.config["linear"].update({"only_if_assigned": "foo@bar.com"})

        self.assertValidationError("[linear]\napi_token  <- Field required")

    def test_statuses_and_status_types_incompatible(self):
        self.config["linear"].update(
            {"api_token": "abc123", "statuses": "Done, Todo", "status_types": "started"}
        )
        self.assertValidationError("statuses and status_types are incompatible")

    def test_status_types_defaults_when_neither_set(self):
        self.config["linear"].update({"api_token": "abc123"})
        conf = self.validate()
        self.assertEqual(
            conf["linear"].status_types, ["backlog", "unstarted", "started"]
        )

    def test_statuses_only(self):
        self.config["linear"].update({"api_token": "abc123", "statuses": "Done, Todo"})
        conf = self.validate()
        self.assertEqual(conf["linear"].statuses, ["Done", "Todo"])
        self.assertIsNone(conf["linear"].status_types)

    def test_status_types_only(self):
        self.config["linear"].update({"api_token": "abc123", "status_types": "started"})
        conf = self.validate()
        self.assertEqual(conf["linear"].status_types, ["started"])
        self.assertEqual(conf["linear"].statuses, [])


class TestLinearIssue(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        "service": "linear",
        "api_token": "abc123",
        "import_labels_as_tags": True,
    }

    def setUp(self):
        super().setUp()
        self.service = self.get_mock_service(LinearService)
        responses.add(responses.POST, "https://api.linear.app/graphql", json=RESPONSE)

    def test_to_taskwarrior(self):
        issue = RESPONSE["data"]["issues"]["nodes"][0]
        issue = self.service.get_issue_for_record(issue, {})

        created_timestamp = datetime(2025, 7, 24, 17, 3, 4, 0, tzinfo=timezone.utc)
        updated_timestamp = datetime(2025, 7, 25, 17, 3, 4, 0, tzinfo=timezone.utc)
        closed_timestamp = datetime(2025, 7, 26, 17, 3, 4, 0, tzinfo=timezone.utc)
        expected_output = {
            "project": "prj",
            "priority": "M",
            "annotations": [],
            "tags": [],
            "linearurl": "https://linear.app/dustins-doings/issue/DUS-5/do-stuff",
            "lineardescription": "Better get started",
            "lineartitle": "DO STUFF",
            "linearidentifier": "DUS-5",
            "linearstatus": "Done",
            "linearteam": "Dustin's Doings",
            "linearcreator": "djmitche@gmail.com",
            "linearassignee": "djmitche@gmail.com",
            "linearcreated": created_timestamp,
            "linearupdated": updated_timestamp,
            "linearclosed": closed_timestamp,
        }

        actual_output = issue.to_taskwarrior()
        self.assertEqual(actual_output, expected_output)

        issue = RESPONSE["data"]["issues"]["nodes"][1]
        issue = self.service.get_issue_for_record(issue, {})

        created_timestamp = datetime(2025, 7, 24, 15, 34, 7, 0, tzinfo=timezone.utc)
        updated_timestamp = datetime(2025, 7, 24, 17, 8, 33, 0, tzinfo=timezone.utc)
        expected_output = {
            "project": None,
            "priority": "M",
            "annotations": [],
            "tags": ["Improvement", "Feature"],
            "linearurl": "https://linear.app/dustins-doings/issue/DUS-1/bugwarrior",
            "lineardescription": "Make a PR",
            "linearidentifier": "DUS-1",
            "linearstatus": "Todo",
            "lineartitle": "Interface Bugwarrior to Linear",
            "linearteam": "Dustin's Doings",
            "linearcreator": None,
            "linearassignee": "djmitche@gmail.com",
            "linearcreated": created_timestamp,
            "linearupdated": updated_timestamp,
            "linearclosed": None,
        }

        actual_output = issue.to_taskwarrior()
        self.assertEqual(actual_output, expected_output)

    @responses.activate
    def test_issues(self):
        issue = next(self.service.issues())
        created_timestamp = datetime(2025, 7, 24, 17, 3, 4, 0, tzinfo=timezone.utc)
        updated_timestamp = datetime(2025, 7, 25, 17, 3, 4, 0, tzinfo=timezone.utc)
        closed_timestamp = datetime(2025, 7, 26, 17, 3, 4, 0, tzinfo=timezone.utc)
        expected = {
            "annotations": [],
            "description": "(bw)#DUS-5 - DO STUFF .. "
            "https://linear.app/dustins-doings/issue/DUS-5/do-stuff",
            "linearassignee": "djmitche@gmail.com",
            "linearclosed": closed_timestamp,
            "linearcreated": created_timestamp,
            "linearcreator": "djmitche@gmail.com",
            "lineardescription": "Better get started",
            "lineartitle": "DO STUFF",
            "linearidentifier": "DUS-5",
            "linearstatus": "Done",
            "linearteam": "Dustin's Doings",
            "linearupdated": updated_timestamp,
            "linearurl": "https://linear.app/dustins-doings/issue/DUS-5/do-stuff",
            "priority": "M",
            "project": 'prj',
            "tags": [],
        }
        self.assertEqual(TaskConstructor(issue).get_taskwarrior_record(), expected)
