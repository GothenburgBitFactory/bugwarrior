from datetime import datetime, timezone
from unittest import mock

import pytest

from bugwarrior.services.azuredevops import AzureDevopsService, striphtml

from ..base import validate
from .base import get_mock_service

SERVICE_CONFIG = {
    "service": "azuredevops",
    "organization": "test_organization",
    "project": "test_project",
    "PAT": "myPAT",
}


@pytest.fixture
def record():
    return {
        "_links": {
            "fields": {
                "href": "https://dev.azure.com/test_organization/c2957126-cdef-4f9a-bcc8-09323d1b7095/_apis/wit/fields"  # noqa: E501
            },
            "html": {
                "href": "https://dev.azure.com/test_organization/c2957126-cdef-4f9a-bcc8-09323d1b7095/_workitems/edit/1"  # noqa: E501
            },
            "self": {
                "href": "https://dev.azure.com/test_organization/c2957126-cdef-4f9a-bcc8-09323d1b7095/_apis/wit/workItems/1"  # noqa: E501
            },
            "workItemComments": {
                "href": "https://dev.azure.com/test_organization/c2957126-cdef-4f9a-bcc8-09323d1b7095/_apis/wit/workItems/1/comments"  # noqa: E501
            },
            "workItemRevisions": {
                "href": "https://dev.azure.com/test_organization/c2957126-cdef-4f9a-bcc8-09323d1b7095/_apis/wit/workItems/1/revisions"  # noqa: E501
            },
            "workItemType": {
                "href": "https://dev.azure.com/test_organization/c2957126-cdef-4f9a-bcc8-09323d1b7095/_apis/wit/workItemTypes/Impediment"  # noqa: E501
            },
            "workItemUpdates": {
                "href": "https://dev.azure.com/test_organization/c2957126-cdef-4f9a-bcc8-09323d1b7095/_apis/wit/workItems/1/updates"  # noqa: E501
            },
        },
        "fields": {
            "Microsoft.VSTS.Common.ClosedBy": {
                "_links": {
                    "avatar": {
                        "href": "https://dev.azure.com/test_organization/_apis/GraphProfile/MemberAvatars/msa.MjhmZjA5NGItMDZiNy03MzgwLTk4YjQtODIwNjU4N2QzODJi"  # noqa: E501
                    }
                },
                "descriptor": "msa.MjhmZjA5NGItMDZiNy03MzgwLTk4YjQtODIwNjU4N2QzODJi",
                "displayName": "testuser1",
                "id": "28ff094b-06b7-6380-98b4-8206587d382b",
                "imageUrl": "https://dev.azure.com/test_organization/_apis/GraphProfile/MemberAvatars/msa.MjhmZjA5NGItMDZiNy03MzgwLTk4YjQtODIwNjU4N2QzODJi",  # noqa: E501
                "uniqueName": "testuser1@example.com",
                "url": "https://spsprodcus3.vssps.visualstudio.com/Aa98ad20f-7b43-48c2-9693-ba2dd8786d34/_apis/Identities/28ff094b-06b7-6380-98b4-8206587d382b",  # noqa: E501
            },
            "Microsoft.VSTS.Common.ClosedDate": "2020-07-08T19:55:46.113Z",
            "Microsoft.VSTS.Common.Priority": 2,
            "Microsoft.VSTS.Common.StateChangeDate": "2020-07-08T19:55:46.113Z",
            "System.AreaPath": "test_project",
            "System.AssignedTo": {
                "_links": {
                    "avatar": {
                        "href": "https://dev.azure.com/test_organization/_apis/GraphProfile/MemberAvatars/msa.MjhmZjA5NGItMDZiNy03MzgwLTk4YjQtODIwNjU4N2QzODJi"  # noqa: E501
                    }
                },
                "descriptor": "msa.MjhmZjA5NGItMDZiNy03MzgwLTk4YjQtODIwNjU4N2QzODJi",
                "displayName": "testuser1",
                "id": "28ff094b-06b7-6380-98b4-8206587d382b",
                "imageUrl": "https://dev.azure.com/test_organization/_apis/GraphProfile/MemberAvatars/msa.MjhmZjA5NGItMDZiNy03MzgwLTk4YjQtODIwNjU4N2QzODJi",  # noqa: E501
                "uniqueName": "testuser1@example.com",
                "url": "https://spsprodcus3.vssps.visualstudio.com/Aa98ad20f-7b43-48c2-9693-ba2dd8786d34/_apis/Identities/28ff094b-06b7-6380-98b4-8206587d382b",  # noqa: E501
            },
            "System.ChangedBy": {
                "_links": {
                    "avatar": {
                        "href": "https://dev.azure.com/test_organization/_apis/GraphProfile/MemberAvatars/msa.MjhmZjA5NGItMDZiNy03MzgwLTk4YjQtODIwNjU4N2QzODJi"  # noqa: E501
                    }
                },
                "descriptor": "msa.MjhmZjA5NGItMDZiNy03MzgwLTk4YjQtODIwNjU4N2QzODJi",
                "displayName": "testuser1",
                "id": "28ff094b-06b7-6380-98b4-8206587d382b",
                "imageUrl": "https://dev.azure.com/test_organization/_apis/GraphProfile/MemberAvatars/msa.MjhmZjA5NGItMDZiNy03MzgwLTk4YjQtODIwNjU4N2QzODJi",  # noqa: E501
                "uniqueName": "testuser1@example.com",
                "url": "https://spsprodcus3.vssps.visualstudio.com/Aa98ad20f-7b43-48c2-9693-ba2dd8786d34/_apis/Identities/28ff094b-06b7-6380-98b4-8206587d382b",  # noqa: E501
            },
            "System.ChangedDate": "2020-07-08T19:55:46.113Z",
            "System.CommentCount": 1,
            "System.CreatedBy": {
                "_links": {
                    "avatar": {
                        "href": "https://dev.azure.com/test_organization/_apis/GraphProfile/MemberAvatars/msa.MTU2MzZhMTEtZDA2Ny03ZWE5LTllNzItNWQ5ODhjMTYzMWM0"  # noqa: E501
                    }
                },
                "descriptor": "msa.MTU2MzZhMTEtZDA2Ny03ZWE5LTllNzItNWQ5ODhjMTYzMWM0",
                "displayName": "testuser2",
                "id": "15636a11-d067-6ea9-9e72-5d988c1631c4",
                "imageUrl": "https://dev.azure.com/test_organization/_apis/GraphProfile/MemberAvatars/msa.MTU2MzZhMTEtZDA2Ny03ZWE5LTllNzItNWQ5ODhjMTYzMWM0",  # noqa: E501
                "uniqueName": "testuser2@example.com",
                "url": "https://spsprodcus3.vssps.visualstudio.com/Aa98ad20f-7b43-48c2-9693-ba2dd8786d34/_apis/Identities/15636a11-d067-6ea9-9e72-5d988c1631c4",  # noqa: E501
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
        "url": "https://dev.azure.com/test_organization/c2957126-cdef-4f9a-bcc8-09323d1b7095/_apis/wit/workItems/1",  # noqa: E501
    }


class TestAzureDevopsConfig:
    @pytest.fixture
    def config(self):
        return {
            "general": {"targets": ["myservice"]},
            "myservice": {"service": "azuredevops"},
        }

    def test_validate_config_required_fields(self, config):
        config["myservice"].update(
            {
                "organization": "test_organization",
                "project": "test_project",
                "PAT": "myPAT",
            }
        )
        validate(config)

    def test_validate_config_no_organization(self, config, assert_validation_error):
        config["myservice"].update({"project": "test_project", "PAT": "myPAT"})

        assert_validation_error(config, '[myservice]\norganization  <- Field required')

    def test_validate_config_no_project(self, config, assert_validation_error):
        config["myservice"].update({"organization": "http://one.com/", "PAT": "myPAT"})

        assert_validation_error(config, '[myservice]\nproject  <- Field required')

    def test_validate_config_no_PAT(self, config, assert_validation_error):
        config["myservice"].update(
            {"organization": "http://one.com/", "project": "test_project"}
        )

        assert_validation_error(config, '[myservice]\nPAT  <- Field required')


class TestAzureDevopsService:
    @pytest.fixture
    def make_service(self, record):
        def make(**overrides):
            service = get_mock_service(
                AzureDevopsService, {**SERVICE_CONFIG, **overrides}
            )
            service.client = mock.MagicMock()
            service.client.get_parent_name.return_value = None
            service.client.get_work_items_from_query.return_value = [1]
            service.client.get_work_item.return_value = record
            return service

        return make

    @pytest.fixture
    def service(self, make_service):
        return make_service()

    def test_to_taskwarrior(self, service, record):
        issue = service.get_issue_for_record(record)
        extra = {
            "project": None,
            "annotations": [],
            "namespace": "test_organization\\test_project",
        }
        issue.extra.update(extra)

        expected = {
            "adotitle": record["fields"]["System.Title"],
            "adodescription": striphtml(record["fields"]["System.Description"]),
            "adoid": record["id"],
            "adourl": record["_links"]["html"]["href"],
            "adotype": record["fields"]["System.WorkItemType"],
            "adostate": record["fields"]["System.State"],
            "adopriority": record["fields"]["Microsoft.VSTS.Common.Priority"],
            "priority": "M",
            "project": None,
            "annotations": [],
            "adonamespace": "test_organization\\test_project",
            "entry": datetime(2020, 7, 8, 17, 31, 46, 0, tzinfo=timezone.utc),
            "end": datetime(2020, 7, 8, 19, 55, 46, 0, tzinfo=timezone.utc),
            "adoactivity": "",
            "adoremainingwork": None,
            "adoparent": None,
        }
        actual_output = issue.to_taskwarrior().to_taskwarrior_data()
        assert actual_output == expected

    def test_issues(self, service):
        expected = {
            "project": None,
            "priority": "M",
            "annotations": [],
            "entry": datetime(2020, 7, 8, 17, 31, 46, 0, tzinfo=timezone.utc),
            "end": datetime(2020, 7, 8, 19, 55, 46, 0, tzinfo=timezone.utc),
            "adotitle": "Example Title",
            "adodescription": " This Description has some html in it ",
            "adoid": 1,
            "adourl": "https://dev.azure.com/test_organization/c2957126-cdef-4f9a-bcc8-09323d1b7095/_workitems/edit/1",  # noqa: E501
            "adotype": "Impediment",
            "adostate": "Closed",
            "adoactivity": "",
            "adopriority": 2,
            "adoremainingwork": None,
            "adoparent": None,
            "adonamespace": "test_organization\\test_project",
            "description": '(bw)Impediment#1 - Example Title .. https://dev.azure.com/test_organization/c2957126-cdef-4f9a-bcc8-09323d1b7095/_workitems/edit/1',  # noqa: E501
        }
        task = next(service.issues())
        assert task.to_taskwarrior_data() == expected

    def test_issues_wiql_filter(self, make_service):
        expected = {
            "project": None,
            "priority": "M",
            "annotations": [],
            "entry": datetime(2020, 7, 8, 17, 31, 46, 0, tzinfo=timezone.utc),
            "end": datetime(2020, 7, 8, 19, 55, 46, 0, tzinfo=timezone.utc),
            "adotitle": "Example Title",
            "adodescription": " This Description has some html in it ",
            "adoid": 1,
            "adourl": "https://dev.azure.com/test_organization/c2957126-cdef-4f9a-bcc8-09323d1b7095/_workitems/edit/1",  # noqa: E501
            "adotype": "Impediment",
            "adostate": "Closed",
            "adoactivity": "",
            "adopriority": 2,
            "adoremainingwork": None,
            "adoparent": None,
            "adonamespace": "test_organization\\test_project",
            "description": '(bw)Impediment#1 - Example Title .. https://dev.azure.com/test_organization/c2957126-cdef-4f9a-bcc8-09323d1b7095/_workitems/edit/1',  # noqa: E501
        }
        service = make_service(wiql_filter='something')
        task = next(service.issues())
        assert task.to_taskwarrior_data() == expected
