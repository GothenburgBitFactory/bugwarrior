from collections.abc import Iterator
import datetime
import logging
import re
import typing
from typing import Any
from urllib.parse import urlparse

from kanboard import Client
from pydantic import Field, computed_field

from bugwarrior import config
from bugwarrior.services import Issue, Service
from bugwarrior.task import Task, Udas

log = logging.getLogger(__name__)


class KanboardConfig(config.ServiceConfig):
    service: typing.Literal['kanboard']
    KEYRING_SERVICE = "kanboard://{username}@{url_netloc}"
    url: config.StrippedTrailingSlashUrl
    username: str
    password: str

    query: str = ''

    only_if_assigned: config.UnsupportedOption[str] = ''
    also_unassigned: config.UnsupportedOption[bool] = False

    @computed_field
    @property
    def url_netloc(self) -> str:
        return urlparse(self.url).netloc


class KanboardUdas(Udas):
    """Service-specific UDAs contributed by Kanboard."""

    UNIQUE_KEY = ("kanboardtaskid",)

    kanboardtaskid: int = Field(title="Kanboard Task ID")
    kanboardtasktitle: str = Field(title="Kanboard Task Title")
    kanboardtaskdescription: str | None = Field(title="Kanboard Task Description")
    kanboardprojectid: int = Field(title="Kanboard Project ID")
    kanboardprojectname: str = Field(title="Kanboard Project Name")
    kanboardurl: str = Field(title="Kanboard URL")


class KanboardTask(Task):
    udas: KanboardUdas


class KanboardIssue(Issue):
    PRIORITY_MAP: dict[str, config.Priority | None] = {
        "0": None,
        "1": "L",
        "2": "M",
        "3": "H",
    }

    def to_taskwarrior(self) -> KanboardTask:
        return KanboardTask(
            project=self.get_project(),
            priority=self.get_priority(),
            annotations=self.get_annotations(),
            tags=self.get_tags(),
            due=self.get_due(),
            entry=self.get_entry(),
            udas=KanboardUdas(
                kanboardtaskid=self.get_task_id(),
                kanboardtasktitle=self.get_task_title(),
                kanboardtaskdescription=self.get_task_description(),
                kanboardprojectid=self.get_project_id(),
                kanboardprojectname=self.get_project_name(),
                kanboardurl=self.get_url(),
            ),
        )

    def get_default_description(self) -> str:
        return self.build_default_description(
            title=self.get_task_title(), url=self.get_url(), number=self.get_task_id()
        )

    def get_task_id(self) -> int:
        return int(self.record["id"])

    def get_task_title(self) -> str:
        return self.record["title"]

    def get_task_description(self) -> str:
        return self.record["description"]

    def get_project_id(self) -> int:
        return int(self.record["project_id"])

    def get_project_name(self) -> str:
        return self.record["project_name"]

    def get_project(self) -> str:
        value = self.get_project_name()
        value = re.sub(r"[^a-zA-Z0-9]", "_", value)
        return value.strip("_")

    def get_url(self) -> str:
        return self.extra["url"]

    def get_tags(self) -> list[str]:
        return self.extra.get("tags", [])

    def get_due(self) -> datetime.datetime | None:
        return self._convert_timestamp_from_field("date_due")

    def get_entry(self) -> datetime.datetime | None:
        return self._convert_timestamp_from_field("date_creation")

    def get_annotations(self) -> list[str]:
        return self.extra.get("annotations", [])

    def _convert_timestamp_from_field(self, field: str) -> datetime.datetime | None:
        timestamp = int(self.record.get(field, 0))
        if timestamp:
            return datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)


class KanboardService(Service):
    API_VERSION = 2.0
    ISSUE_CLASS = KanboardIssue
    TASK_SCHEMA = KanboardTask
    CONFIG_SCHEMA = KanboardConfig

    def __init__(
        self, config: KanboardConfig, main_config: config.MainSectionConfig
    ) -> None:
        super().__init__(config, main_config)
        password = self.get_secret("password", self.config.username)
        self.client = Client(
            f"{self.config.url}/jsonrpc.php", self.config.username, password
        )
        default_query = f"status:open assignee:{self.config.username}"
        self.query = self.config.query or default_query

    def annotations(self, task: dict[str, Any], url: str) -> list[str]:
        comments = []
        if int(task.get("nb_comments", 0)):
            comments = self.client.get_all_comments(**{"task_id": task["id"]})
        return self.build_annotations(
            ((c["name"], c["comment"]) for c in comments), url
        )

    def issues(self) -> Iterator[Task]:
        # The API provides only a per-project search. Retrieve the list of
        # projects first and query each project in turn.
        projects = self.client.get_my_projects_list()
        tasks = []
        for project_id, project_name in projects.items():
            log.debug(
                "Search for tasks in project %r using query %r",
                project_name,
                self.query,
            )
            params = {"project_id": project_id, "query": self.query}
            response = self.client.search_tasks(**params)
            log.debug("Found %d task(s) in project %r", len(response), project_name)
            tasks.extend(response)

        for task in tasks:
            task_id = task["id"]
            extra = {}

            # Resolve a task's URL.
            response = self.client.get_task(task_id=task_id)
            extra["url"] = response["url"]

            # Resolve a task's tags.
            response = self.client.get_task_tags(task_id=task_id)
            extra["tags"] = [v for v in response.values()]

            # Resolve a task's comments.
            extra["annotations"] = self.annotations(task, extra["url"])

            yield self.process_record(task, extra)
