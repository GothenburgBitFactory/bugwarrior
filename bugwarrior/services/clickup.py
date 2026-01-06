import datetime
import logging
import typing
from typing import Generator, Optional

import requests

from bugwarrior import config
from bugwarrior.services import Client, Issue, Service

log = logging.getLogger(__name__)


class ClickupConfig(config.ServiceConfig):
    service: typing.Literal["clickup"]
    token: str
    team_id: int


class ClickupClient(Client):
    """Abstraction of Clickup API v2"""

    def __init__(self, token):
        self.token = token

    @staticmethod
    def _get_url_for_tasks(team_id: int, page: int = 0):
        base_url = "https://api.clickup.com/api/v2/"
        query = f"include_closed=false&page={page}"
        return f"{base_url}team/{team_id}/task?{query}"

    def get_tasks_for_team(self, team_id: int) -> Generator[dict, None, None]:
        headers = {"Authorization": self.token}

        page = 0
        while True:
            response = requests.get(
                self._get_url_for_tasks(team_id, page), headers=headers
            )
            json = self.json_response(response)
            for task in json["tasks"]:
                yield task

            if json["last_page"]:
                break

            # Next page
            page += 1


class ClickupIssue(Issue):
    ID = "clickupid"
    DESCRIPTION = "clickupdescription"
    STATUS = "clickupstatus"
    UPDATED_AT = "clickupupdated"
    CREATOR = "clickupcreator"
    URL = "clickupurl"
    LIST_NAME = "clickuplistname"
    PROJECT = "clickupproject"
    FOLDER = "clickupfolder"
    SPACE = "clickupspace"
    NAME = "clickupname"

    UDAS = {
        ID: {"type": "string", "label": "Clickup id"},
        DESCRIPTION: {"type": "string", "label": "Clickup Description"},
        STATUS: {"type": "string", "label": "Clickup Status Title"},
        UPDATED_AT: {"type": "date", "label": "Clickup Updated"},
        CREATOR: {"type": "string", "label": "Clickup Creator"},
        URL: {"type": "string", "label": "Clickup URL"},
        LIST_NAME: {"type": "string", "label": "Clickup List name"},
        PROJECT: {"type": "string", "label": "Clickup Project id"},
        FOLDER: {"type": "string", "label": "Clickup Folder id"},
        SPACE: {"type": "string", "label": "Clickup Space id"},
        NAME: {"type": "string", "label": "Clickup Title"},
    }
    UNIQUE_KEY = (ID,)

    PRIORITY_MAP = {"urgent": "H", "high": "M", "normal": "L", "low": ""}

    def to_taskwarrior(self):
        if not self.record["project"]["hidden"]:
            project = self.record["project"]["name"]
        else:
            project = None

        return {
            "project": project,
            "priority": self.get_priority(),
            "due": self.parse_timestamp(self.record["due_date"]),
            "entry": self.parse_timestamp(self.record["date_created"]),
            self.ID: self.record["id"],
            self.DESCRIPTION: self.record["description"],
            self.STATUS: self.record["status"]["status"],
            self.UPDATED_AT: self.parse_timestamp(self.record["date_updated"]),
            self.CREATOR: self.record["creator"]["username"],
            self.URL: self.record["url"],
            self.LIST_NAME: self.record["list"]["name"],
            self.PROJECT: self.record["project"]["id"],
            self.FOLDER: self.record["folder"]["id"],
            self.SPACE: self.record["space"]["id"],
            self.NAME: self.record["name"],
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.record["name"], url=self.record["url"]
        )

    @staticmethod
    def parse_timestamp(
        milliseconds_unix: Optional[str],
    ) -> Optional[datetime.datetime]:
        if milliseconds_unix is None:
            return None

        seconds_unix = float(milliseconds_unix) // 1e3
        return datetime.datetime.fromtimestamp(seconds_unix, tz=datetime.timezone.utc)


class ClickupService(Service):
    API_VERSION = 1.0
    ISSUE_CLASS = ClickupIssue
    CONFIG_SCHEMA = ClickupConfig

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.client = ClickupClient(token=self.get_secret('token'))

    @staticmethod
    def get_keyring_service(config):
        return "clickup://"

    def is_assigned(self, issue: dict) -> bool:
        if not self.config.only_if_assigned:
            return True

        if self.config.also_unassigned and len(issue["assignees"]) == 0:
            return True

        for assignee in issue["assignees"]:
            if assignee["username"] == self.config.only_if_assigned:
                return True

        return False

    def issues(self):
        for task in self.client.get_tasks_for_team(self.config.team_id):
            if self.is_assigned(task):
                yield self.get_issue_for_record(task)
