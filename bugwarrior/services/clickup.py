from collections.abc import Iterator
import datetime
import logging
import typing
from typing import Generator, Optional

from pydantic import Field
import requests

from bugwarrior import config
from bugwarrior.services import Client, Issue, Service
from bugwarrior.task import IssueDatetime, Task, Udas

log = logging.getLogger(__name__)


class ClickupConfig(config.ServiceConfig):
    service: typing.Literal["clickup"]
    KEYRING_SERVICE = "clickup://"
    token: str
    team_id: int


class ClickupClient(Client):
    """Abstraction of Clickup API v2"""

    def __init__(self, token: str) -> None:
        self.token = token

    @staticmethod
    def _get_url_for_tasks(team_id: int, page: int = 0) -> str:
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


class ClickupUdas(Udas):
    """Service-specific UDAs contributed by Clickup."""

    UNIQUE_KEY = ("clickupid",)

    clickupid: str = Field(title="Clickup id")
    clickupdescription: str | None = Field(title="Clickup Description")
    clickupstatus: str = Field(title="Clickup Status Title")
    clickupupdated: IssueDatetime = Field(title="Clickup Updated")
    clickupcreator: str = Field(title="Clickup Creator")
    clickupurl: str = Field(title="Clickup URL")
    clickuplistname: str = Field(title="Clickup List name")
    clickupproject: str = Field(title="Clickup Project id")
    clickupfolder: str = Field(title="Clickup Folder id")
    clickupspace: str = Field(title="Clickup Space id")
    clickupname: str = Field(title="Clickup Title")


class ClickupTask(Task):
    udas: ClickupUdas


class ClickupIssue(Issue):
    PRIORITY_MAP = {"urgent": "H", "high": "M", "normal": "L", "low": ""}

    def to_taskwarrior(self) -> ClickupTask:
        if not self.record["project"]["hidden"]:
            project = self.record["project"]["name"]
        else:
            project = None

        return ClickupTask(
            project=project,
            priority=self.get_priority(),
            due=self.parse_timestamp(self.record["due_date"]),
            entry=self.parse_timestamp(self.record["date_created"]),
            udas=ClickupUdas(
                clickupid=self.record["id"],
                clickupdescription=self.record["description"],
                clickupstatus=self.record["status"]["status"],
                clickupupdated=self.parse_timestamp(self.record["date_updated"]),
                clickupcreator=self.record["creator"]["username"],
                clickupurl=self.record["url"],
                clickuplistname=self.record["list"]["name"],
                clickupproject=self.record["project"]["id"],
                clickupfolder=self.record["folder"]["id"],
                clickupspace=self.record["space"]["id"],
                clickupname=self.record["name"],
            ),
        )

    def get_default_description(self) -> str:
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
    API_VERSION = 2.0
    ISSUE_CLASS = ClickupIssue
    TASK_SCHEMA = ClickupTask
    CONFIG_SCHEMA = ClickupConfig

    def __init__(
        self, config: ClickupConfig, main_config: config.MainSectionConfig
    ) -> None:
        super().__init__(config, main_config)
        self.client = ClickupClient(token=self.get_secret('token'))

    def is_assigned(self, issue: dict) -> bool:
        if not self.config.only_if_assigned:
            return True

        if self.config.also_unassigned and len(issue["assignees"]) == 0:
            return True

        for assignee in issue["assignees"]:
            if assignee["username"] == self.config.only_if_assigned:
                return True

        return False

    def issues(self) -> Iterator[Task]:
        for task in self.client.get_tasks_for_team(self.config.team_id):
            if self.is_assigned(task):
                yield self.process_record(task)
