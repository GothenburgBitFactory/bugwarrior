import os.path
import pickle
from copy import copy
from datetime import datetime, timedelta
from unittest import mock
from unittest.mock import patch

from dateutil.tz import tzutc
from google.oauth2.credentials import Credentials

from bugwarrior.config.load import BugwarriorConfigParser
from bugwarrior.services import gmail

from .base import AbstractServiceTest, ConfigTest, ServiceTest

TEST_CREDENTIAL = {
    "token": "itsatokeneveryone",
    "refresh_token": "itsarefreshtokeneveryone",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_id": "example.apps.googleusercontent.com",
    "client_secret": "itsasecrettoeveryone",
    "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
}


class TestGmailService(ConfigTest):

    def setUp(self):
        super().setUp()
        self.config = BugwarriorConfigParser()
        self.config['general'] = {'targets': 'myservice'}
        self.config['myservice'] = {'service': 'gmail'}

        mock_data = mock.Mock()
        mock_data.path = self.tempdir

        mock_api = mock.Mock()
        gmail.GmailService.build_api = mock_api

        conf = self.validate()
        self.service = gmail.GmailService(
            conf['myservice'], conf['general'], 'myservice')

    def test_get_credentials_exists_and_valid(self):
        expected = Credentials(**copy(TEST_CREDENTIAL))
        self.assertEqual(expected.valid, True)
        with open(self.service.credentials_path, "wb") as token:
            pickle.dump(expected, token)

        self.assertEqual(self.service.get_credentials().to_json(),
                         expected.to_json())

    def test_get_credentials_with_refresh(self):
        expired_credential = Credentials(**copy(TEST_CREDENTIAL))
        expired_credential.expiry = datetime.utcnow()
        self.assertEqual(expired_credential.valid, False)
        with open(self.service.credentials_path, "wb") as token:
            pickle.dump(expired_credential, token)

        with patch("google.oauth2.reauth.refresh_grant") as mock_refresh_grant:
            access_token = "newaccesstoken"
            refresh_token = "newrefreshtoken"
            expiry = datetime.utcnow() + timedelta(hours=24)
            grant_response = {"id_token": "idtoken"}
            rapt_token = "reauthprooftoken"
            mock_refresh_grant.return_value = (
                access_token, refresh_token, expiry, grant_response, rapt_token
            )
            refreshed_credential = self.service.get_credentials()
        self.assertEqual(refreshed_credential.valid, True)


TEST_THREAD = {
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

TEST_LABELS = [
    {"id": "IMPORTANT", "name": "IMPORTANT"},
    {"id": "CATEGORY_PERSONAL", "name": "CATEGORY_PERSONAL"},
    {"id": "Label_1", "name": "sticky"},
    {"id": "Label_43", "name": "postit"},
]


class TestGmailIssue(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        'service': 'gmail',
        'gmail.add_tags': 'added',
        'gmail.login_name': 'test@example.com',
    }

    def setUp(self):
        super().setUp()

        mock_api = mock.Mock()
        mock_api().users().labels().list().execute.return_value = {'labels': TEST_LABELS}
        mock_api().users().threads().list().execute.return_value = {
            'threads': [{'id': TEST_THREAD['id']}]}
        mock_api().users().threads().get().execute.return_value = TEST_THREAD
        gmail.GmailService.build_api = mock_api
        self.service = self.get_mock_service(gmail.GmailService, section='test_section')

    def test_config_paths(self):
        credentials_path = os.path.join(
            self.service.main_config.data.path,
            'gmail_credentials_test_example_com.pickle')
        self.assertEqual(self.service.credentials_path, credentials_path)

    def test_to_taskwarrior(self):
        thread = TEST_THREAD
        issue = self.service.get_issue_for_record(
            thread,
            gmail.thread_extras(thread, self.service.get_labels()))
        expected = {
            'annotations': [],
            'entry': datetime(2019, 1, 5, 21, 7, 47, tzinfo=tzutc()),
            'gmailthreadid': '1234',
            'gmaillastmessageid': 'CMCRSF+6r=x5JtW4wlRYR5qdfRq+iAtSoec5NqrHvRpvVgHbHdg@mail.gmail.com',  # noqa: E501
            'gmailsnippet': 'Bugwarrior is great',
            'gmaillastsender': 'Foo Bar',
            'tags': {'postit', 'sticky'},
            'gmailsubject': 'Regarding Bugwarrior',
            'gmailurl': 'https://mail.google.com/mail/u/0/#all/1234',
            'gmaillabels': 'CATEGORY_PERSONAL IMPORTANT postit sticky',
            'priority': 'M',
            'gmaillastsenderaddr': 'foobar@example.com'}

        taskwarrior = issue.to_taskwarrior()
        taskwarrior['tags'] = set(taskwarrior['tags'])

        self.assertEqual(taskwarrior, expected)

    def test_issues(self):
        issue = next(self.service.issues())
        expected = {
            'annotations': ['@Foo Bar - Regarding Bugwarrior'],
            'entry': datetime(2019, 1, 5, 21, 7, 47, tzinfo=tzutc()),
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
            'gmaillastsenderaddr': 'foobar@example.com'}

        taskwarrior = issue.get_taskwarrior_record()
        taskwarrior['tags'] = set(taskwarrior['tags'])

        self.assertEqual(taskwarrior, expected)

    def test_last_sender(self):
        test_thread = {
            'messages': [
                {
                    'payload':
                        {
                            'headers': [
                                {'name': 'From', 'value': 'Xyz <xyz@example.com'}
                            ]
                        }
                },
                {
                    'payload':
                        {
                            'headers': [
                                {'name': 'From', 'value': 'Foo Bar <foobar@example.com'}
                            ]
                        }
                },
            ]
        }
        self.assertEqual(gmail.thread_last_sender(test_thread), ('Foo Bar', 'foobar@example.com'))
