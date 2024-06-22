from unittest import mock

from .base import AbstractServiceTest, ServiceTest
from bugwarrior.services.logseq import LogseqService, LogseqClient


class TestLogseqIssue(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        "service": "logseq",
        "host": "localhost",
        "port": 12315,
        "token": "TESTTOKEN",
    }

    test_record = {
        "properties": {"duration": '{"TODO":[0,1699562197346]}'},
        "priority": "C",
        "properties-order": ["duration"],
        "parent": {"id": 7083},
        "id": 7146,
        "uuid": "66699a83-3ee0-4edc-81c6-a24c9b80bec6",
        "path-refs": [
            {"id": 4},
            {"id": 10},
            {"id": 555},
            {"id": 559},
            {"id": 568},
            {"id": 1777},
            {"id": 7070},
        ],
        "content": "DOING [#A] Do something",
        "properties-text-values": {"duration": '{"TODO":[0,1699562197346]}'},
        "marker": "DOING",
        "page": {"id": 7070},
        "left": {"id": 7109},
        "format": "markdown",
        "refs": [{"id": 4}, {"id": 10}, {"id": 555}, {"id": 568}],
    }

    test_extra = {
        "graph": "Test",
    }

    def setUp(self):
        super().setUp()

        self.service = self.get_mock_service(LogseqService)
        self.service.client = mock.MagicMock(spec=LogseqClient)
        self.service.client.get_issues = mock.MagicMock(
            return_value=[self.test_record, self.test_extra]
        )

    def test_to_taskwarrior(self):
        issue = self.service.get_issue_for_record(self.test_record, self.test_extra)

        expected = {
            "annotations": [],
            "due": None,
            "scheduled": None,
            "wait": None,
            "status": "pending",
            "priority": "L",
            "project": self.test_extra["graph"],
            "tags": [],
            issue.ID: int(self.test_record["id"]),
            issue.UUID: self.test_record["uuid"],
            issue.STATE: self.test_record["marker"],
            issue.TITLE: "DOING Do something",
            issue.DEADLINE: None,
            issue.SCHEDULED: None,
            issue.URI: "logseq://graph/Test?block-id=66699a83-3ee0-4edc-81c6-a24c9b80bec6",
        }

        actual = issue.to_taskwarrior()

        self.assertEqual(actual, expected)

    def test_issues(self):
        self.service.client.get_graph_name.return_value = self.test_extra["graph"]
        self.service.client.get_issues.return_value = [[self.test_record]]
        issue = next(self.service.issues())

        expected = {
            "annotations": [],
            "description": f"(bw)Is#{self.test_record['id']}"
            + " - DOING Do something"
            + " .. logseq://graph/Test?block-id=66699a83-3ee0-4edc-81c6-a24c9b80bec6",
            "due": None,
            "scheduled": None,
            "wait": None,
            "status": "pending",
            "priority": "L",
            "project": self.test_extra["graph"],
            "tags": [],
            issue.ID: int(self.test_record["id"]),
            issue.UUID: self.test_record["uuid"],
            issue.STATE: self.test_record["marker"],
            issue.TITLE: "DOING Do something",
            issue.DEADLINE: None,
            issue.SCHEDULED: None,
            issue.URI: "logseq://graph/Test?block-id=66699a83-3ee0-4edc-81c6-a24c9b80bec6",
        }

        self.assertEqual(issue.get_taskwarrior_record(), expected)
