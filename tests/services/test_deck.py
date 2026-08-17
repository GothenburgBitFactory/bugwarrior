from datetime import datetime, timezone
from unittest import mock

import pytest

from bugwarrior.services.deck import NextcloudDeckClient

from ..base import get_validated_service


@pytest.fixture
def record():
    return {
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
                "ETag": "e388bcf5a1d076dd6b7d097ff259cd16",
            }
        ],
        "assignedUsers": [
            {
                "id": 2,
                "participant": {
                    "primaryKey": "rainbow",
                    "uid": "rainbow",
                    "displayname": "Rainbow",
                    "type": 0,
                },
                "cardId": 35,
                "type": 0,
            }
        ],
        "attachments": None,
        "attachmentCount": 0,
        "owner": {
            "primaryKey": "unicorn",
            "uid": "unicorn",
            "displayname": "Unicorn",
            "type": 0,
        },
        "order": 10,
        "archived": False,
        "duedate": "2022-11-20T23:00:00+00:00",
        "deletedAt": 0,
        "commentsUnread": 0,
        "commentsCount": 0,
        "id": 11,
        "ETag": "9641ba85250eedb2f2027ac49cf58796",
        "overdue": 0,
    }


SERVICE_CONFIG = {
    'service': 'deck',
    'base_uri': 'http://localhost:8080',
    'username': 'testuser',
    'password': 'testpassword',
    'import_labels_as_tags': True,
}


class TestDeckIssue:
    @pytest.fixture
    def config(self):
        return {
            'general': {
                'targets': ['myservice'],
                # would otherwise cut the title short
                'description_length': '45',
            },
            'myservice': {**SERVICE_CONFIG},
        }

    @pytest.fixture
    def make_service(self, record):
        def make(config):
            service = get_validated_service(config)
            service.client = mock.MagicMock(spec=NextcloudDeckClient)
            service.client.get_boards = mock.MagicMock(
                return_value=[{'id': 5, 'title': 'testboard'}]
            )
            service.client.get_stacks = mock.MagicMock(
                return_value=[{'id': 13, 'title': 'teststack', 'cards': [record]}]
            )
            service.client.get_comments = mock.MagicMock(
                return_value={
                    'ocs': {
                        'data': [{'actorDisplayName': 'Lena', 'message': 'testcomment'}]
                    }
                }
            )
            return service

        return make

    @pytest.fixture
    def service(self, config, make_service):
        return make_service(config)

    def test_to_taskwarrior(self, service, record):
        issue = service.get_issue_for_record(
            record,
            {
                'board': {'title': 'testboard', 'id': 5},
                'stack': {'title': 'teststack', 'id': 13},
                'annotations': ['@Lena - testcomment'],
            },
        )

        expected = {
            'annotations': ['@Lena - testcomment'],
            'entry': datetime(2022, 8, 17, 20, 16, 22, tzinfo=timezone.utc),
            'due': datetime(2022, 11, 20, 23, 0, tzinfo=timezone.utc),
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
            'tags': ['Later'],
        }
        actual = issue.to_taskwarrior().to_taskwarrior_data()

        assert actual == expected

    def test_issues(self, service):
        task = next(service.issues())

        expected = {
            'annotations': ['@Lena - testcomment'],
            'entry': datetime(2022, 8, 17, 20, 16, 22, tzinfo=timezone.utc),
            'due': datetime(2022, 11, 20, 23, 0, tzinfo=timezone.utc),
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
            'tags': ['Later'],
        }

        assert task.to_taskwarrior_data() == expected

    def test_get_owner(self, config, record, make_service):
        config['myservice']['only_if_assigned'] = 'rainbow'
        service = make_service(config)
        assert service.get_owner(record) == 'rainbow'

    def test_filter_boards_include(self, config, make_service):
        config['myservice']['include_board_ids'] = '5'
        service = make_service(config)
        assert service.filter_boards({'title': 'testboard', 'id': 5})
        assert not service.filter_boards({'title': 'testboard', 'id': 6})

    def test_filter_boards_exclude(self, config, make_service):
        config['myservice']['exclude_board_ids'] = '5'
        service = make_service(config)
        assert not service.filter_boards({'title': 'testboard', 'id': 5})
        assert service.filter_boards({'title': 'testboard', 'id': 6})
