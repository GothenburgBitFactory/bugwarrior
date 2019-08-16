
from datetime import datetime
from dateutil.tz import tzutc
from unittest.mock import MagicMock

import bugwarrior.services.outlook365 as outlook365
from .base import ServiceTest, AbstractServiceTest

TEST_MESSAGES = [
    MagicMock(**{
        'subject': 'Test',
        'get_body_text.return_value': 'Body text',
        'body_preview': 'Snippet text',
        'received': datetime(2019, 8, 15, 23, 56, 45, tzinfo=tzutc()),
        'conversation_id': 'someid',
        'categories': ['foo', 'bar'],
        'web_link': 'https://sample.invalid',
    }),
    MagicMock(**{
        'subject': 'Ignored',
        'get_body_text.return_value': 'Ignored',
        'body_preview': 'Ignored',
        'received': datetime(2019, 8, 15, 23, 56, 45, tzinfo=tzutc()),
        'conversation_id': 'ignored',
        'categories': ['ignored'],
        'web_link': 'https://sample.invalid',
    }),
]


class TestOutlook365Issue(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        'outlook365.description_template': '{{outlook365subject}}',
    }

    def setUp(self):
        super(TestOutlook365Issue, self).setUp()

        mock_api = MagicMock(is_authenticated=True)
        mock_api.mailbox().get_messages.return_value = TEST_MESSAGES
        outlook365.Outlook365Service.get_account = MagicMock(return_value=mock_api)
        self.service = self.get_mock_service(outlook365.Outlook365Service, section='test_section')

    def test_to_taskwarrior(self):
        issue = self.service.get_issue_for_record(outlook365.to_record(TEST_MESSAGES[0]))
        expected = {
            'annotations': [],
            'entry': datetime(2019, 8, 15, 23, 56, 45, tzinfo=tzutc()),
            'tags': ['foo', 'bar'],
            'priority': 'M',
            'outlook365subject': 'Test',
            'outlook365body': 'Body text',
            'outlook365weblink': 'https://sample.invalid',
            'outlook365preview': 'Snippet text',
            'outlook365conversationid': 'someid',
        }

        tw = issue.to_taskwarrior()
        self.assertEqual(tw, expected)

    def test_issues(self):
        issue = next(self.service.issues())
        expected = {
            'description': 'Test',
            'annotations': [],
            'entry': datetime(2019, 8, 15, 23, 56, 45, tzinfo=tzutc()),
            'tags': {'foo', 'bar'},
            'priority': 'M',
            'outlook365subject': 'Test',
            'outlook365body': 'Body text',
            'outlook365weblink': 'https://sample.invalid',
            'outlook365preview': 'Snippet text',
            'outlook365conversationid': 'someid',
        }

        tw = issue.get_taskwarrior_record()
        tw['tags'] = set(tw['tags'])

        self.assertEqual(tw, expected)
