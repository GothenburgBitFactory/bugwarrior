import datetime
from unittest import mock

from dateutil.tz.tz import tzutc

from bugwarrior import config
from bugwarrior.config.load import BugwarriorConfigParser
from bugwarrior.services.azuredevops import (
    AzureDevopsService,
    striphtml,
)

from .base import AbstractServiceTest, ConfigTest, ServiceTest


TEST_ISSUE = {
    "_links": {
        "fields": {
            "href": "https://dev.azure.com/test_organization/c2957126-cdef-4f9a-bcc8-09323d1b7095/_apis/wit/fields"
        },
        "html": {
            "href": "https://dev.azure.com/test_organization/c2957126-cdef-4f9a-bcc8-09323d1b7095/_workitems/edit/1"
        },
        "self": {
            "href": "https://dev.azure.com/test_organization/c2957126-cdef-4f9a-bcc8-09323d1b7095/_apis/wit/workItems/1"
        },
        "workItemComments": {
            "href": "https://dev.azure.com/test_organization/c2957126-cdef-4f9a-bcc8-09323d1b7095/_apis/wit/workItems/1/comments"
        },
        "workItemRevisions": {
            "href": "https://dev.azure.com/test_organization/c2957126-cdef-4f9a-bcc8-09323d1b7095/_apis/wit/workItems/1/revisions"
        },
        "workItemType": {
            "href": "https://dev.azure.com/test_organization/c2957126-cdef-4f9a-bcc8-09323d1b7095/_apis/wit/workItemTypes/Impediment"
        },
        "workItemUpdates": {
            "href": "https://dev.azure.com/test_organization/c2957126-cdef-4f9a-bcc8-09323d1b7095/_apis/wit/workItems/1/updates"
        },
    },
    "fields": {
        "Microsoft.VSTS.Common.ClosedBy": {
            "_links": {
                "avatar": {
                    "href": "https://dev.azure.com/test_organization/_apis/GraphProfile/MemberAvatars/msa.MjhmZjA5NGItMDZiNy03MzgwLTk4YjQtODIwNjU4N2QzODJi"
                }
            },
            "descriptor": "msa.MjhmZjA5NGItMDZiNy03MzgwLTk4YjQtODIwNjU4N2QzODJi",
            "displayName": "testuser1",
            "id": "28ff094b-06b7-6380-98b4-8206587d382b",
            "imageUrl": "https://dev.azure.com/test_organization/_apis/GraphProfile/MemberAvatars/msa.MjhmZjA5NGItMDZiNy03MzgwLTk4YjQtODIwNjU4N2QzODJi",
            "uniqueName": "testuser1@example.com",
            "url": "https://spsprodcus3.vssps.visualstudio.com/Aa98ad20f-7b43-48c2-9693-ba2dd8786d34/_apis/Identities/28ff094b-06b7-6380-98b4-8206587d382b",
        },
        "Microsoft.VSTS.Common.ClosedDate": "2020-07-08T19:55:46.113Z",
        "Microsoft.VSTS.Common.Priority": 2,
        "Microsoft.VSTS.Common.StateChangeDate": "2020-07-08T19:55:46.113Z",
        "System.AreaPath": "test_project",
        "System.AssignedTo": {
            "_links": {
                "avatar": {
                    "href": "https://dev.azure.com/test_organization/_apis/GraphProfile/MemberAvatars/msa.MjhmZjA5NGItMDZiNy03MzgwLTk4YjQtODIwNjU4N2QzODJi"
                }
            },
            "descriptor": "msa.MjhmZjA5NGItMDZiNy03MzgwLTk4YjQtODIwNjU4N2QzODJi",
            "displayName": "testuser1",
            "id": "28ff094b-06b7-6380-98b4-8206587d382b",
            "imageUrl": "https://dev.azure.com/test_organization/_apis/GraphProfile/MemberAvatars/msa.MjhmZjA5NGItMDZiNy03MzgwLTk4YjQtODIwNjU4N2QzODJi",
            "uniqueName": "testuser1@example.com",
            "url": "https://spsprodcus3.vssps.visualstudio.com/Aa98ad20f-7b43-48c2-9693-ba2dd8786d34/_apis/Identities/28ff094b-06b7-6380-98b4-8206587d382b",
        },
        "System.ChangedBy": {
            "_links": {
                "avatar": {
                    "href": "https://dev.azure.com/test_organization/_apis/GraphProfile/MemberAvatars/msa.MjhmZjA5NGItMDZiNy03MzgwLTk4YjQtODIwNjU4N2QzODJi"
                }
            },
            "descriptor": "msa.MjhmZjA5NGItMDZiNy03MzgwLTk4YjQtODIwNjU4N2QzODJi",
            "displayName": "testuser1",
            "id": "28ff094b-06b7-6380-98b4-8206587d382b",
            "imageUrl": "https://dev.azure.com/test_organization/_apis/GraphProfile/MemberAvatars/msa.MjhmZjA5NGItMDZiNy03MzgwLTk4YjQtODIwNjU4N2QzODJi",
            "uniqueName": "testuser1@example.com",
            "url": "https://spsprodcus3.vssps.visualstudio.com/Aa98ad20f-7b43-48c2-9693-ba2dd8786d34/_apis/Identities/28ff094b-06b7-6380-98b4-8206587d382b",
        },
        "System.ChangedDate": "2020-07-08T19:55:46.113Z",
        "System.CommentCount": 1,
        "System.CreatedBy": {
            "_links": {
                "avatar": {
                    "href": "https://dev.azure.com/test_organization/_apis/GraphProfile/MemberAvatars/msa.MTU2MzZhMTEtZDA2Ny03ZWE5LTllNzItNWQ5ODhjMTYzMWM0"
                }
            },
            "descriptor": "msa.MTU2MzZhMTEtZDA2Ny03ZWE5LTllNzItNWQ5ODhjMTYzMWM0",
            "displayName": "testuser2",
            "id": "15636a11-d067-6ea9-9e72-5d988c1631c4",
            "imageUrl": "https://dev.azure.com/test_organization/_apis/GraphProfile/MemberAvatars/msa.MTU2MzZhMTEtZDA2Ny03ZWE5LTllNzItNWQ5ODhjMTYzMWM0",
            "uniqueName": "testuser2@example.com",
            "url": "https://spsprodcus3.vssps.visualstudio.com/Aa98ad20f-7b43-48c2-9693-ba2dd8786d34/_apis/Identities/15636a11-d067-6ea9-9e72-5d988c1631c4",
        },
        "System.CreatedDate": "2020-07-08T17:31:46.493Z",
        "System.Description": "<h1> This Description has some html in it </h1>",
        "System.IterationPath": "test_project\\2020.4",
        "System.Reason": "Impediment removed",
        "System.State": "Closed",
        "System.TeamProject": "test_project",
        "System.Title": "Example Title",
        "System.WorkItemType": "Impediment",
    },
    "id": 1,
    "rev": 4,
    "url": "https://dev.azure.com/test_organization/c2957126-cdef-4f9a-bcc8-09323d1b7095/_apis/wit/workItems/1",
}


