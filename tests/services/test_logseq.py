import datetime
from unittest import mock

import pytest

from bugwarrior.services.logseq import LogseqClient, LogseqIssue, LogseqService

SERVICE_CLASS = LogseqService

SERVICE_CONFIG = {
    "service": "logseq",
    "host": "localhost",
    "port": 12315,
    "token": "TESTTOKEN",
}


@pytest.fixture
def record():
    return {
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


@pytest.fixture
def extra():
    return {
        "baseURI": "logseq://graph/Test?block-id=",
        "graph": "Test",
        "page_title": "TestPageTitle",
    }


@pytest.fixture
def page():
    return {
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


class TestLogseqIssue:
    @pytest.fixture
    def service(self, make_service):
        service = make_service()
        service.client = mock.MagicMock(spec=LogseqClient)
        return service

    def test_to_taskwarrior(self, service, record, extra):
        issue = service.get_issue_for_record(record, extra)

        expected = {
            "annotations": [],
            "due": datetime.datetime(year=2025, month=7, day=31),
            "scheduled": datetime.datetime(year=2025, month=7, day=1),
            "wait": None,
            "status": "pending",
            "priority": "L",
            "project": extra["graph"],
            "tags": [],
            "logseqid": str(record["id"]),
            "logsequuid": record["uuid"],
            "logseqstate": record["marker"],
            "logseqtitle": "Do something http://example.com/page#NotATag `#code`"
            + " #【Test tag one】 #【TestTagTwo】 #TestTagThree",
            "logsequri": extra["baseURI"] + record["uuid"],
            "logseqscheduled": datetime.datetime(year=2025, month=7, day=1),
            "logseqdeadline": datetime.datetime(year=2025, month=7, day=31),
            "logseqpage": "TestPageTitle",
        }

        actual = issue.to_taskwarrior().to_taskwarrior_data()

        assert actual == expected

    def test_to_taskwarrior_with_tags(self, make_service, record, extra):
        overrides = {"import_labels_as_tags": "True"}
        service = make_service(**overrides)
        issue = service.get_issue_for_record(record, extra)

        actual = issue.to_taskwarrior().to_taskwarrior_data()
        assert actual["tags"] == ["Testtagone", "TestTagTwo", "TestTagThree"]

    def test_to_taskwarrior_todo(self, service, record, extra):
        record["content"] = "TODO test task in todo state\n"
        record["marker"] = "TODO"
        issue = service.get_issue_for_record(record, extra)
        actual = issue.to_taskwarrior().to_taskwarrior_data()
        assert actual["status"] == "pending"

    def test_to_taskwarrior_waiting(self, service, record, extra):
        record["content"] = "WAITING test task in waiting state\n"
        record["marker"] = "WAITING"
        issue = service.get_issue_for_record(record, extra)
        actual = issue.to_taskwarrior().to_taskwarrior_data()
        assert actual["status"] == "pending"
        assert actual["wait"] == LogseqIssue.SOMEDAY

    def test_to_taskwarrior_dates_with_time(self, service, record, extra):
        record["content"] = (
            "DOING test schedule and deadline dates with times\n"
            "SCHEDULED: <2025-07-01 Tue 12:30>\n"
            "DEADLINE: <2025-07-31 Thu 12:30>"
        )

        issue = service.get_issue_for_record(record, extra)
        actual = issue.to_taskwarrior().to_taskwarrior_data()

        scheduled = datetime.datetime(year=2025, month=7, day=1, hour=12, minute=30)
        deadline = datetime.datetime(year=2025, month=7, day=31, hour=12, minute=30)
        assert actual["scheduled"] == scheduled
        assert actual["due"] == deadline
        assert actual["logseqscheduled"] == scheduled
        assert actual["logseqdeadline"] == deadline

    def test_to_taskwarrior_dates_with_repeat(self, service, record, extra):
        record["content"] = (
            "DOING test schedule and deadline dates with times\n"
            "SCHEDULED: <2025-07-01 Tue 12:30 .+1d>\n"
            "DEADLINE: <2025-07-31 Thu .+1d>"
        )

        issue = service.get_issue_for_record(record, extra)
        actual = issue.to_taskwarrior().to_taskwarrior_data()

        scheduled = datetime.datetime(year=2025, month=7, day=1, hour=12, minute=30)
        deadline = datetime.datetime(year=2025, month=7, day=31)
        assert actual["scheduled"] == scheduled
        assert actual["due"] == deadline
        assert actual["logseqscheduled"] == scheduled
        assert actual["logseqdeadline"] == deadline

    def test_issues(self, service, record, extra, page):
        service.client.get_graph_name.return_value = extra["graph"]
        service.client.get_issues.return_value = [[record]]
        service.client.get_page.return_value = page
        task = next(service.issues())

        expected = {
            "annotations": [],
            "description": f"(bw)#{record['id']}"
            + " - Do something http://example.com/pag"
            + " .. "
            + extra["baseURI"]
            + record["uuid"],
            "due": datetime.datetime(year=2025, month=7, day=31),
            "scheduled": datetime.datetime(year=2025, month=7, day=1),
            "wait": None,
            "status": "pending",
            "priority": "L",
            "project": extra["graph"],
            "tags": [],
            "logseqid": str(record["id"]),
            "logsequuid": record["uuid"],
            "logseqstate": record["marker"],
            "logseqtitle": "Do something http://example.com/page#NotATag `#code`"
            + " #【Test tag one】 #【TestTagTwo】 #TestTagThree",
            "logsequri": extra["baseURI"] + record["uuid"],
            "logseqscheduled": datetime.datetime(year=2025, month=7, day=1),
            "logseqdeadline": datetime.datetime(year=2025, month=7, day=31),
            "logseqpage": "Jul 1st, 2025",
        }

        assert task.to_taskwarrior_data() == expected
