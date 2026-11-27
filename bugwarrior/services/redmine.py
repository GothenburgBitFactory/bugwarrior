from collections.abc import Iterator
import datetime
import logging
import re
import typing
from typing import Any

from pydantic import Field, field_validator
import requests

from bugwarrior import config
from bugwarrior.services import Client, Issue, Service
from bugwarrior.task import Date, Duration, Numeric, String, Task, Udas

log = logging.getLogger(__name__)


class RedMineConfig(config.ServiceConfig):
    _DEPRECATE_PROJECT_NAME = True
    project_name: str = ""

    service: typing.Literal["redmine"]
    KEYRING_SERVICE = "redmine://{login}@{url}/"
    url: config.StrippedTrailingSlashUrl
    key: str

    issue_limit: int = 100
    query: str = ""
    login: str = ""
    password: str = ""
    verify_ssl: bool = True

    also_unassigned: config.UnsupportedOption[bool] = False


class RedMineClient(Client):
    def __init__(
        self,
        url: str,
        key: str,
        auth: tuple[str, str] | None,
        issue_limit: int | None,
        verify_ssl: bool,
    ) -> None:
        self.url = url
        self.key = key
        self.auth = auth
        self.issue_limit = issue_limit
        self.verify_ssl = verify_ssl

    def find_issues(
        self, issue_limit: int | None, query: str, only_if_assigned: bool | str = False
    ) -> list[dict[str, Any]]:
        args = {}
        url = "/issues.json?" + query

        # TODO: if issue_limit is greater than 100, implement pagination
        # to return all issues. Leave the implementation of this to
        # the unlucky soul with >100 issues assigned to them.
        if issue_limit is not None:
            args["limit"] = issue_limit

        if only_if_assigned:
            args["assigned_to_id"] = "me"

        return self.call_api(url, args)["issues"]

    def call_api(self, uri: str, params: dict[str, Any]) -> dict[str, Any]:
        url = self.url.rstrip("/") + uri
        kwargs: dict[str, Any] = {
            "headers": {"X-Redmine-API-Key": self.key},
            "params": params,
            "verify": self.verify_ssl,
        }

        if self.auth:
            kwargs["auth"] = self.auth

        return self.json_response(requests.get(url, **kwargs))


class RedMineUdas(Udas):
    """Service-specific UDAs contributed by Redmine."""

    PREFIX = "redmine"
    UNIQUE_KEY = ("id",)

    url: String = Field(title="Redmine URL")
    subject: String = Field(title="Redmine Subject")
    id: Numeric = Field(title="Redmine ID")
    description: String = Field(title="Redmine Description")
    tracker: String = Field(title="Redmine Tracker")
    status: String = Field(title="Redmine Status")
    author: String = Field(title="Redmine Author")
    category: String = Field(title="Redmine Category")
    startdate: Date = Field(title="Redmine Start Date")
    spenthours: Duration = Field(title="Redmine Spent Hours")
    estimatedhours: Duration = Field(title="Redmine Estimated Hours")
    createdon: Date = Field(title="Redmine Created On")
    updatedon: Date = Field(title="Redmine Updated On")
    duedate: Date = Field(title="Redmine Due Date")
    assignedto: String = Field(title="Redmine Assigned To")
    projectname: String = Field(title="Redmine Project")

    @field_validator("spenthours", "estimatedhours", mode="before")
    @classmethod
    def hours_to_duration(cls, value: Any) -> Any:
        """Read Redmine's count of hours as a duration."""
        if value is None:
            return None
        return datetime.timedelta(hours=float(value))


class RedMineTask(Task):
    udas: RedMineUdas


class RedMineIssue(Issue):
    PRIORITY_MAP: dict[str, config.Priority] = {
        "Low": "L",
        "Normal": "M",
        "High": "H",
        "Urgent": "H",
        "Immediate": "H",
    }

    def to_taskwarrior(self) -> RedMineTask:
        return RedMineTask(
            project=self.get_project_name(),
            annotations=self.extra.get("annotations", []),
            priority=self.get_priority(),
            udas=RedMineUdas(
                url=self.get_issue_url(),
                subject=self.record["subject"],
                id=self.record["id"],
                description=self.record.get("description", ""),
                tracker=self.record["tracker"]["name"],
                status=self.record["status"]["name"],
                author=self.record["author"]["name"],
                projectname=self.record["project"]["name"],
                assignedto=(self.record.get("assigned_to") or {}).get("name"),
                category=(self.record.get("category") or {}).get("name"),
                startdate=self.record.get("start_date"),
                createdon=self.record.get("created_on"),
                updatedon=self.record.get("updated_on"),
                duedate=self.record.get("due_date"),
                estimatedhours=self.record.get("estimated_hours"),
                spenthours=self.record.get("spent_hours"),
            ),
        )

    def get_priority(self) -> config.Priority:
        return self.PRIORITY_MAP.get(
            self.record.get("priority", {}).get("name"), self.config.default_priority
        )

    def get_issue_url(self) -> str:
        return self.config.url + "/issues/" + str(self.record["id"])

    def get_project_name(self) -> str:
        if self.config.project_name:
            return self.config.project_name
        # TODO: It would be nice to use the project slug (if the Redmine
        # instance supports it), but this would require (1) an API call
        # to get the list of projects, and then a look up between the
        # project ID contained in self.record and the list of projects.
        return re.sub(r"[^a-zA-Z0-9]", "", self.record["project"]["name"]).lower()

    def get_default_description(self) -> str:
        return self.build_default_description(
            title=self.record["subject"],
            url=self.get_issue_url(),
            number=self.record["id"],
            cls="issue",
        )


class RedMineService(Service):
    API_VERSION = 2.0
    ISSUE_CLASS = RedMineIssue
    TASK_SCHEMA = RedMineTask
    CONFIG_SCHEMA = RedMineConfig

    def __init__(
        self, config: RedMineConfig, main_config: config.MainSectionConfig
    ) -> None:
        super().__init__(config, main_config)

        self.key = self.get_secret("key")

        password = (
            self.get_secret("password", self.config.login)
            if self.config.login
            else None
        )
        auth = (
            (self.config.login, password) if (self.config.login and password) else None
        )
        self.client = RedMineClient(
            self.config.url,
            self.key,
            auth,
            self.config.issue_limit,
            self.config.verify_ssl,
        )

    def issues(self) -> Iterator[Task]:
        issues = self.client.find_issues(
            self.config.issue_limit, self.config.query, self.config.only_if_assigned
        )
        log.debug(" Found %i total.", len(issues))
        for issue in issues:
            yield self.get_task_for_record(issue)
