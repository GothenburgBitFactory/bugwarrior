from collections.abc import Iterator
from dataclasses import asdict
from datetime import datetime, time
import logging
import typing
from typing import Any

from pydantic import Field
from todoist_api_python.api import TodoistAPI
from todoist_api_python.models import Task as ApiTask

from bugwarrior import config
from bugwarrior.services import Client, Issue, Service
from bugwarrior.task import IssueDatetime, Task, Udas

log = logging.getLogger(__name__)


class TodoistConfig(config.ServiceConfig):
    service: typing.Literal["todoist"]
    KEYRING_SERVICE = "todoist://"
    token: str
    filter: str = "(view all)"
    import_labels_as_tags: bool = False
    label_template: str = "{{label}}"
    char_open_bracket: str = "〈"
    char_close_bracket: str = "〉"


class TodoistClient(Client):
    def __init__(self, token: str, filter: str) -> None:
        self._api = TodoistAPI(token)
        self.filter = filter

    @classmethod
    def task_to_dict(cls, task: ApiTask) -> dict[str, Any]:
        record = asdict(task)
        # add data items for additional properties
        record["is_completed"] = task.is_completed
        record["url"] = task.url
        return record

    def get_projects(self) -> list[Any]:
        all_projects = []
        projects_iter = self._api.get_projects()
        for projects in projects_iter:
            for project in projects:
                all_projects.append(project)
        return all_projects

    def get_sections(self) -> list[Any]:
        all_sections = []
        sections_iter = self._api.get_sections()
        for sections in sections_iter:
            for section in sections:
                all_sections.append(section)
        return all_sections

    def get_users(self, project_id: Any) -> list[Any]:
        all_users = []
        users_iter = self._api.get_collaborators(project_id)
        for users in users_iter:
            for user in users:
                all_users.append(user)
        return all_users

    def get_issues(self) -> Iterator[dict[str, Any]]:
        tasks_iter = self._api.filter_tasks(query=self.filter)
        for tasks in tasks_iter:
            for task in tasks:
                record = self.task_to_dict(task)
                yield record

    def get_comments(self, task_id: str) -> list[Any]:
        all_comments = []
        comments_iter = self._api.get_comments(task_id=task_id)
        for comments in comments_iter:
            for comment in comments:
                all_comments.append(comment)
        return all_comments


class TodoistUdas(Udas):
    """Service-specific UDAs contributed by Todoist."""

    UNIQUE_KEY = ("todoistid",)

    todoistid: str = Field(title="Todoist ID")
    todoistcontent: str = Field(title="Todoist Content")
    todoistdescription: str = Field(title="Todoist Description")
    todoistdue: IssueDatetime = Field(title="Todoist Due Date")
    todoistdeadline: IssueDatetime = Field(title="Todoist Deadline Date")
    todoistduration: str | None = Field(title="Todoist Duration")
    todoistsection: str | None = Field(title="Todoist Section")
    todoistassignee: str | None = Field(title="Todoist Assignee")
    todoistassigner: str | None = Field(title="Todoist Assigner")
    todoisturl: str = Field(title="Todoist URL")
    todoistparentid: str | None = Field(title="Todoist Parent ID")


class TodoistTask(Task):
    udas: TodoistUdas


