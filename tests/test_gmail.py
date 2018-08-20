import mock
import os.path
from .base import ServiceTest, AbstractServiceTest
import bugwarrior.services.gmail as gmail

TEST_THREAD = {
        "messages": [
            {
                "payload": {
                    "headers": [
                        {
                            "name": "From",
                            "value": "Foo Bar <foobar@example.com>"
                        },
                        {
                            "name": "Subject",
                            "value": "Regarding Bugwarrior"
                        },
                        {
                            "name": "To",
                            "value": "ct@example.com"
                        }
                    ],
                    "parts": [
                        {
                        }
                    ]
                },
                "snippet": "Bugwarrior is great",
                "threadId": "1234",
                "labelIds": [
                    "IMPORTANT",
                    "Label_1",
                    "Label_43",
                    "CATEGORY_PERSONAL"
                ],
                "id": "9999"
            }
        ],
        "id": "1234"
    }

TEST_LABELS = [
        {'id': 'IMPORTANT', 'name': 'IMPORTANT'},
        {'id': 'CATEGORY_PERSONAL', 'name': 'CATEGORY_PERSONAL'},
        {'id': 'Label_1', 'name': 'sticky'},
        {'id': 'Label_43', 'name': 'postit'},
]

class TestGmailIssue(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        'gmail.add_tags': 'added',
        'gmail.login_name': 'test@example.com',
    }

    def setUp(self):
        super(TestGmailIssue, self).setUp()

        mock_api = mock.Mock()
        mock_api().users().labels().list().execute.return_value = {'labels': TEST_LABELS}
        mock_api().users().threads().list().execute.return_value = {'threads': [{'id': TEST_THREAD['id']}]}
        mock_api().users().threads().get().execute.return_value = TEST_THREAD
        gmail.GmailService.build_api = mock_api
        self.service = self.get_mock_service(gmail.GmailService, section='test_section')

    def test_config_paths(self):
        credentials_path = os.path.join(
            self.service.config.data.path,
            'gmail_credentials_test_example_com.json')
        self.assertEqual(self.service.credentials_path, credentials_path)

    def test_to_taskwarrior(self):
        thread = TEST_THREAD
        issue = self.service.get_issue_for_record(
                thread,
                gmail.thread_extras(thread, self.service.get_labels()))
        expected = {
            'gmailthreadid': '1234',
            'gmailsnippet': 'Bugwarrior is great',
            'gmaillastsender': 'Foo Bar',
            'tags': set(['sticky', 'postit']),
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
            'gmailthreadid': '1234',
            'gmailsnippet': 'Bugwarrior is great',
            'gmaillastsender': 'Foo Bar',
            'description': u'(bw)Is#1234 - Regarding Bugwarrior .. https://mail.google.com/mail/u/0/#all/1234',
            'priority': 'M',
            'tags': set(['sticky', 'postit', 'added']),
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
