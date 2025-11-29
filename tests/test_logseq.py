import copy
import datetime
from unittest import mock

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.logseq import LogseqClient, LogseqIssue, LogseqService

from .base import AbstractServiceTest, ServiceTest


class TestLogseqIssue(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        "service": "logseq",
        "host": "localhost",
        "port": 12315,
        "token": "TESTTOKEN",
    }

    test_record = {
        "properties": {
            "id": "67dae9ea-8e4d-4ad1-91dc-72aacc72a802",
            "duration": '{"TODO":[0,1699562197346]}',
        },
        "priority": "C",
        "properties-order": ["duration", "id"],
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
        "content": (
            "DOING [#C] Do something http://example.com/page#NotATag `#code`"
            " #[[Test tag one]] #[[TestTagTwo]] #TestTagThree\n"
            "SCHEDULED: <2025-07-01 Tue>\n"
            "DEADLINE: <2025-07-31 Thu>\n"
            "id:: 67dae9ea-8e4d-4ad1-91dc-72aacc72a802\n"
            ":LOGBOOK:\n"
            "CLOCK: [2025-06-03 Tue 13:56:47]--[2025-06-03 Tue 13:56:49] =>  00:00:02\n"
            ":END:"
        ),
        "properties-text-values": {
            "duration": '{"TODO":[0,1699562197346]}',
            "id": "67dae9ea-8e4d-4ad1-91dc-72aacc72a802",
        },
        "marker": "DOING",
        "page": {"id": 7070},
        "left": {"id": 7109},
        "format": "markdown",
        "refs": [{"id": 4}, {"id": 10}, {"id": 555}, {"id": 568}],
    }

    test_extra = {
        "baseURI": "logseq://graph/Test?block-id=",
        "graph": "Test",
        "page_title": "TestPageTitle",
    }

    test_page = {
        "updatedAt": 1751385600000,
        "journalDay": 20250701,
        "createdAt": 1751371200000,
        "id": 19,
        "name": "jul 1st, 2025",
        "uuid": "6692f0c1-f610-40e3-840f-ba763627de40",
        "journal?": True,
        "originalName": "Jul 1st, 2025",
        "file": {"id": 25},
        "format": "markdown",
    }

    def setUp(self):
        super().setUp()

        self.service = self.get_mock_service(LogseqService)
        self.service.client = mock.MagicMock(spec=LogseqClient)

    def test_to_taskwarrior(self):
        issue = self.service.get_issue_for_record(self.test_record, self.test_extra)

        expected = {
            "annotations": [],
            "due": datetime.datetime(year=2025, month=7, day=31),
            "scheduled": datetime.datetime(year=2025, month=7, day=1),
            "wait": None,
            "status": "pending",
            "priority": "L",
            "project": self.test_extra["graph"],
            "tags": [],
            issue.ID: int(self.test_record["id"]),
            issue.UUID: self.test_record["uuid"],
            issue.STATE: self.test_record["marker"],
            issue.TITLE: "Do something http://example.com/page#NotATag `#code`"
            + " #【Test tag one】 #【TestTagTwo】 #TestTagThree",
            issue.URI: self.test_extra["baseURI"] + self.test_record["uuid"],
            issue.SCHEDULED: datetime.datetime(year=2025, month=7, day=1),
            issue.DEADLINE: datetime.datetime(year=2025, month=7, day=31),
            issue.PAGE: "TestPageTitle",
        }

        actual = issue.to_taskwarrior()

        self.assertEqual(actual, expected)

    def test_to_taskwarrior_with_tags(self):
        overrides = {"import_labels_as_tags": "True"}
        service = self.get_mock_service(LogseqService, config_overrides=overrides)
        issue = service.get_issue_for_record(self.test_record, self.test_extra)

        actual = issue.to_taskwarrior()
        self.assertEqual(actual["tags"], ["Testtagone", "TestTagTwo", "TestTagThree"])

    def test_to_taskwarrior_todo(self):
        test_record = copy.copy(self.test_record)
        test_record["content"] = "TODO test task in todo state\n"
        test_record["marker"] = "TODO"
        issue = self.service.get_issue_for_record(test_record, self.test_extra)
        actual = issue.to_taskwarrior()
        self.assertEqual(actual["status"], "pending")

    def test_to_taskwarrior_waiting(self):
        test_record = copy.copy(self.test_record)
        test_record["content"] = "WAITING test task in waiting state\n"
        test_record["marker"] = "WAITING"
        issue = self.service.get_issue_for_record(test_record, self.test_extra)
        actual = issue.to_taskwarrior()
        self.assertEqual(actual["status"], "pending")
        self.assertEqual(actual["wait"], LogseqIssue.SOMEDAY)

    def test_to_taskwarrior_dates_with_time(self):
        test_record = copy.copy(self.test_record)
        test_record["content"] = (
            "DOING test schedule and deadline dates with times\n"
            "SCHEDULED: <2025-07-01 Tue 12:30>\n"
            "DEADLINE: <2025-07-31 Thu 12:30>"
        )
        print(test_record)

        issue = self.service.get_issue_for_record(test_record, self.test_extra)
        actual = issue.to_taskwarrior()

        scheduled = datetime.datetime(year=2025, month=7, day=1, hour=12, minute=30)
        deadline = datetime.datetime(year=2025, month=7, day=31, hour=12, minute=30)
        self.assertEqual(actual["scheduled"], scheduled)
        self.assertEqual(actual["due"], deadline)
        self.assertEqual(actual[issue.SCHEDULED], scheduled)
        self.assertEqual(actual[issue.DEADLINE], deadline)

    def test_to_taskwarrior_dates_with_repeat(self):
        test_record = copy.copy(self.test_record)
        test_record["content"] = (
            "DOING test schedule and deadline dates with times\n"
            "SCHEDULED: <2025-07-01 Tue 12:30 .+1d>\n"
            "DEADLINE: <2025-07-31 Thu .+1d>"
        )
        print(test_record)

        issue = self.service.get_issue_for_record(test_record, self.test_extra)
        actual = issue.to_taskwarrior()

        scheduled = datetime.datetime(year=2025, month=7, day=1, hour=12, minute=30)
        deadline = datetime.datetime(year=2025, month=7, day=31)
        self.assertEqual(actual["scheduled"], scheduled)
        self.assertEqual(actual["due"], deadline)
        self.assertEqual(actual[issue.SCHEDULED], scheduled)
        self.assertEqual(actual[issue.DEADLINE], deadline)

    def test_issues(self):
        self.service.client.get_graph_name.return_value = self.test_extra["graph"]
        self.service.client.get_issues.return_value = [[self.test_record]]
        self.service.client.get_page.return_value = self.test_page
        issue = next(self.service.issues())

        expected = {
            "annotations": [],
            "description": f"(bw)#{self.test_record['id']}"
            + " - Do something http://example.com/page#NotATag `#code`"
            + " #【Test tag one】 #【TestTagTwo】 #TestTagThree"
            + " .. "
            + self.test_extra["baseURI"]
            + self.test_record["uuid"],
            "due": datetime.datetime(year=2025, month=7, day=31),
            "scheduled": datetime.datetime(year=2025, month=7, day=1),
            "wait": None,
            "status": "pending",
            "priority": "L",
            "project": self.test_extra["graph"],
            "tags": [],
            issue.ID: int(self.test_record["id"]),
            issue.UUID: self.test_record["uuid"],
            issue.STATE: self.test_record["marker"],
            issue.TITLE: "Do something http://example.com/page#NotATag `#code`"
            + " #【Test tag one】 #【TestTagTwo】 #TestTagThree",
            issue.URI: self.test_extra["baseURI"] + self.test_record["uuid"],
            issue.SCHEDULED: datetime.datetime(year=2025, month=7, day=1),
            issue.DEADLINE: datetime.datetime(year=2025, month=7, day=31),
            issue.PAGE: "Jul 1st, 2025",
        }

        self.assertEqual(TaskConstructor(issue).get_taskwarrior_record(), expected)
