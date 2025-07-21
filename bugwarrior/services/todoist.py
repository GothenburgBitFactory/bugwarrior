import logging

from todoist_api_python.api import TodoistAPI
import typing_extensions

from datetime import datetime, time
from dataclasses import asdict

from bugwarrior import config
from bugwarrior.services import Service, Issue, Client

from todoist_api_python.models import Task

log = logging.getLogger(__name__)


class TodoistConfig(config.ServiceConfig):
    service: typing_extensions.Literal["todoist"]
    token: str
    filter: str = None
    import_labels_as_tags = False
    label_template = "{{label}}"
    char_open_bracket: str = "〈"
    char_close_bracket: str = "〉"
    due_date_mapping: str = "default"  # default, always_due, always_scheduleds


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
        record["labels"] = task.labels
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


class TodoistIssue(Issue):
    ASSIGNEE = "todoistassignee"
    ASSIGNER = "todoistassigner"
    CONTENT = "todoistcontent"
    DESCRIPTION = "todoistdescription"
    DUE = "todoistdue"
    DEADLINE = "todoistdeadline"
    DURATION = "todoistduration"
    ID = "todoistid"
    SECTION = "todoistsection"
    URL = "todoisturl"

    PRIORITY_MAP = {
        4: "H",
        3: "M",
        2: "L",
        1: None,
    }

    UDAS = {
        ID: {
            "type": "string",
            "label": "Todoist ID",
        },
        CONTENT: {
            "type": "string",
            "label": "Todoist Content",
        },
        DESCRIPTION: {
            "type": "string",
            "label": "Todoist Description",
        },
        DUE: {
            "type": "date",
            "label": "Todoist Due Date",
        },
        DEADLINE: {
            "type": "date",
            "label": "Todoist Deadline Date",
        },
        DURATION: {
            "type": "string",
            "label": "Todoist Duration",
        },
        SECTION: {
            "type": "string",
            "label": "Todoist Section",
        },
        ASSIGNEE: {
            "type": "string",
            "label": "Todoist Assignee",
        },
        ASSIGNER: {
            "type": "string",
            "label": "Todoist Assigner",
        },
        URL: {
            "type": "string",
            "label": "Todoist URL",
        },
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

        # map the Todoist due and deadline to the taret Issue scheduled and due based on the
        # date mapping setting
        if self.config.due_date_mapping == "default":
            due = todoist_deadline if todoist_deadline else todoist_due
            scheduled = todoist_due if todoist_deadline else None
        elif self.config.due_date_mapping == "always_due":
            due = todoist_due
            scheduled = None
        elif self.config.due_date_mapping == "always_scheduled":
            due = todoist_deadline
            scheduled = todoist_due
        else:
            logging.warning(
                f'Invalid due_date_mapping setting "{self.config.due_date_mapping}"',
                ". Using default mapping",
            )
            due = todoist_deadline if todoist_deadline else todoist_due
            scheduled = todoist_due if todoist_deadline else None

        task = {
            "project": self.extra["project"],
            "priority": self.get_priority(),
            # "annotations": None,  # TODO for future addition of comments
            "tags": (
                self.get_tags_from_labels(self.record["labels"])
                if self.record["labels"]
                else []
            ),
            "scheduled": scheduled,
            "due": due,
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
        }
        return task

    def get_default_description(self):
        description = self.build_default_description(
            title=self._unescape_content(self.record["content"]),
            url=self.record["url"],
            number=self.record["id"],
            cls="issue",
        )
        return description


class TodoistService(Service):
    ISSUE_CLASS = TodoistIssue
    CONFIG_SCHEMA = TodoistConfig

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = TodoistClient(
            token=self.config.token,
            filter=self.config.filter,
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
            }
            yield self.get_issue_for_record(issue, extra)
