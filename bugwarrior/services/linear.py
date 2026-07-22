from collections.abc import Iterator
import json
import logging
import re
import typing
from typing import Any

from pydantic import Field, model_validator
import requests

from bugwarrior import config
from bugwarrior.collect import CollectedIssue
from bugwarrior.services import (
    Client,
    Service,
    build_default_description,
    get_secret,
    get_tags_from_labels,
)
from bugwarrior.task import IssueDatetime, Task, Udas

log = logging.getLogger(__name__)


class LinearConfig(config.ServiceConfig):
    service: typing.Literal["linear"]
    KEYRING_SERVICE = "linear://{host}"
    api_token: str

    host: config.StrippedTrailingSlashUrl = "https://api.linear.app/graphql"
    statuses: config.ConfigList = []
    status_types: typing.Optional[config.ConfigList] = None
    import_labels_as_tags: bool = False
    label_template: str = "{{label|replace(' ', '_')}}"
    also_unassigned: config.UnsupportedOption[bool] = False

    @model_validator(mode='before')
    @classmethod
    def statuses_or_status_types(cls, values: Any) -> dict[str, Any]:
        statuses = values.get("statuses")
        status_types = values.get("status_types")
        if statuses and status_types:
            raise ValueError("statuses and status_types are incompatible")
        if not statuses and not status_types:
            values["status_types"] = ["backlog", "unstarted", "started"]
        return values


class LinearUdas(Udas):
    """Service-specific UDAs contributed by Linear."""

    UNIQUE_KEY = ("linearurl",)

    linearurl: str | None = Field(default=None, title="Issue URL")
    lineartitle: str | None = Field(default=None, title="Issue Title")
    lineardescription: str | None = Field(default=None, title="Issue Description")
    linearstatus: str | None = Field(default=None, title="Issue State")
    linearidentifier: str | None = Field(default=None, title="Linear Identifier")
    linearteam: str | None = Field(default=None, title="Project ID")
    linearcreator: str | None = Field(default=None, title="Issue Creator")
    linearassignee: str | None = Field(default=None, title="Issue Assignee")
    linearcreated: IssueDatetime = Field(default=None, title="Issue Created")
    linearupdated: IssueDatetime = Field(default=None, title="Issue Updated")
    linearclosed: IssueDatetime = Field(default=None, title="Issue Closed")


class LinearTask(Task):
    udas: LinearUdas


class LinearService(Service):
    API_VERSION = 2.0
    UDAS_CLASS = LinearUdas
    CONFIG_SCHEMA = LinearConfig

    # Linear exposes issue priority as an integer:
    #   0 = No priority, 1 = Urgent, 2 = High, 3 = Medium, 4 = Low.
    PRIORITY_MAP: dict[int, config.Priority] = {1: "H", 2: "H", 3: "M", 4: "L"}

    def to_taskwarrior(
        self, record: dict[str, Any], extra: dict[str, Any]
    ) -> LinearTask:
        # Get a value, defaulting empty results to the given default. Some
        # GraphQL response values, such as for `project`, are either an object
        # or None, rather than being omitted when empty, so this allows chained
        # traversal of such values.
        def get(v: Any, k: str, default: Any = None) -> Any:
            return v.get(k, default) or default

        return LinearTask(
            project=(
                re.sub(
                    r"[^a-zA-Z0-9]",
                    "_",
                    get(get(record, "project", {}), "name", ""),
                ).lower()
                or None
            ),
            priority=self.get_priority(record),
            due=record.get("dueDate"),
            entry=record.get("createdAt"),
            annotations=get(extra, "annotations", []),
            tags=self.get_tags(record),
            udas=LinearUdas(
                linearurl=record["url"],
                lineartitle=get(record, "title"),
                lineardescription=record.get("description"),
                linearstatus=get(get(record, "state", {}), "name"),
                linearidentifier=get(record, "identifier"),
                linearteam=get(get(record, "team", {}), "name"),
                linearcreator=get(get(record, "creator", {}), "email"),
                linearassignee=get(get(record, "assignee", {}), "email"),
                linearcreated=record.get("createdAt"),
                linearupdated=record.get("updatedAt"),
                linearclosed=record.get("completedAt"),
            ),
        )

    def get_tags(self, record: dict[str, Any]) -> list[str]:
        labels = [
            label["name"] for label in record.get("labels", {}).get("nodes", [])
        ]
        return get_tags_from_labels(self.config, record, labels)

    def get_default_description(self, record: dict[str, Any]) -> str:
        return build_default_description(
            self.main_config,
            title=record.get("title", ""),
            url=record.get("url", ""),
            number=record.get("identifier", ""),
            cls="task",
        )

    def __init__(
        self, config: LinearConfig, main_config: config.MainSectionConfig
    ) -> None:
        super().__init__(config, main_config)

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": get_secret(self.config, "api_token"),
                "Content-Type": "application/json",
            }
        )

        self.filter: list[dict[str, Any]] = []
        if self.config.only_if_assigned:
            self.filter.append(
                {"assignee": {"email": {"eq": self.config.only_if_assigned}}}
            )
        if self.config.statuses:
            self.filter.append({"state": {"name": {"in": list(self.config.statuses)}}})
        elif self.config.status_types:
            self.filter.append(
                {"state": {"type": {"in": list(self.config.status_types)}}}
            )

        self.query = """
            query Issues($filter: IssueFilter!, $after: String) {
              issues(filter: $filter, first: 250, after: $after) {
                nodes {
                  url
                  title
                  description
                  assignee {
                    email
                  }
                  creator {
                    email
                  }
                  completedAt
                  updatedAt
                  createdAt
                  dueDate
                  project {
                    name
                  }
                  labels {
                    nodes {
                      name
                    }
                  }
                  url
                  state {
                    name
                  }
                  identifier
                  priority
                  team {
                    name
                  }
                }
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
            }
            """

    def issues(self) -> Iterator[CollectedIssue]:
        for record in self.get_issues():
            yield self.process_record(record, {})

    def get_issues(self) -> Iterator[dict[str, Any]]:
        """
        Make Linear API requests, paginating with cursors until exhausted.

        Linear's GraphQL API uses Relay-style cursor pagination on the
        ``issues`` connection. Without an explicit ``first`` argument, the
        server returns its default page size (50) and we silently lose any
        remaining issues. We request the maximum page size (250) and follow
        ``pageInfo.endCursor`` until ``hasNextPage`` is false.
        """
        cursor = None
        filter_arg = {"and": self.filter} if self.filter else {}
        while True:
            data = {
                "query": self.query,
                "variables": {"filter": filter_arg, "after": cursor},
            }
            response = self.session.post(self.config.host, data=json.dumps(data))
            res = Client.json_response(response)

            if "errors" in res:
                messages = [
                    error.get("message", "Unknown error") for error in res['errors']
                ]
                raise ValueError("; ".join(messages))

            issues = res.get("data", {}).get("issues", {})
            for node in issues.get("nodes", []):
                yield node

            page_info = issues.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                return
            cursor = page_info.get("endCursor")
