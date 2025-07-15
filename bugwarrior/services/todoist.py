import logging

from todoist_api_python.api import TodoistAPI
import typing_extensions

from datetime import datetime, time

from bugwarrior import config
from bugwarrior.services import Service, Issue, Client

log = logging.getLogger(__name__)


class TodoistConfig(config.ServiceConfig):
    service: typing_extensions.Literal["todoist"]
    token: str
    filter: str = None
    char_open_bracket: str = "〈"
    char_close_bracket: str = "〉"
    inline_links: bool = True


class TodoistClient(Client):
    def __init__(self, token, filter):
        self._api = TodoistAPI(token)
        self.filter = filter

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
        return tasks_iter


class TodoistIssue(Issue):
    ASSIGNEE = "todoistassignee"
    ASSIGNER = "todoistassigner"
    CONTENT = "todoistcontent"
    DESCRIPTION = "todoistdescription"
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

    UNIQUE_KEY = (ID, ID)

    # replace characters that cause escaping issues in teh description like [] and "
    # this is a workaround for https://github.com/ralphbean/taskw/issues/172
    def _unescape_content(self, content):
        return (
            content.replace('"', "'")  # prevent &dquote; in task details
            .replace("[", self.config.char_open_bracket)  # prevent &open; and &close;
            .replace("]", self.config.char_close_bracket)
        )

    def to_taskwarrior(self):
        default_time = time(0, 0, 0)
        # use due date "scheduled".
        # adjust timezone to use local time for "floating" dates
        if self.record.due and type(self.record.due.date) is datetime:
            if self.record.due.timezone:
                scheduled = self.record.due.date
            else:
                scheduled = self.record.due.date.replace(tzinfo=None)
        else:
            scheduled = (
                datetime.combine(self.record.due.date, default_time, tzinfo=None)
                if self.record.due
                else None
            )

        # use deadline as "due".
        # deadline if set is only a date with no time or timezone. adjust to locla time
        due = (
            datetime.combine(self.record.deadline.date, default_time, tzinfo=None)
            if self.record.deadline
            else None
        )

        task = {
            "project": self.extra["project"],
            "priority": self.PRIORITY_MAP[self.record.priority],
            # "annotations": None,
            "tags": self.record.labels if self.record.labels else [],
            "scheduled": scheduled,
            "due": due,
            "status": "completed" if self.record.is_completed else "pending",
            "entry": self.record.created_at,
            self.ID: self.record.id,
            self.CONTENT: self._unescape_content(self.record.content),
            self.DESCRIPTION: self._unescape_content(self.record.description),
            self.DURATION: self.extra["duration"],
            self.ASSIGNEE: self.extra["assignee"],
            self.ASSIGNER: self.extra["assigner"],
            self.SECTION: self.extra["section"],
            self.URL: self.record.url,
        }
        return task

    def get_default_description(self):
        description = self.build_default_description(
            title=self._unescape_content(self.record.content),
            url=self.record.url if self.config.inline_links else '',
            number=self.record.id,
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

    def get_owner(self, issue):
        # Issue assignment hasn't been implemented yet.
        raise NotImplementedError(
            "This service has not implemented support for 'only_if_assigned'."
        )

    def issues(self):
        project_index = {project.id: project.name for project in self.client.get_projects()}
        section_index = {section.id: section.name for section in self.client.get_sections()}
        user_index = {
            user.id: f"{user.name} <{user.email}>"
            for project in project_index.keys()
            for user in self.client.get_users(project)
        }
        for issue_iter in self.client.get_issues():
            for issue in issue_iter:
                extra = {
                    "project": project_index[issue.project_id],
                    "section": (
                        section_index[issue.section_id]
                        if issue.section_id in section_index.keys()
                        else None
                    ),
                    "assignee": (
                        user_index[issue.assignee_id] if issue.assignee_id else None
                    ),
                    "assigner": (
                        user_index[issue.assigner_id] if issue.assigner_id else None
                    ),
                    "duration": (
                        f"{issue.duration.amount} {issue.duration.unit}"
                        if issue.duration
                        else None
                    ),
                }
                yield self.get_issue_for_record(issue, extra)
