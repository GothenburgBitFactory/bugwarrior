from builtins import filter
import re
import six
from urllib.parse import urlparse

import requests
from six.moves.urllib.parse import quote_plus
from jinja2 import Template

from bugwarrior.config import asbool, aslist, die
from bugwarrior.services import IssueService, Issue, ServiceClient

import logging
log = logging.getLogger(__name__)

class TeamworkClient(ServiceClient):

    def __init__(self, host, token):
        self.host = host
        self.token = token

    def authenticate(self):
        response = requests.get(self.host + "/authenticate.json", auth=(self.token, ""))
        return self.json_response(response)

    def call_api(self, method, endpoint, data=None):
        response = requests.get(self.host + endpoint, auth=(self.token, ""), params=data)
        return self.json_response(response)

class TeamworkIssue(Issue):
    URL = 'teamwork_url'
    TITLE = 'teamwork_title'
    DESCRIPTION_LONG = 'teamwork_description_long'
    PROJECT_ID = 'teamwork_project_id'
    STATUS = 'teamwork_status'
    ID = 'teamwork_id'

    UDAS = {
        URL: {
            'type': 'string',
            'label': 'Teamwork Url',
        },
        TITLE: {
            'type': 'string',
            'label': 'Teamwork Title',
        },
        DESCRIPTION_LONG: {
            'type': 'string',
            'label': 'Teamwork Description Long',
        },
        PROJECT_ID: {
            'type': 'numeric',
            'label': 'Teamwork Project ID',
        },
        STATUS: {
            'type': 'string',
            'label': 'Teamwork Status',
        },
        ID: {
            'type': 'numeric',
            'label': 'Teamwork Task ID',
        },
    }

    UNIQUE_KEY = (URL, )
    PRIORITY_MAP = {
        "low": "L",
        "medium": "M",
        "high": "H"
    }

    def get_owner(self, issue):
        if issue:
            if self.record.get("responsible-party-ids", ""):
                if self.user_id in self.record.get("responsible-party-ids", ""):
                    return self.name

    def get_author(self, issue):
        if issue:
            author = self.record["creator-firstname"] + " " + self.record["creator-lastname"]
            return author

    def get_task_url(self):
        return self.extra["host"] + "/#/tasks/" + str(self.record["id"])

    def get_default_description(self):
        return self.build_default_description(
            title=self.record["content"],
            url=self.get_task_url(),
            number=self.record["id"],
        )

    def to_taskwarrior(self):
        task_url = self.get_task_url()
        description = self.record.get("content", "")
        parent_id = self.record["parentTaskId"]
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

class TeamworkService(IssueService):
    ISSUE_CLASS = TeamworkIssue
    CONFIG_PREFIX = 'teamwork_projects'

    def __init__(self, *args, **kwargs):
        super(TeamworkService, self).__init__(*args, **kwargs)
        self.host = self.config.get('host', '')
        self.token = self.config.get('token', '')
        self.client = TeamworkClient(self.host, self.token)
        user = self.client.authenticate()
        self.user_id = user["account"]["userId"]
        self.name = user["account"]["firstname"] + " " + user["account"]["lastname"]

    def get_comments(self, issue):
        if self.annotation_comments:
            if issue.get("comments-count", 0) > 0:
                endpoint = "/tasks/{task_id}/comments.json".format(task_id=issue["id"])
                comments = self.client.call_api("GET", endpoint)
                comment_list = []
                for comment in comments["comments"]:
                    url = self.host + "/#/tasks/" + str(issue["id"])
                    author = "{first} {last}".format(
                        first=comment["author-firstname"],
                        last=comment["author-lastname"],
                    )
                    text = comment["body"]
                    comment_list.append((author, text))
                return self.build_annotations(comment_list, None)
        return [] 


    def issues(self):
        response = self.client.call_api("GET", "/tasks.json")#, data= { "responsible-party-ids": self.user_id })
        for issue in response["todo-items"]:
            # Determine if issue is need by if following comments, changes or assigned
            if issue["userFollowingComments"] or issue["userFollowingChanges"]\
                    or (self.user_id in issue.get("responsible-party-ids", "")):
                issue_obj = self.get_issue_for_record(issue)
                extra = {
                    "host": self.host,
                    'annotations': self.get_comments(issue),
                }
                issue_obj.update_extra(extra)
                yield issue_obj
