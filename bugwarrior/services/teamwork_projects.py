from collections.abc import Iterator
import logging
import typing
from typing import Any

import requests

from bugwarrior import config
from bugwarrior.services import Client, Issue, Service

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


class TeamworkIssue(Issue):
    URL = 'teamwork_url'
    TITLE = 'teamwork_title'
    DESCRIPTION_LONG = 'teamwork_description_long'
    PROJECT_ID = 'teamwork_project_id'
    STATUS = 'teamwork_status'
    ID = 'teamwork_id'

    UDAS = {
        URL: {'type': 'string', 'label': 'Teamwork Url'},
        TITLE: {'type': 'string', 'label': 'Teamwork Title'},
        DESCRIPTION_LONG: {'type': 'string', 'label': 'Teamwork Description Long'},
        PROJECT_ID: {'type': 'numeric', 'label': 'Teamwork Project ID'},
        STATUS: {'type': 'string', 'label': 'Teamwork Status'},
        ID: {'type': 'numeric', 'label': 'Teamwork Task ID'},
    }

    UNIQUE_KEY = (URL,)
    PRIORITY_MAP = {"low": "L", "medium": "M", "high": "H"}

    def get_task_url(self) -> str:
        return self.extra["host"] + "/#/tasks/" + str(self.record["id"])

    def get_default_description(self) -> str:
        return self.build_default_description(
            title=self.record["content"],
            url=self.get_task_url(),
            number=self.record["id"],
        )

    def to_taskwarrior(self) -> dict[str, Any]:
        task_url = self.get_task_url()
        status = self.record["status"]

        due = self.parse_date(self.record.get('due-date'))
        created = self.parse_date(self.record.get('created-on'))
        modified = self.parse_date(self.record.get('last-changed-on'))

        end = ""
        if str(status) in ["reopened", "new"]:
            status = "Open"
        else:
            end = modified
            status = "Closed"

        return {
            'project': self.record["project-name"],
            'priority': self.get_priority(),
            'due': due,
            'entry': created,
            'end': end,
            'modified': modified,
            'annotations': self.extra.get('annotations', []),
            self.URL: task_url,
            self.TITLE: self.record.get("content", ""),
            self.DESCRIPTION_LONG: self.record.get("description", ""),
            self.PROJECT_ID: int(self.record["project-id"]),
            self.STATUS: status,
            self.ID: int(self.record["id"]),
        }


class TeamworkService(Service[TeamworkIssue]):
    API_VERSION = 2.0
    ISSUE_CLASS = TeamworkIssue
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
        if self.main_config.annotation_comments and issue.get("comments-count", 0) > 0:
            endpoint = f"tasks/{issue['id']}/comments.json"
            comments = self.client.get(endpoint)
            comment_list = []
            for comment in comments["comments"]:
                author = "{first} {last}".format(
                    first=comment["author-firstname"], last=comment["author-lastname"]
                )
                text = comment["body"]
                comment_list.append((author, text))
            return self.build_annotations(comment_list, None)
        return []

    def issues(self) -> Iterator[TeamworkIssue]:
        response = self.client.get("tasks.json")
        for issue in response["todo-items"]:
            # Determine if issue is need by if following comments, changes or assigned
            if (
                issue["userFollowingComments"]
                or issue["userFollowingChanges"]
                or (self.user_id in issue.get("responsible-party-ids", ""))
            ):
                issue_obj = self.get_issue_for_record(issue)
                extra = {
                    "host": self.config.host,
                    'annotations': self.get_comments(issue),
                }
                issue_obj.extra.update(extra)
                yield issue_obj