class TodoistIssue(Issue):
    PRIORITY_MAP: dict[int, config.Priority | None] = {4: "H", 3: "M", 2: "L", 1: None}

    # replace characters that cause escaping issues like [] and "
    # this is a workaround for https://github.com/ralphbean/taskw/issues/172
    def _unescape_content(self, content: str) -> str:
        return (
            content.replace('"', "'")  # prevent &dquote; in task details
            .replace("[", self.config.char_open_bracket)  # prevent &open; and &close;
            .replace("]", self.config.char_close_bracket)
        )

    def to_taskwarrior(self) -> TodoistTask:
        default_time = time(0, 0, 0)
        # adjust timezone to use local time for "floating" dates
        if self.record["due"]:
            # The Todoist due date could be a `date` or `datetime`
            if isinstance(self.record["due"]["date"], datetime):
                if self.record["due"]["timezone"]:
                    todoist_due = self.record["due"]["date"]
                else:
                    # if no timezone set is set remove tzinfo
                    # otherwixe it will be treated as UTC by default
                    todoist_due = self.record["due"]["date"].replace(tzinfo=None)
            else:
                # the due is just a `date` with no time or timezone.
                todoist_due = datetime.combine(
                    self.record["due"]["date"], default_time, tzinfo=None
                )
        else:
            todoist_due = None

        # deadline if set is only a date with no time or timezone.
        todoist_deadline = (
            datetime.combine(self.record["deadline"]["date"], default_time, tzinfo=None)
            if self.record["deadline"]
            else None
        )

        return TodoistTask(
            project=self.extra["project"],
            priority=self.get_priority(),
            annotations=self.extra.get("annotations", []),
            tags=(
                self.get_tags_from_labels(self.record["labels"])
                if self.record["labels"]
                else []
            ),
            scheduled=None,
            due=todoist_due,
            status="completed" if self.record["is_completed"] else "pending",
            entry=self.record["created_at"],
            udas=TodoistUdas(
                todoistid=self.record["id"],
                todoistcontent=self._unescape_content(self.record["content"]),
                todoistdescription=self._unescape_content(self.record["description"]),
                todoistdue=todoist_due,
                todoistdeadline=todoist_deadline,
                todoistduration=self.extra["duration"],
                todoistassignee=self.extra["assignee"],
                todoistassigner=self.extra["assigner"],
                todoistsection=self.extra["section"],
                todoisturl=self.record["url"],
                todoistparentid=self.record["parent_id"],
            ),
        )

    def get_default_description(self) -> str:
        description = self.build_default_description(
            title=self._unescape_content(self.record["content"]),
            url=self.record["url"],
            number=self.record["id"],
            cls="subtask" if self.record["parent_id"] else "task",
        )
        return description


class TodoistService(Service):
    API_VERSION = 2.0
    ISSUE_CLASS = TodoistIssue
    TASK_SCHEMA = TodoistTask
    CONFIG_SCHEMA = TodoistConfig

    def __init__(
        self, config: TodoistConfig, main_config: config.MainSectionConfig
    ) -> None:
        super().__init__(config, main_config)
        self.token = self.get_secret("token")

        # apply additional filters
        filter = self.config.filter
        if self.config.only_if_assigned:
            # fetch personal tasks (!shared)
            personal = "!shared"
            # fetch assigned tasks in shared projects (shared & assigned)
            shared_assigned = f"| shared & assigned to: {self.config.only_if_assigned}"
            # fetch unassigned tasks in shared projects (shared & !assigned)
            unassigned = "| shared & !assigned" if self.config.also_unassigned else ""
            filter += f" & ({personal} {shared_assigned} {unassigned})"

        log.info(f"Using Todoist filter: {filter}")

        self.client = TodoistClient(token=self.token, filter=filter)

    def annotations(
        self, user_index: dict[Any, str], issue: dict[str, Any]
    ) -> list[str]:
        comments = (
            self.client.get_comments(issue["id"])
            if self.main_config.annotation_comments
            else []
        )
        return self.build_annotations(
            [
                (user_index.get(comment.poster_id) or "", comment.content)
                for comment in comments
            ],
            issue["url"],
        )

    def issues(self) -> Iterator[Task]:
        project_index = {
            project.id: project.name for project in self.client.get_projects()
        }
        section_index = {
            section.id: section.name for section in self.client.get_sections()
        }
        user_index = {
            user.id: f"{user.name} <{user.email}>"
            for project in project_index.keys()
            for user in self.client.get_users(project)
        }

        for issue in self.client.get_issues():
            extra = {
                "project": project_index.get(issue["project_id"]),
                "section": section_index.get(issue["section_id"]),
                "assignee": user_index.get(issue["assignee_id"]),
                "assigner": user_index.get(issue["assigner_id"]),
                "duration": (
                    f'{issue["duration"]["amount"]} {issue["duration"]["unit"]}'
                    if issue["duration"]
                    else None
                ),
                "annotations": self.annotations(user_index, issue),
            }
            yield self.process_record(issue, extra)
