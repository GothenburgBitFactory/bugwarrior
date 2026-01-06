from datetime import datetime, timezone

import responses

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.clickup import ClickupClient, ClickupService

from .base import AbstractServiceTest, ConfigTest, ServiceTest


class TestData:
    def __init__(self):
        self.tasks = {
            "tasks": [
                {
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
            ],
            "last_page": True,
        }

    def get_page(self, page_number: int):
        if page_number == 0:
            tasks = self.tasks.copy()
            tasks["last_page"] = False
            return tasks
        else:
            return self.tasks

    def get_task_contents(self):
        tasks = self.tasks["tasks"]
        tasks += tasks
        return tasks

    def get_task(self):
        return self.get_task_contents()[0]


class TestClickupClient(ServiceTest):
    def setUp(self):
        super().setUp()
        self.client = ClickupClient('XXXXXX')
        self.data = TestData()

    def test_init(self):
        http_client = ClickupClient('12345')
        self.assertEqual(
            "https://api.clickup.com/api/v2/team/1234/task?include_closed=false&page=0",
            http_client._get_url_for_tasks(1234, 0),
        )

    @responses.activate
    def test_get_repo(self):
        self.add_response(
            "https://api.clickup.com/api/v2/team/1234/task?include_closed=false&page=0",
            json=self.data.get_page(0),
        )
        self.add_response(
            "https://api.clickup.com/api/v2/team/1234/task?include_closed=false&page=1",
            json=self.data.get_page(1),
        )
        result = [item for item in self.client.get_tasks_for_team(team_id=1234)]
        self.assertSequenceEqual(self.data.get_task_contents(), result)


class TestClickupService(ConfigTest):
    def setUp(self):
        super().setUp()
        self.data = TestData()
        self.config = {
            'general': {'targets': ['myservice']},
            'myservice': {
                'service': 'clickup',
                'token': 'XXXXXX',
                'also_unassigned': 'true',
                'team_id': 1234,
            },
        }

    @property
    def service(self):
        conf = self.validate()
        service = ClickupService(conf['myservice'], conf['general'])
        return service

    def test_get_keyring_service(self):
        conf = self.validate()['myservice']
        self.assertEqual(ClickupService.get_keyring_service(conf), 'clickup://')

    def test_is_assigned(self):
        task = self.data.get_task()

        self.assertTrue(self.service.is_assigned(task))

        self.config["myservice"]["only_if_assigned"] = "Pedro Manobrista"

        self.assertTrue(self.service.is_assigned(task))

        self.config["myservice"]["also_unassigned"] = False

        self.assertFalse(self.service.is_assigned(task))

        task["assignees"] = [
            {
                "id": 2606423512,
                "username": "Pedro Manobrista",
                "color": "#595d66",
                "initials": "PM",
                "email": "pedro.manobrista@spiderman.com",
                "profilePicture": None,
            }
        ]
        self.assertTrue(self.service.is_assigned(task))


class TestClickupIssue(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {'service': 'clickup', 'team_id': 1234, 'token': 'arbitrary_token'}

    def setUp(self):
        super().setUp()
        self.service = self.get_mock_service(ClickupService)

        self.data = TestData()

    def test_to_taskwarrior(self):
        issue = self.service.get_issue_for_record(self.data.get_task())

        task = self.data.get_task()
        expected_output = {
            "project": None,
            "priority": 'M',
            "due": None,
            "entry": datetime.fromtimestamp(
                int(task["date_created"]) // 1e3, tz=timezone.utc
            ),
            issue.ID: task["id"],
            issue.DESCRIPTION: task["description"],
            issue.STATUS: task["status"]["status"],
            issue.UPDATED_AT: datetime.fromtimestamp(
                int(task["date_updated"]) // 1e3, tz=timezone.utc
            ),
            issue.CREATOR: task["creator"]["username"],
            issue.URL: task["url"],
            issue.LIST_NAME: task["list"]["name"],
            issue.PROJECT: task["project"]["id"],
            issue.FOLDER: task["folder"]["id"],
            issue.SPACE: task["space"]["id"],
            issue.NAME: task["name"],
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

    @responses.activate
    def test_issues(self):
        self.add_response(
            "https://api.clickup.com/api/v2/team/1234/task?include_closed=false&page=0",
            json=self.data.get_page(1),
        )

        issue = next(self.service.issues())

        task = self.data.get_task()
        expected_output = {
            "project": None,
            "priority": 'M',
            "due": None,
            "tags": [],
            "entry": datetime.fromtimestamp(
                int(task["date_created"]) // 1e3, tz=timezone.utc
            ),
            "description": "(bw)Is# - My task .. https://app.clickup.com/t/86adrdd2j",
            issue.ID: task["id"],
            issue.DESCRIPTION: task["description"],
            issue.STATUS: task["status"]["status"],
            issue.UPDATED_AT: datetime.fromtimestamp(
                int(task["date_updated"]) // 1e3, tz=timezone.utc
            ),
            issue.CREATOR: task["creator"]["username"],
            issue.URL: task["url"],
            issue.LIST_NAME: task["list"]["name"],
            issue.PROJECT: task["project"]["id"],
            issue.FOLDER: task["folder"]["id"],
            issue.SPACE: task["space"]["id"],
            issue.NAME: task["name"],
        }

        self.assertEqual(
            TaskConstructor(issue).get_taskwarrior_record(), expected_output
        )
