from dataclasses import asdict
from datetime import datetime, time
import logging
import typing

from todoist_api_python.api import TodoistAPI
from todoist_api_python.models import Task

from bugwarrior import config
from bugwarrior.services import Client, Issue, Service

log = logging.getLogger(__name__)


class TodoistConfig(config.ServiceConfig):
    service: typing.Literal["todoist"]
    token: str
    filter: str = "(view all)"
    import_labels_as_tags: bool = False
    label_template: str = "{{label}}"
    char_open_bracket: str = "〈"
    char_close_bracket: str = "〉"


class TodoistClient(Client):
    def __init__(self, token, filter):
        self._api = TodoistAPI(token)
        self.filter = filter

    @classmethod
    def task_to_dict(cls, task: Task):
        record = asdict(task)
        # add data items for additional properties
        record["is_completed"] = task.is_completed
        record["url"] = task.url
        return record

    def get_projects(self):
        all_projects = []
        projects_iter = self._api.get_projects()
        for projects in projects_iter:
            for project in projects:
                all_projects.append(project)
        return all_projects

    def get_sections(self):
        all_sections = []
        sections_iter = self._api.get_sections()
        for sections in sections_iter:
            for section in sections:
                all_sections.append(section)
        return all_sections

    def get_users(self, project_id):
        all_users = []
        users_iter = self._api.get_collaborators(project_id)
        for users in users_iter:
            for user in users:
                all_users.append(user)
        return all_users

    def get_issues(self):
        tasks_iter = self._api.filter_tasks(query=self.filter)
        for tasks in tasks_iter:
            for task in tasks:
                record = self.task_to_dict(task)
                yield record

    def get_comments(self, task_id):
        all_comments = []
        comments_iter = self._api.get_comments(task_id=task_id)
        for comments in comments_iter:
            for comment in comments:
                all_comments.append(comment)
        return all_comments


class TodoistIssue(Issue):
    ASSIGNEE = "todoistassignee"
    ASSIGNER = "todoistassigner"
    CONTENT = "todoistcontent"
    DESCRIPTION = "todoistdescription"
    DUE = "todoistdue"
    DEADLINE = "todoistdeadline"
    DURATION = "todoistduration"
    ID = "todoistid"
    PARENT_ID = "todoistparentid"
    SECTION = "todoistsection"
    URL = "todoisturl"

    PRIORITY_MAP = {4: "H", 3: "M", 2: "L", 1: None}

    UDAS = {
        ID: {"type": "string", "label": "Todoist ID"},
        CONTENT: {"type": "string", "label": "Todoist Content"},
        DESCRIPTION: {"type": "string", "label": "Todoist Description"},
        DUE: {"type": "date", "label": "Todoist Due Date"},
        DEADLINE: {"type": "date", "label": "Todoist Deadline Date"},
        DURATION: {"type": "string", "label": "Todoist Duration"},
        SECTION: {"type": "string", "label": "Todoist Section"},
        ASSIGNEE: {"type": "string", "label": "Todoist Assignee"},
        ASSIGNER: {"type": "string", "label": "Todoist Assigner"},
        URL: {"type": "string", "label": "Todoist URL"},
        PARENT_ID: {"type": "string", "label": "Todoist Parent ID"},
    }

    UNIQUE_KEY = (ID,)

    # replace characters that cause escaping issues like [] and "
    # this is a workaround for https://github.com/ralphbean/taskw/issues/172
    def _unescape_content(self, content):
        return (
            content.replace('"', "'")  # prevent &dquote; in task details
            .replace("[", self.config.char_open_bracket)  # prevent &open; and &close;
            .replace("]", self.config.char_close_bracket)
        )

    def to_taskwarrior(self):
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

        task = {
            "project": self.extra["project"],
            "priority": self.get_priority(),
            "annotations": self.extra.get("annotations", []),
            "tags": (
                self.get_tags_from_labels(self.record["labels"])
                if self.record["labels"]
                else []
            ),
            "scheduled": None,
            "due": todoist_due,
            "status": "completed" if self.record["is_completed"] else "pending",
            "entry": self.record["created_at"],
            self.ID: self.record["id"],
            self.CONTENT: self._unescape_content(self.record["content"]),
            self.DESCRIPTION: self._unescape_content(self.record["description"]),
            self.DUE: todoist_due,
            self.DEADLINE: todoist_deadline,
            self.DURATION: self.extra["duration"],
            self.ASSIGNEE: self.extra["assignee"],
            self.ASSIGNER: self.extra["assigner"],
            self.SECTION: self.extra["section"],
            self.URL: self.record["url"],
            self.PARENT_ID: self.record["parent_id"],
        }
        return task

    def get_default_description(self):
        description = self.build_default_description(
            title=self._unescape_content(self.record["content"]),
            url=self.record["url"],
            number=self.record["id"],
            cls="subtask" if self.record["parent_id"] else "task",
        )
        return description


class TodoistService(Service):
    API_VERSION = 1.0
    ISSUE_CLASS = TodoistIssue
    CONFIG_SCHEMA = TodoistConfig

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

    @staticmethod
    def get_keyring_service(config):
        return "todoist://"

    def annotations(self, user_index, issue):
        comments = (
            self.client.get_comments(issue["id"])
            if self.main_config.annotation_comments
            else []
        )
        return self.build_annotations(
            [
                (user_index.get(comment.poster_id), comment.content)
                for comment in comments
            ],
            issue["url"],
        )

    def issues(self):
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
            yield self.get_issue_for_record(issue, extra)
