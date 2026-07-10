from datetime import datetime, timedelta, timezone
from pathlib import Path
import pickle
from unittest import mock
from unittest.mock import patch

from google.oauth2.credentials import Credentials
import pytest

from bugwarrior.collect import TaskConstructor
from bugwarrior.services import gmail

from ..base import get_validated_service
from .base import get_mock_service


@pytest.fixture
def credential():
    return {
        "token": "itsatokeneveryone",
        "refresh_token": "itsarefreshtokeneveryone",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "example.apps.googleusercontent.com",
        "client_secret": "itsasecrettoeveryone",
        "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
    }


SERVICE_CONFIG = {
    'service': 'gmail',
    'add_tags': 'added',
    'login_name': 'test@example.com',
}


class TestGmailService:
    @pytest.fixture
    def config(self):
        return {
            'general': {'targets': ['myservice']},
            'myservice': {'service': 'gmail'},
        }

    @pytest.fixture
    def service(self, config, monkeypatch):
        monkeypatch.setattr(gmail.GmailService, 'build_api', mock.Mock())

        return get_validated_service(config)

    def test_get_credentials_exists_and_valid(self, service, credential):
        expected = Credentials(**credential)
        assert expected.valid is True
        with open(service.credentials_path, "wb") as token:
            pickle.dump(expected, token)

        assert service.get_credentials().to_json() == expected.to_json()

    def test_get_credentials_with_refresh(self, service, credential):
        expired_credential = Credentials(**credential)
        expired_credential.expiry = datetime.now(timezone.utc).replace(tzinfo=None)
        assert expired_credential.valid is False
        with open(service.credentials_path, "wb") as token:
            pickle.dump(expired_credential, token)

        with patch("google.oauth2.reauth.refresh_grant") as mock_refresh_grant:
            access_token = "newaccesstoken"
            refresh_token = "newrefreshtoken"
            expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
                hours=24
            )
            grant_response = {"id_token": "idtoken"}
            rapt_token = "reauthprooftoken"
            mock_refresh_grant.return_value = (
                access_token,
                refresh_token,
                expiry,
                grant_response,
                rapt_token,
            )
            refreshed_credential = service.get_credentials()
        assert refreshed_credential.valid is True


@pytest.fixture
def record():
    return {
        "messages": [
            {
                "payload": {
                    "headers": [
                        {"name": "From", "value": "Foo Bar <foobar@example.com>"},
                        {"name": "Subject", "value": "Regarding Bugwarrior"},
                        {"name": "To", "value": "ct@example.com"},
                        {
                            "name": "Message-ID",
                            "value": "<CMCRSF+6r=x5JtW4wlRYR5qdfRq+iAtSoec5NqrHvRpvVgHbHdg@mail.gmail.com>",  # noqa: E501
                        },
                    ],
                    "parts": [{}],
                },
                "snippet": "Bugwarrior is great",
                "internalDate": 1546722467000,
                "threadId": "1234",
                "labelIds": ["IMPORTANT", "Label_1", "Label_43", "CATEGORY_PERSONAL"],
                "id": "9999",
            }
        ],
        "id": "1234",
    }


@pytest.fixture
def labels():
    return [
        {"id": "IMPORTANT", "name": "IMPORTANT"},
        {"id": "CATEGORY_PERSONAL", "name": "CATEGORY_PERSONAL"},
        {"id": "Label_1", "name": "sticky"},
        {"id": "Label_43", "name": "postit"},
    ]


class TestGmailIssue:
    @pytest.fixture
    def service(self, record, labels, monkeypatch):
        mock_api = mock.Mock()
        mock_api().users().labels().list().execute.return_value = {'labels': labels}
        mock_api().users().threads().list().execute.return_value = {
            'threads': [{'id': record['id']}]
        }
        mock_api().users().threads().get().execute.return_value = record
        monkeypatch.setattr(gmail.GmailService, 'build_api', mock_api)
        return get_mock_service(gmail.GmailService, SERVICE_CONFIG)

    def test_config_paths(self, service):
        credentials_path = (
            Path(service.main_config.data.path)
            / 'gmail_credentials_test_example_com.pickle'
        )
        assert Path(service.credentials_path) == credentials_path

    def test_to_taskwarrior(self, service, record):
        issue = service.get_issue_for_record(
            record, gmail.thread_extras(record, service.get_labels())
        )
        expected = {
            'annotations': [],
            'entry': datetime(2019, 1, 5, 21, 7, 47, tzinfo=timezone.utc),
            'gmailthreadid': '1234',
            'gmaillastmessageid': 'CMCRSF+6r=x5JtW4wlRYR5qdfRq+iAtSoec5NqrHvRpvVgHbHdg@mail.gmail.com',  # noqa: E501
            'gmailsnippet': 'Bugwarrior is great',
            'gmaillastsender': 'Foo Bar',
            'tags': {'postit', 'sticky'},
            'gmailsubject': 'Regarding Bugwarrior',
            'gmailurl': 'https://mail.google.com/mail/u/0/#all/1234',
            'gmaillabels': 'CATEGORY_PERSONAL IMPORTANT postit sticky',
            'priority': 'M',
            'gmaillastsenderaddr': 'foobar@example.com',
        }

        taskwarrior = issue.to_taskwarrior()
        taskwarrior['tags'] = set(taskwarrior['tags'])

        assert taskwarrior == expected

    def test_issues(self, service):
        issue = next(service.issues())
        expected = {
            'annotations': ['@Foo Bar - Regarding Bugwarrior'],
            'entry': datetime(2019, 1, 5, 21, 7, 47, tzinfo=timezone.utc),
            'gmailthreadid': '1234',
            'gmaillastmessageid': 'CMCRSF+6r=x5JtW4wlRYR5qdfRq+iAtSoec5NqrHvRpvVgHbHdg@mail.gmail.com',  # noqa: E501
            'gmailsnippet': 'Bugwarrior is great',
            'gmaillastsender': 'Foo Bar',
            'description': '(bw)Is#1234 - Regarding Bugwarrior .. https://mail.google.com/mail/u/0/#all/1234',  # noqa: E501
            'priority': 'M',
            'tags': {'added', 'postit', 'sticky'},
            'gmailsubject': 'Regarding Bugwarrior',
            'gmailurl': 'https://mail.google.com/mail/u/0/#all/1234',
            'gmaillabels': 'CATEGORY_PERSONAL IMPORTANT postit sticky',
            'gmaillastsenderaddr': 'foobar@example.com',
        }

        taskwarrior = TaskConstructor(issue).get_taskwarrior_record()
        taskwarrior['tags'] = set(taskwarrior['tags'])

        assert taskwarrior == expected

    def test_last_sender(self):
        test_thread = {
            'messages': [
                {
                    'payload': {
                        'headers': [{'name': 'From', 'value': 'Xyz <xyz@example.com'}]
                    }
                },
                {
                    'payload': {
                        'headers': [
                            {'name': 'From', 'value': 'Foo Bar <foobar@example.com'}
                        ]
                    }
                },
            ]
        }
        assert gmail.thread_last_sender(test_thread) == (
            'Foo Bar',
            'foobar@example.com',
        )
