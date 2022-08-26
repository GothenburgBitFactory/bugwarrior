import datetime
from unittest import mock

import pydantic
from dateutil.tz import tzutc

from bugwarrior.services.deck import NextcloudDeckClient, NextcloudDeckService
from .base import AbstractServiceTest, ServiceTest


# NOTE: replace with stdlib dataclasses.dataclass once python-3.6 is dropped
@pydantic.dataclasses.dataclass
class TestData:
    arbitrary_card = {
        "title": "check that nextcloud deck integration works",
        "description": "some additional description",
        "stackId": 13,
        "type": "plain",
        "lastModified": 1660884880,
        "lastEditor": None,
        "createdAt": 1660767382,
        "labels": [
            {
                "title": "Later",
                "color": "F1DB50",
                "boardId": 2,
                "cardId": 11,
                "lastModified": 1660767234,
                "id": 8,
                "ETag": "e388bcf5a1d076dd6b7d097ff259cd16"
            }
        ],
        "assignedUsers": [
            {
                "id": 2,
                "participant": {
                    "primaryKey": "rainbow",
                    "uid": "rainbow",
                    "displayname": "Rainbow",
                    "type": 0
                },
                "cardId": 35,
                "type": 0
            }
        ],
        "attachments": None,
        "attachmentCount": 0,
        "owner": {
            "primaryKey": "unicorn",
            "uid": "unicorn",
            "displayname": "Unicorn",
            "type": 0
        },
        "order": 10,
        "archived": False,
        "duedate": "2022-11-20T23:00:00+00:00",
        "deletedAt": 0,
        "commentsUnread": 0,
        "commentsCount": 0,
        "id": 11,
        "ETag": "9641ba85250eedb2f2027ac49cf58796",
        "overdue": 0
    }


class TestNextcloudDeckIssue(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        'service': 'deck',
        'deck.base_uri': 'http://localhost:8080',
        'deck.username': 'testuser',
        'deck.password': 'testpassword',
        'deck.import_labels_as_tags': True,
    }

    def setUp(self):
        super().setUp()

        self.data = TestData()

        self.service = self.get_mock_service(NextcloudDeckService)
        self.service.client = mock.MagicMock(spec=NextcloudDeckClient)
        self.service.client.get_boards = mock.MagicMock(
            return_value=[{'id': 5, 'title': 'testboard'}])
        self.service.client.get_stacks = mock.MagicMock(
            return_value=[{'id': 13, 'title': 'teststack', 'cards': [self.data.arbitrary_card]}])

    def test_to_taskwarrior(self):
        issue = self.service.get_issue_for_record(
            self.data.arbitrary_card, {
                'board': {'title': 'testboard', 'id': 5},
                'stack': {'title': 'teststack', 'id': 13},
            })

        expected = {
            #'annotations': [],
            'entry': datetime.datetime(2022, 8, 17, 20, 16, 22, tzinfo=tzutc()),
            'due': datetime.datetime(2022, 11, 20, 23, 0, tzinfo=tzutc()),
            'nextclouddeckassignee': 'rainbow',
            'nextclouddeckauthor': 'unicorn',
            'nextclouddeckboardid': 5,
            'nextclouddeckboardtitle': 'testboard',
            'nextclouddeckstackid': 13,
            'nextclouddeckstacktitle': 'teststack',
            'nextclouddeckcardid': 11,
            'nextclouddeckcardtitle': 'check that nextcloud deck integration works',
            'nextclouddeckdescription': 'some additional description',
            'nextclouddeckorder': 10,
            'priority': 'M',
            'project': 'testboard',
            'tags': ['Later']
        }
        actual = issue.to_taskwarrior()

        self.assertEqual(actual, expected)

    def test_issues(self):
        issue = next(self.service.issues())

        expected = {
            #'annotations': [],
            'entry': datetime.datetime(2022, 8, 17, 20, 16, 22, tzinfo=tzutc()),
            'due': datetime.datetime(2022, 11, 20, 23, 0, tzinfo=tzutc()),
            'description': '(bw)Is# - check that nextcloud deck integration works',
            'nextclouddeckassignee': 'rainbow',
            'nextclouddeckauthor': 'unicorn',
            'nextclouddeckboardid': 5,
            'nextclouddeckboardtitle': 'testboard',
            'nextclouddeckstackid': 13,
            'nextclouddeckstacktitle': 'teststack',
            'nextclouddeckcardid': 11,
            'nextclouddeckcardtitle': 'check that nextcloud deck integration works',
            'nextclouddeckdescription': 'some additional description',
            'nextclouddeckorder': 10,
            'priority': 'M',
            'project': 'testboard',
            'tags': ['Later']
        }

        self.assertEqual(issue.get_taskwarrior_record(), expected)
