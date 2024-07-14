import logging

from todoist_api_python.api import TodoistAPI
import typing_extensions

from bugwarrior import config
from bugwarrior.services import IssueService, Issue, ServiceClient

log = logging.getLogger(__name__)


class TodoistConfig(config.ServiceConfig):
    service: typing_extensions.Literal["todoist"]
    token: str
    filter: str = None


class TodoistClient(ServiceClient):
    def __init__(self, token, filter):
        self._api = TodoistAPI(token)
        self.filter = filter

    def get_projects(self):
        projects = self._api.get_projects()
        return projects

    def get_users(self, project_id):
        users = self._api.get_collaborators(project_id)
        return users

    def get_issues(self):
        tasks = self._api.get_tasks(filter=self.filter)
        return tasks


class TodoistIssue(Issue):
    ASSIGNEE = "todoistassignee"
    CONTENT = "todoistcontent"
    DESCRIPTION = "todoistdescription"
    ID = "todoistid"
    LABELS = "todoistlabels"
    PARENT_ID = "todoistparentid"
    PROJECT_ID = "todoistprojectid"
    SECTION_ID = "todoistsectionid"
    URL = "todoisturl"
    SYNC_ID = "todoistsyncid"

    PRIORITY_MAP = {
        1: "H",
        2: "M",
        3: "L",
        4: "",
    }

    UDAS = {
        ASSIGNEE: {
            "type": "string",
            "label": "Todoist Assignee",
        },
        CONTENT: {
            "type": "string",
            "label": "Todoist Content",
        },
        DESCRIPTION: {
            "type": "string",
            "label": "Todoist Description",
        },
        ID: {
            "type": "string",
            "label": "Todoist ID",
        },
        SYNC_ID: {
            "type": "string",
            "label": "Todoist Sync ID",
        },
        URL: {
            "type": "string",
            "label": "Todoist URL",
        },
    }

    UNIQUE_KEY = (ID, SYNC_ID)

    def to_taskwarrior(self):
        print(self.record)
        task = {
            "project": self.extra["project"],
            "priority": self.PRIORITY_MAP[self.record.priority],
            # "annotations": None,
            "tags": self.record.labels if self.record.labels else [],
            "due": self.record.due.date if self.record.due else None,
            "status": "completed" if self.record.is_completed else "pending",
            self.ASSIGNEE: self.extra["assignee"],
            self.CONTENT: self.record.content,
            self.DESCRIPTION: self.record.description,
            self.ID: self.record.id,
            self.SYNC_ID: self.record.sync_id,
            self.URL: self.record.url,
        }
        return task

    def get_default_description(self):
        description = self.build_default_description(
            title=self.record.content,
            url=self.record.url,
            number=self.record.id,
            cls="issue",
        )
        return description


class TodoistService(IssueService):
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
        user_index = {
            user.id: user.name
            for project in project_index.keys()
            for user in self.client.get_users(project)
        }
        for issue in self.client.get_issues():
            extra = {
                "project": project_index[issue.project_id],
                "assignee": user_index[issue.assignee_id] if issue.assignee_id else None,
            }
            yield self.get_issue_for_record(issue, extra)
