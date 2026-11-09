import base64
from collections.abc import Iterator
import logging
import re
import sys
from typing import Annotated, Any, Literal
from urllib.parse import quote

from pydantic import BeforeValidator, Field
import requests

from bugwarrior import config
from bugwarrior.services import Client, Issue, Service
from bugwarrior.task import Numeric, String, Task, Udas

log = logging.getLogger(__name__)

EscapedStr = Annotated[str, BeforeValidator(quote)]


class AzureDevopsConfig(config.ServiceConfig):
    service: Literal["azuredevops"]
    KEYRING_SERVICE = "azuredevops://{organization}@{host}"
    PAT: str
    project: EscapedStr
    organization: EscapedStr

    host: config.NoSchemeUrl = "dev.azure.com"
    wiql_filter: str = ""


def striphtml(data: str) -> str:
    p = re.compile(r"<.*?>")
    return p.sub("", data)


def format_item(item: str | None) -> str | None:
    """Removes HTML Elements, splits by line"""
    if item:
        item_lines = re.split(r"<br>|</.*?>|&nbsp;", item)
        text = "\n".join([striphtml(line) for line in item_lines if striphtml(line)])
        return text
    return


class AzureDevopsClient(Client):
    def __init__(self, pat: str, org: str, project: str, host: str) -> None:
        if pat[0] != ":":
            pat = f":{pat}"
        self.pat = base64.b64encode(pat.encode("ascii")).decode("ascii")
        self.organization = org
        self.project = project
        self.host = host
        self.base_url = f"https://{host}/{org}/{project}/_apis/wit"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "authorization": f"Basic {self.pat}",
                "accept": "application/json",
                "content-type": "application/json",
            }
        )
        self.params = {"api-version": "6.0-preview.2"}

    def get_work_item(self, workitemid: str | int) -> dict[str, Any]:
        queryset = self.params.copy()
        queryset.update({"$expand": "all"})
        resp = self.session.get(
            f"{self.base_url}/workitems/{workitemid}", params=queryset
        )
        return resp.json()

    def get_work_items_from_query(self, query: str) -> list[int]:
        data = str({"query": query})
        resp = self.session.post(f"{self.base_url}/wiql", data=data, params=self.params)
        if resp.status_code == 401:
            log.critical(
                "HTTP 401 - Error authenticating! Please check 'PAT' in the configuration"
            )
            sys.exit(1)
        if (
            resp.status_code == 400
            and resp.json()["typeKey"]
            == "WorkItemTrackingQueryResultSizeLimitExceededException"
        ):
            log.critical(
                "Too many azure devops results in query, please "
                "narrow the search by updating the ado.wiql_filter"
            )
            sys.exit(1)
        return [workitem["id"] for workitem in resp.json()["workItems"]]

    def get_workitem_comments(
        self, workitem: dict[str, Any]
    ) -> list[dict[str, Any]] | None:
        comment_link = workitem["_links"]["workItemComments"]["href"]
        resp = self.session.get(comment_link)
        return resp.json().get("comments", None)

    def get_parent_name(self, workitem: dict[str, Any]) -> str | None:
        parent_id = workitem.get("fields", {}).get("System.Parent")

        if parent_id:
            parent_item = self.get_work_item(parent_id)
            return parent_item.get("fields", {}).get("System.Title")
        else:
            return None


class AzureDevopsUdas(Udas):
    """Service-specific UDAs contributed by Azure Devops."""

    UDA_PREFIX = "ado"

    UNIQUE_KEY = ("url",)

    title: String = Field(title="Azure Devops Title")
    description: String = Field(title="Azure Devops Description")
    id: Numeric = Field(title="Azure Devops ID number")
    url: String = Field(title="Azure Devops URL")
    type: String = Field(title="Azure Devops Work Item Type")
    state: String = Field(title="Azure Devops Work Item State")
    activity: String = Field(title="Azure Devops Activity")
    priority: Numeric = Field(title="Azure Devops Priority")
    remainingwork: Numeric = Field(title="Azure Devops Amount of Remaining Work")
    parent: String = Field(title="Azure Devops Parent Work Item Name")
    namespace: String = Field(title="Azure Devops Namespace")


