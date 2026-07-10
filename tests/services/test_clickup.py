from datetime import datetime, timezone

import pytest
import responses

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.clickup import ClickupClient, ClickupService

from ..base import get_validated_service, validate
from .base import get_mock_service


@pytest.fixture
def record():
    return {
        "id": "86adrdd2j",
        "custom_id": None,
        "custom_item_id": 0,
        "name": "My task",
        "text_content": "",
        "description": "",
        "status": {
            "status": "mystatus",
            "id": "p901312298283_rBjB6Xxi",
            "color": "#b660e0",
            "type": "custom",
            "orderindex": 4,
        },
        "orderindex": "1.00000282100000000000000000000000",
        "date_created": "1765390998981",
        "date_updated": "1765391016301",
        "date_closed": None,
        "date_done": None,
        "archived": False,
        "creator": {
            "id": 261642312,
            "username": "Me",
            "color": "#595d66",
            "email": "me@example.com",
            "profilePicture": None,
        },
        "assignees": [],
        "group_assignees": [],
        "watchers": [
            {
                "id": 261642312,
                "username": "Me",
                "color": "#595d66",
                "initials": "M",
                "email": "me@example.com",
                "profilePicture": None,
            }
        ],
        "checklists": [],
        "tags": [],
        "parent": None,
        "top_level_parent": None,
        "priority": None,
        "due_date": None,
        "start_date": None,
        "points": None,
        "time_estimate": None,
        "custom_fields": [],
        "dependencies": [],
        "linked_tasks": [],
        "locations": [],
        "team_id": "90232846929",
        "url": "https://app.clickup.com/t/86adrdd2j",
        "sharing": {
            "public": False,
            "public_share_expires_on": None,
            "public_fields": [
                "assignees",
                "priority",
                "due_date",
                "content",
                "comments",
                "attachments",
                "customFields",
                "subtasks",
                "tags",
                "checklists",
                "coverimage",
            ],
            "token": None,
            "seo_optimized": False,
        },
        "permission_level": "create",
        "list": {"id": "901323335746", "name": "List", "access": True},
        "project": {
            "id": "901515652835",
            "name": "hidden",
            "hidden": True,
            "access": True,
        },
        "folder": {
            "id": "901315352835",
            "name": "hidden",
            "hidden": True,
            "access": True,
        },
        "space": {"id": "901312298283"},
    }


@pytest.fixture
def task_page(record):
    """Return a one-task API response page, the last one for page_number > 0."""

    def get(page_number):
        return {"tasks": [record], "last_page": page_number > 0}

    return get


SERVICE_CONFIG = {'service': 'clickup', 'team_id': 1234, 'token': 'arbitrary_token'}


class TestClickupClient:
    def test_init(self):
        http_client = ClickupClient('12345')
        assert (
            "https://api.clickup.com/api/v2/team/1234/task?include_closed=false&page=0"
            == http_client._get_url_for_tasks(1234, 0)
        )

    @responses.activate
    def test_get_repo(self, record, task_page):
        client = ClickupClient('XXXXXX')
        responses.get(
            "https://api.clickup.com/api/v2/team/1234/task?include_closed=false&page=0",
            json=task_page(0),
        )
        responses.get(
            "https://api.clickup.com/api/v2/team/1234/task?include_closed=false&page=1",
            json=task_page(1),
        )
        result = [item for item in client.get_tasks_for_team(team_id=1234)]
        assert result == [record, record]


class TestClickupService:
    @pytest.fixture
    def config(self):
        return {
            'general': {'targets': ['myservice']},
            'myservice': {**SERVICE_CONFIG, 'also_unassigned': 'true'},
        }

    def test_keyring_service(self, config):
        conf = validate(config).service_configs[0]
        assert conf.keyring_service == 'clickup://'

    def test_is_assigned(self, config, record):
        assert get_validated_service(config).is_assigned(record)

        config["myservice"]["only_if_assigned"] = "Pedro Manobrista"

        assert get_validated_service(config).is_assigned(record)

        config["myservice"]["also_unassigned"] = False

        assert not get_validated_service(config).is_assigned(record)

        record["assignees"] = [
            {
                "id": 2606423512,
                "username": "Pedro Manobrista",
                "color": "#595d66",
                "initials": "PM",
                "email": "pedro.manobrista@spiderman.com",
                "profilePicture": None,
            }
        ]
        assert get_validated_service(config).is_assigned(record)


class TestClickupIssue:
    @pytest.fixture
    def service(self):
        return get_mock_service(ClickupService, SERVICE_CONFIG)

    def test_to_taskwarrior(self, service, record):
        issue = service.get_issue_for_record(record)

        expected_output = {
            "project": None,
            "priority": 'M',
            "due": None,
            "entry": datetime.fromtimestamp(
                int(record["date_created"]) // 1e3, tz=timezone.utc
            ),
            issue.ID: record["id"],
            issue.DESCRIPTION: record["description"],
            issue.STATUS: record["status"]["status"],
            issue.UPDATED_AT: datetime.fromtimestamp(
                int(record["date_updated"]) // 1e3, tz=timezone.utc
            ),
            issue.CREATOR: record["creator"]["username"],
            issue.URL: record["url"],
            issue.LIST_NAME: record["list"]["name"],
            issue.PROJECT: record["project"]["id"],
            issue.FOLDER: record["folder"]["id"],
            issue.SPACE: record["space"]["id"],
            issue.NAME: record["name"],
        }
        actual_output = issue.to_taskwarrior()

        assert actual_output == expected_output

    @responses.activate
    def test_issues(self, service, record, task_page):
        responses.get(
            "https://api.clickup.com/api/v2/team/1234/task?include_closed=false&page=0",
            json=task_page(1),
        )

        issue = next(service.issues())

        expected_output = {
            "project": None,
            "priority": 'M',
            "due": None,
            "tags": [],
            "entry": datetime.fromtimestamp(
                int(record["date_created"]) // 1e3, tz=timezone.utc
            ),
            "description": "(bw)Is# - My task .. https://app.clickup.com/t/86adrdd2j",
            issue.ID: record["id"],
            issue.DESCRIPTION: record["description"],
            issue.STATUS: record["status"]["status"],
            issue.UPDATED_AT: datetime.fromtimestamp(
                int(record["date_updated"]) // 1e3, tz=timezone.utc
            ),
            issue.CREATOR: record["creator"]["username"],
            issue.URL: record["url"],
            issue.LIST_NAME: record["list"]["name"],
            issue.PROJECT: record["project"]["id"],
            issue.FOLDER: record["folder"]["id"],
            issue.SPACE: record["space"]["id"],
            issue.NAME: record["name"],
        }

        assert TaskConstructor(issue).get_taskwarrior_record() == expected_output
