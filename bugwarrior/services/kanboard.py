from __future__ import absolute_import

import datetime
import logging
import re

from bugwarrior.config import die
from bugwarrior.services import Issue, IssueService
from kanboard import Kanboard

log = logging.getLogger(__name__)


class KanboardIssue(Issue):
    TASK_ID = "kanboardtaskid"
    TASK_TITLE = "kanboardtasktitle"
    TASK_DESCRIPTION = "kanboardtaskdescription"
    PROJECT_ID = "kanboardprojectid"
    PROJECT_NAME = "kanboardprojectname"
    URL = "kanboardurl"

    UDAS = {
        TASK_ID: {"type": "numeric", "label": "Kanboard Task ID"},
        TASK_TITLE: {"type": "string", "label": "Kanboard Task Title"},
        TASK_DESCRIPTION: {"type": "string", "label": "Kanboard Task Description"},
        PROJECT_ID: {"type": "numeric", "label": "Kanboard Project ID"},
        PROJECT_NAME: {"type": "string", "label": "Kanboard Project Name"},
        URL: {"type": "string", "label": "Kanboard URL"},
    }
    UNIQUE_KEY = (TASK_ID,)

    PRIORITY_MAP = {"0": None, "1": "L", "2": "M", "3": "H"}

    def to_taskwarrior(self):
        return {
            "project": self.get_project(),
            "priority": self.get_priority(),
            "annotations": self.get_annotations(),
            "tags": self.get_tags(),
            "due": self.get_due(),
            "entry": self.get_entry(),
            self.TASK_ID: self.get_task_id(),
            self.TASK_TITLE: self.get_task_title(),
            self.TASK_DESCRIPTION: self.get_task_description(),
            self.PROJECT_ID: self.get_project_id(),
            self.PROJECT_NAME: self.get_project_name(),
            self.URL: self.get_url(),
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.get_task_title(),
            url=self.get_processed_url(self.get_url()),
            number=self.get_task_id(),
        )

    def get_task_id(self):
        return int(self.record["id"])

    def get_task_title(self):
        return self.record["title"]

    def get_task_description(self):
        return self.record["description"]

    def get_project_id(self):
        return int(self.record["project_id"])

    def get_project_name(self):
        return self.record["project_name"]

    def get_project(self):
        value = self.get_project_name()
        value = re.sub(r"[^a-zA-Z0-9]", "_", value)
        return value.strip("_")

    def get_url(self):
        return self.extra["url"]

    def get_tags(self):
        return self.extra.get("tags", [])

    def get_due(self):
        timestamp = int(self.record.get("date_due", "0"))
        if timestamp:
            return datetime.datetime.fromtimestamp(timestamp)

    def get_entry(self):
        timestamp = int(self.record.get("date_creation", "0"))
        if timestamp:
            return datetime.datetime.fromtimestamp(timestamp)

    def get_annotations(self):
        return self.extra.get("annotations", [])


class KanboardService(IssueService):
    ISSUE_CLASS = KanboardIssue
    CONFIG_PREFIX = "kanboard"

    def __init__(self, *args, **kw):
        super(KanboardService, self).__init__(*args, **kw)
        username = self.config.get("username")
        password = self.get_password("password", username)
        self.url = self.config.get("base_uri").rstrip("/")
        self.client = Kanboard("/".join((self.url, "jsonrpc.php")), username, password)
        default_query = "status:open assignee:{}".format(username)
        self.query = self.config.get("query", default_query)

    def annotations(self, task, url):
        comments = []
        if int(task.get("nb_comments", "0")):
            comments = self.client.get_all_comments(**{"task_id": task["id"]})
        return self.build_annotations(
            ((c["name"], c["comment"]) for c in comments), url
        )

    def issues(self):
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

            yield self.get_issue_for_record(task, extra)

    @classmethod
    def validate_config(cls, service_config, target):
        for option in ("base_uri", "username", "password"):
            if option not in service_config:
                die("[%s] has no 'kanboard.%s'" % (target, option))

        IssueService.validate_config(service_config, target)

    @staticmethod
    def get_keyring_service(service_config):
        username = service_config.get("username")
        base_uri = service_config.get("base_uri")
        return "kanboard://%s@%s" % (username, base_uri)
