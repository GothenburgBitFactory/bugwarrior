import json
import logging
import re
import typing

from pydantic import model_validator
import requests

from bugwarrior import config
from bugwarrior.services import Client, Issue, Service

log = logging.getLogger(__name__)


class LinearConfig(config.ServiceConfig):
    service: typing.Literal["linear"]
    api_token: str

    host: config.StrippedTrailingSlashUrl = "https://api.linear.app/graphql"
    statuses: config.ConfigList = []
    status_types: typing.Optional[config.ConfigList] = None
    import_labels_as_tags: bool = False
    label_template: str = "{{label|replace(' ', '_')}}"
    also_unassigned: config.UnsupportedOption[bool] = False

    @model_validator(mode='before')
    @classmethod
    def statuses_or_status_types(cls, values):
        statuses = values.get("statuses")
        status_types = values.get("status_types")
        if statuses and status_types:
            raise ValueError("statuses and status_types are incompatible")
        if not statuses and not status_types:
            values["status_types"] = ["backlog", "unstarted", "started"]
        return values


class LinearIssue(Issue):
    URL = "linearurl"
    TITLE = "lineartitle"
    DESCRIPTION = "lineardescription"
    STATUS = "linearstatus"
    IDENTIFIER = "linearidentifier"
    TEAM = "linearteam"
    CREATOR = "linearcreator"
    ASSIGNEE = "linearassignee"
    CREATED_AT = "linearcreated"
    UPDATED_AT = "linearupdated"
    CLOSED_AT = "linearclosed"

    UDAS = {
        URL: {"type": "string", "label": "Issue URL"},
        TITLE: {"type": "string", "label": "Issue Title"},
        DESCRIPTION: {"type": "string", "label": "Issue Description"},
        STATUS: {"type": "string", "label": "Issue State"},
        IDENTIFIER: {"type": "string", "label": "Linear Identifier"},
        TEAM: {"type": "string", "label": "Project ID"},
        CREATOR: {"type": "string", "label": "Issue Creator"},
        ASSIGNEE: {"type": "string", "label": "Issue Assignee"},
        CREATED_AT: {"type": "date", "label": "Issue Created"},
        UPDATED_AT: {"type": "date", "label": "Issue Updated"},
        CLOSED_AT: {"type": "date", "label": "Issue Closed"},
    }

    UNIQUE_KEY = (URL,)

    def to_taskwarrior(self):
        description = self.record.get("description")
        created = self.parse_date(self.record.get("createdAt"))
        modified = self.parse_date(self.record.get("updatedAt"))
        closed = self.parse_date(self.record.get("completedAt"))

        # Get a value, defaulting empty results to the given default. Some
        # GraphQL response values, such as for `project`, are either an object
        # or None, rather than being omitted when empty, so this allows chained
        # traversal of such values.
        def get(v, k, default=None):
            r = v.get(k, default)
            if not r:
                return default
            return r

        return {
            "project": (
                re.sub(
                    r"[^a-zA-Z0-9]",
                    "_",
                    get(get(self.record, "project", {}), "name", ""),
                ).lower()
                or None
            ),
            "priority": self.config.default_priority,
            "annotations": get(self.extra, "annotations", []),
            "tags": self.get_tags(),
            self.URL: self.record["url"],
            self.TITLE: get(self.record, "title"),
            self.DESCRIPTION: description,
            self.STATUS: get(get(self.record, "state", {}), "name"),
            self.IDENTIFIER: get(self.record, "identifier"),
            self.TEAM: get(get(self.record, "team", {}), "name"),
            self.CREATOR: get(get(self.record, "creator", {}), "email"),
            self.ASSIGNEE: get(get(self.record, "assignee", {}), "email"),
            self.CREATED_AT: created,
            self.UPDATED_AT: modified,
            self.CLOSED_AT: closed,
        }

    def get_tags(self):
        labels = [
            label["name"] for label in self.record.get("labels", {}).get("nodes", [])
        ]
        return self.get_tags_from_labels(labels)

    def get_default_description(self):
        return self.build_default_description(
            title=self.record.get("title"),
            url=self.record.get("url"),
            number=self.record.get("identifier"),
            cls="task",
        )


class LinearService(Service, Client):
    API_VERSION = 1.0
    ISSUE_CLASS = LinearIssue
    CONFIG_SCHEMA = LinearConfig

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": self.get_secret("api_token"),
                "Content-Type": "application/json",
            }
        )

        self.filter = []
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
            query Issues($filter: IssueFilter!) {
              issues(filter: $filter) {
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
                  team {
                    name
                  }
                }
              }
            }
            """

    @staticmethod
    def get_keyring_service(config):
        return f"linear://{config.host}"

    def issues(self):
        for issue in self.get_issues():
            yield self.get_issue_for_record(issue, {})

    def get_issues(self):
        """
        Make a Linear API request, using the query defined in the constructor.
        """
        data = {
            "query": self.query,
            "variables": {"filter": {"and": self.filter} if self.filter else {}},
        }
        response = self.session.post(self.config.host, data=json.dumps(data))
        res = self.json_response(response)

        if "errors" in res:
            messages = [
                error.get("message", "Unknown error") for error in res['errors']
            ]
            raise ValueError(messages.join("; "))

        return res.get("data", {}).get("issues", {}).get("nodes", [])