class TestAzureDevopsServiceConfig(ConfigTest):
    def setUp(self):
        super().setUp()
        self.config = BugwarriorConfigParser()
        self.config.add_section("general")
        self.config.set("general", "targets", "test_ado")
        self.config.add_section("test_ado")
        self.config.set("test_ado", "service", "azuredevops")

    def test_validate_config_required_fields(self):
        self.config.set("test_ado", "ado.organization", "test_organization")
        self.config.set("test_ado", "ado.project", "test_project")
        self.config.set("test_ado", "ado.PAT", "myPAT")
        self.validate()

    def test_validate_config_no_organization(self):
        self.config.set("test_ado", "ado.project", "test_project")
        self.config.set("test_ado", "ado.PAT", "myPAT")

        self.assertValidationError(
            '[test_ado]\nado.organization  <- field required')

    def test_validate_config_no_project(self):
        self.config.set("test_ado", "ado.organization", "http://one.com/")
        self.config.set("test_ado", "ado.PAT", "myPAT")

        self.assertValidationError(
            '[test_ado]\nado.project  <- field required')

    def test_validate_config_no_PAT(self):
        self.config.set("test_ado", "ado.organization", "http://one.com/")
        self.config.set("test_ado", "ado.project", "test_project")

        self.assertValidationError(
            '[test_ado]\nado.PAT  <- field required')


