from datetime import datetime, timezone
import json

import responses

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.linear import LinearService

from .base import ConfigTest, ServiceIssueTest

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
                    "priority": 4,
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
                    "dueDate": "2025-08-22",
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
                    "priority": 1,
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
        assert conf.service_configs[0].status_types == [
            "backlog",
            "unstarted",
            "started",
        ]

    def test_statuses_only(self):
        self.config["linear"].update({"api_token": "abc123", "statuses": "Done, Todo"})
        conf = self.validate()
        assert conf.service_configs[0].statuses == ["Done", "Todo"]
        assert conf.service_configs[0].status_types is None

    def test_status_types_only(self):
        self.config["linear"].update({"api_token": "abc123", "status_types": "started"})
        conf = self.validate()
        assert conf.service_configs[0].status_types == ["started"]
        assert conf.service_configs[0].statuses == []


class TestLinearIssue(ServiceIssueTest):
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
            "priority": "L",
            "due": None,
            "entry": created_timestamp,
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
        assert actual_output == expected_output

        issue = RESPONSE["data"]["issues"]["nodes"][1]
        issue = self.service.get_issue_for_record(issue, {})

        created_timestamp = datetime(2025, 7, 24, 15, 34, 7, 0, tzinfo=timezone.utc)
        updated_timestamp = datetime(2025, 7, 24, 17, 8, 33, 0, tzinfo=timezone.utc)
        due_timestamp = datetime(2025, 8, 22, 0, 0, 0, 0, tzinfo=timezone.utc)
        expected_output = {
            "project": None,
            "priority": "H",
            "due": due_timestamp,
            "entry": created_timestamp,
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
        assert actual_output == expected_output

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
            "due": None,
            "entry": created_timestamp,
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
            "priority": "L",
            "project": 'prj',
            "tags": [],
        }
        assert TaskConstructor(issue).get_taskwarrior_record() == expected

    def test_priority_mapping(self):
        # Linear priority integers must map onto taskwarrior's H/M/L buckets,
        # with "No priority" (0) and a missing field both falling back to the
        # service-wide default.
        cases = [
            (0, "M"),  # No priority -> default_priority (M)
            (1, "H"),  # Urgent
            (2, "H"),  # High
            (3, "M"),  # Medium
            (4, "L"),  # Low
        ]
        for linear_priority, expected in cases:
            with self.subTest(linear_priority=linear_priority):
                record = {
                    **RESPONSE["data"]["issues"]["nodes"][0],
                    "priority": linear_priority,
                }
                issue = self.service.get_issue_for_record(record, {})
                assert issue.to_taskwarrior()["priority"] == expected

        # A record without a priority key at all should also fall back.
        record = {
            k: v
            for k, v in RESPONSE["data"]["issues"]["nodes"][0].items()
            if k != "priority"
        }
        issue = self.service.get_issue_for_record(record, {})
        assert issue.to_taskwarrior()["priority"] == "M"

    @responses.activate
    def test_issues_paginates(self):
        """Drains every page when Linear signals ``hasNextPage``."""
        # Reset the default mock registered in setUp so we can control page order.
        responses.reset()

        page_one = {
            "data": {
                "issues": {
                    "nodes": [RESPONSE["data"]["issues"]["nodes"][0]],
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor-page-2"},
                }
            }
        }
        page_two = {
            "data": {
                "issues": {
                    "nodes": [RESPONSE["data"]["issues"]["nodes"][1]],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }
        responses.add(responses.POST, "https://api.linear.app/graphql", json=page_one)
        responses.add(responses.POST, "https://api.linear.app/graphql", json=page_two)

        identifiers = [issue.record["identifier"] for issue in self.service.issues()]
        assert identifiers == ["DUS-5", "DUS-1"]

        # Two HTTP calls were made, and the second one carried the cursor
        # returned by the first.
        assert len(responses.calls) == 2
        first_body = json.loads(responses.calls[0].request.body)
        second_body = json.loads(responses.calls[1].request.body)
        assert first_body["variables"]["after"] is None
        assert second_body["variables"]["after"] == "cursor-page-2"