class AzureDevopsTask(Task):
    udas: AzureDevopsUdas


class AzureDevopsIssue(Issue):
    PRIORITY_MAP: dict[str, config.Priority] = {"1": "H", "2": "M", "3": "L", "4": "L"}

    def get_priority(self) -> config.Priority:
        value = self.record["fields"].get(
            "Microsoft.VSTS.Common.Priority", self.config.default_priority
        )
        return self.PRIORITY_MAP.get(value, self.config.default_priority)

    def to_taskwarrior(self) -> AzureDevopsTask:
        fields = self.record["fields"]
        return AzureDevopsTask(
            project=self.extra["project"],
            priority=self.get_priority(),
            annotations=self.extra.get("annotations", []),
            entry=fields.get("System.CreatedDate"),
            end=fields.get("Microsoft.VSTS.Common.ClosedDate"),
            udas=AzureDevopsUdas(
                title=fields["System.Title"],
                description=format_item(fields.get("System.Description")),
                id=self.record["id"],
                url=self.record["_links"]["html"]["href"],
                type=fields["System.WorkItemType"],
                state=fields["System.State"],
                activity=fields.get("System.Activity", ""),
                priority=fields.get("Microsoft.VSTS.Common.Priority"),
                remainingwork=fields.get("Microsoft.VSTS.Scheduling.RemainingWork"),
                parent=self.record.get("ParentTitle"),
                namespace=self.extra.get("namespace"),
            ),
        )

    def get_default_description(self) -> str:
        return self.build_default_description(
            title=self.record["fields"]["System.Title"],
            url=self.record["_links"]["html"]["href"],
            number=self.record["id"],
            cls=self.record["fields"]["System.WorkItemType"].lower(),
        )


class AzureDevopsService(Service):
    API_VERSION = 2.0
    ISSUE_CLASS = AzureDevopsIssue
    TASK_SCHEMA = AzureDevopsTask
    CONFIG_SCHEMA = AzureDevopsConfig

    def __init__(
        self, config: AzureDevopsConfig, main_config: config.MainSectionConfig
    ) -> None:
        super().__init__(config, main_config)
        self.client = AzureDevopsClient(
            pat=self.get_secret("PAT"),
            project=self.config.project,
            org=self.config.organization,
            host=self.config.host,
        )

    def get_query(self) -> list[int]:
        default_query = "SELECT [System.Id] FROM workitems"

        # Test for Clauses, add WHERE if any exist
        if any(
            [
                self.config.wiql_filter,
                self.config.only_if_assigned,
                self.config.also_unassigned,
            ]
        ):
            default_query += " WHERE "

        # Adding The User Added Query
        if self.config.wiql_filter:
            default_query += self.config.wiql_filter

        # Adding logic for common configuration items
        if self.config.only_if_assigned:
            if self.config.wiql_filter:
                default_query += " AND "
            if self.config.also_unassigned:
                default_query += (
                    "([System.AssignedTo] = @me OR [System.AssignedTo] == '')"
                )
            else:
                default_query += "[System.AssignedTo] = @me "

        list_of_items = self.client.get_work_items_from_query(default_query)
        return list_of_items

    def annotations(self, issue: dict[str, Any]) -> list[str]:
        # Build Annotations based on comments by commenter and comment text
        url = issue["_links"]["html"]["href"]
        annotations = []
        if self.main_config.annotation_comments:
            comments = self.client.get_workitem_comments(issue)
            if comments:
                for comment in comments:
                    try:
                        name = comment["revisedBy"]["displayName"]
                    except KeyError:
                        name = comment["modifiedBy"]["displayName"]
                    text = format_item(comment["text"]) or ""
                    annotations.append((name, text))
        return self.build_annotations(annotations, url)

    def issues(self) -> Iterator[Task]:
        issue_ids = self.get_query()
        for issue_id in issue_ids:
            issue = self.client.get_work_item(issue_id)
            parent_title = self.client.get_parent_name(issue)
            issue["ParentTitle"] = parent_title
            extra = {
                "project": issue["ParentTitle"],
                "annotations": self.annotations(issue),
                "namespace": f"{self.config.organization}\\{self.config.project}",
            }
            yield self.get_task_for_record(issue, extra)