class TestAzureDevopsService(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        "service": "azuredevops",
        "ado.organization": "test_organization",
        "ado.project": "test_project",
        "ado.PAT": "myPAT",
    }

    def setUp(self):
        super().setUp()
        self.service = self.get_mock_service(AzureDevopsService)
        self.service.client.get_parent_name.return_value = None
        self.service.client.get_work_items_from_query.return_value = [1]
        self.service.client.get_work_item.return_value = TEST_ISSUE

    def get_mock_service(self, *args, **kwargs):
        service = super().get_mock_service(*args, **kwargs)
        service.client = mock.MagicMock()
        return service

    def test_to_taskwarrior(self):
        record = TEST_ISSUE
        issue = self.service.get_issue_for_record(record)
        extra = {
            "project": None,
            "annotations": [],
            "namespace": "test_organization\\test_project",
        }
        issue.update_extra(extra)

        expected = {
            issue.TITLE: TEST_ISSUE["fields"]["System.Title"],
            issue.DESCRIPTION: striphtml(TEST_ISSUE["fields"]["System.Description"]),
            issue.ID: TEST_ISSUE["id"],
            issue.URL: TEST_ISSUE["_links"]["html"]["href"],
            issue.TYPE: TEST_ISSUE["fields"]["System.WorkItemType"],
            issue.STATE: TEST_ISSUE["fields"]["System.State"],
            issue.PRIORITY: TEST_ISSUE["fields"]["Microsoft.VSTS.Common.Priority"],
            "priority": "M",
            "project": None,
            "annotations": [],
            "adonamespace": "test_organization\\test_project",
            "entry": datetime.datetime(2020, 7, 8, 17, 31, 46, 493000, tzinfo=tzutc()),
            "end": datetime.datetime(2020, 7, 8, 19, 55, 46, 113000, tzinfo=tzutc()),
            "adoactivity": "",
            "adoremainingwork": None,
            "adoparent": None,
        }
        actual_output = issue.to_taskwarrior()
        self.assertEqual(actual_output, expected)

    def test_issues(self):
        expected = {
            "project": None,
            "priority": "M",
            "annotations": [],
            "entry": datetime.datetime(2020, 7, 8, 17, 31, 46, 493000, tzinfo=tzutc()),
            "end": datetime.datetime(2020, 7, 8, 19, 55, 46, 113000, tzinfo=tzutc()),
            "adotitle": "Example Title",
            "adodescription": " This Description has some html in it ",
            "adoid": 1,
            "adourl": "https://dev.azure.com/test_organization/c2957126-cdef-4f9a-bcc8-09323d1b7095/_workitems/edit/1",
            "adotype": "Impediment",
            "adostate": "Closed",
            "adoactivity": "",
            "adopriority": 2,
            "adoremainingwork": None,
            "adoparent": None,
            "adonamespace": "test_organization\\test_project",
            "description": '(bw)Impediment#1 - Example Title .. https://dev.azure.com/test_organization/c2957126-cdef-4f9a-bcc8-09323d1b7095/_workitems/edit/1',
            "tags": []
        }
        issue = next(self.service.issues())
        self.assertEqual(issue.get_taskwarrior_record(), expected)
