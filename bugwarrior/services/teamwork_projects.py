from collections.abc import Iterator
import logging
import typing
from typing import Any

from pydantic import Field
import requests

from bugwarrior import config
from bugwarrior.services import Client, Issue, Service
from bugwarrior.task import Task, Udas

log = logging.getLogger(__name__)


class TeamworkConfig(config.ServiceConfig):
    service: typing.Literal['teamwork_projects']
    KEYRING_SERVICE = 'teamwork_projects://{host}'
    host: config.StrippedTrailingSlashUrl
    token: str

    only_if_assigned: config.UnsupportedOption[str] = ''
    also_unassigned: config.UnsupportedOption[bool] = False


class TeamworkClient(Client):
    def __init__(self, host: str, token: str) -> None:
        self.host = host
        self.token = token

    def get(self, endpoint: str) -> dict[str, Any]:
        response = requests.get(f"{self.host}/{endpoint}", auth=(self.token, ""))
        return self.json_response(response)


class TeamworkUdas(Udas):
    """Service-specific UDAs contributed by Teamwork Projects."""

    UNIQUE_KEY = ('teamwork_url',)

    teamwork_url: str = Field(title='Teamwork Url')
    teamwork_title: str | None = Field(title='Teamwork Title')
    teamwork_description_long: str | None = Field(title='Teamwork Description Long')
    teamwork_project_id: int = Field(title='Teamwork Project ID')
    teamwork_status: str = Field(title='Teamwork Status')
    teamwork_id: int = Field(title='Teamwork Task ID')


class TeamworkTask(Task):
    udas: TeamworkUdas


class TeamworkIssue(Issue):
    PRIORITY_MAP = {"low": "L", "medium": "M", "high": "H"}

    def get_task_url(self) -> str:
        return self.extra["host"] + "/#/tasks/" + str(self.record["id"])

    def get_default_description(self) -> str:
        return self.build_default_description(
            title=self.record["content"],
            url=self.get_task_url(),
            number=self.record["id"],
        )

    def to_taskwarrior(self) -> TeamworkTask:
        modified = self.record.get('last-changed-on')
        is_open = str(self.record["status"]) in ["reopened", "new"]

        return TeamworkTask(
            project=self.record["project-name"],
            priority=self.get_priority(),
            due=self.record.get('due-date'),
            entry=self.record.get('created-on'),
            end=None if is_open else modified,
            modified=modified,
            annotations=self.extra.get('annotations', []),
            udas=TeamworkUdas(
                teamwork_url=self.get_task_url(),
                teamwork_title=self.record.get("content", ""),
                teamwork_description_long=self.record.get("description", ""),
                teamwork_project_id=self.record["project-id"],
                teamwork_status="Open" if is_open else "Closed",
                teamwork_id=self.record["id"],
            ),
        )


class TeamworkService(Service):
    API_VERSION = 2.0
    ISSUE_CLASS = TeamworkIssue
    TASK_SCHEMA = TeamworkTask
    CONFIG_SCHEMA = TeamworkConfig

    def __init__(
        self, config: TeamworkConfig, main_config: config.MainSectionConfig
    ) -> None:
        super().__init__(config, main_config)
        self.client = TeamworkClient(self.config.host, self.config.token)
        user = self.client.get("authenticate.json")
        self.user_id = user["account"]["userId"]
        self.name = user["account"]["firstname"] + " " + user["account"]["lastname"]

    def get_comments(self, issue: dict[str, Any]) -> list[str]:
        if self.main_config.annotation_comments:
            if issue.get("comments-count", 0) > 0:
                endpoint = f"tasks/{issue['id']}/comments.json"
                comments = self.client.get(endpoint)
                comment_list = []
                for comment in comments["comments"]:
                    author = "{first} {last}".format(
                        first=comment["author-firstname"],
                        last=comment["author-lastname"],
                    )
                    text = comment["body"]
                    comment_list.append((author, text))
                return self.build_annotations(comment_list, None)
        return []

    def issues(self) -> Iterator[Task]:
        response = self.client.get("tasks.json")
        for issue in response["todo-items"]:
            # Determine if issue is need by if following comments, changes or assigned
            if (
                issue["userFollowingComments"]
                or issue["userFollowingChanges"]
                or (self.user_id in issue.get("responsible-party-ids", ""))
            ):
                extra = {
                    "host": self.config.host,
                    'annotations': self.get_comments(issue),
                }
                yield self.process_record(issue, extra)
