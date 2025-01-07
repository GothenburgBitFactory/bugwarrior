from unittest import mock

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.logseq import LogseqService, LogseqClient

from .base import AbstractServiceTest, ServiceTest


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
        "content": "DOING [#A] Do something #[[Test tag]] #[[TestTag]] #TestTag",
        "properties-text-values": {"duration": '{"TODO":[0,1699562197346]}'},
        "marker": "DOING",
        "page": {"id": 7070},
        "left": {"id": 7109},
        "format": "markdown",
        "refs": [{"id": 4}, {"id": 10}, {"id": 555}, {"id": 568}],
    }

    test_extra = {
        "baseURI": "logseq://graph/Test?block-id=",
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
            "tags": ['TestTag', 'Testtag', 'TestTag'],
            issue.ID: int(self.test_record["id"]),
            issue.UUID: self.test_record["uuid"],
            issue.STATE: self.test_record["marker"],
            issue.TITLE: "Do something #【Test tag】 #【TestTag】 #TestTag",
            issue.URI: self.test_extra["baseURI"] + self.test_record["uuid"],
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
            + " - Do something #【Test tag】 #【TestTag】 #TestTag"
            + " .. " + self.test_extra["baseURI"] + self.test_record["uuid"],
            "due": None,
            "scheduled": None,
            "wait": None,
            "status": "pending",
            "priority": "L",
            "project": self.test_extra["graph"],
            "tags": ['TestTag', 'Testtag', 'TestTag'],
            issue.ID: int(self.test_record["id"]),
            issue.UUID: self.test_record["uuid"],
            issue.STATE: self.test_record["marker"],
            issue.TITLE: "Do something #【Test tag】 #【TestTag】 #TestTag",
            issue.URI: self.test_extra["baseURI"] + self.test_record["uuid"],
        }

        self.assertEqual(TaskConstructor(issue).get_taskwarrior_record(), expected)
