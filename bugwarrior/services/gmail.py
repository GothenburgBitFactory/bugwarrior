import email
from .google import GoogleService
from bugwarrior.services import Issue

import logging
log = logging.getLogger(__name__)

class GmailIssue(Issue):
    THREAD_ID = 'gmailthreadid'
    SUBJECT = 'gmailsubject'
    URL = 'gmailurl'
    LAST_SENDER = 'gmaillastsender'
    LAST_SENDER_ADDR = 'gmaillastsenderaddr'
    SNIPPET = 'gmailsnippet'

    UNIQUE_KEY = (THREAD_ID,)
    UDAS = {
        THREAD_ID: {
            'type': 'string',
            'label': 'GMail Thread Id',
        },
        SUBJECT: {
            'type': 'string',
            'label': 'GMail Subject',
        },
        URL: {
            'type': 'string',
            'label': 'GMail URL',
        },
        LAST_SENDER: {
            'type': 'string',
            'label': 'GMail last sender name',
        },
        LAST_SENDER_ADDR: {
            'type': 'string',
            'label': 'GMail last sender address',
        },
        SNIPPET: {
            'type': 'string',
            'label': 'GMail snippet',
        }
    }
    EXCLUDE_LABELS = [
        'IMPORTANT',
        'CATEGORY_PERSONAL',
        'CATEGORY_PROMOTIONS',
        'CATEGORY_UPDATES',
        'CATEGORY_FORUMS',
        'SENT']

    def to_taskwarrior(self):
        return {
            'tags': [label
                for label in self.extra['labels']
                if label not in self.EXCLUDE_LABELS],
            'priority': self.origin['default_priority'],
            self.THREAD_ID: self.record['id'],
            self.SUBJECT: self.extra['subject'],
            self.URL: self.extra['url'],
            self.LAST_SENDER: self.extra['last_sender_name'],
            self.LAST_SENDER_ADDR: self.extra['last_sender_address'],
            self.SNIPPET: self.extra['snippet'],
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.extra['subject'],
            url=self.get_processed_url(self.extra['url']),
            number=self.record['id'],
            cls='issue',
        )

class GmailService(GoogleService):
    APPLICATION_NAME = 'Bugwarrior Gmail Service'
    SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'

    ISSUE_CLASS = GmailIssue
    CONFIG_PREFIX = 'gmail'
    RESOURCE = 'gmail'

    def __init__(self, *args, **kw):
        super(GmailService, self).__init__(*args, **kw)
        self.query = self.config.get('query', 'label:Starred')

    def get_labels(self):
        result = self.api.users().labels().list(userId=self.login_name).execute()
        return {label['id']: label['name'] for label in result['labels']}

    def get_threads(self):
        thread_service = self.api.users().threads()

        result = thread_service.list(userId=self.login_name, q=self.query).execute()
        return [
            thread_service.get(userId='me', id=thread['id']).execute()
            for thread in result.get('threads', [])]

    def issues(self):
        labels = self.get_labels()
        for thread in self.get_threads():
            yield self.get_issue_for_record(thread, thread_extras(thread, labels))

def thread_extras(thread, labels):
    (name, address) = thread_last_sender(thread)
    return {
        'labels': [labels[label_id] for label_id in thread_labels(thread)],
        'subject': message_header(thread['messages'][0], 'Subject'),
        'url': "https://mail.google.com/mail/u/0/#all/%s" % (thread['id'],),
        'last_sender_name': name,
        'last_sender_address': address,
        'snippet': thread_snippet(thread),
    }

def thread_labels(thread):
    return {label for message in thread['messages'] for label in message['labelIds']}

def thread_subject(thread):
    return message_header(thread['messages'][0], 'Subject')

def thread_last_sender(thread):
    from_header = message_header(thread['messages'][-1], 'From')
    (name, address) = email.utils.parseaddr(from_header)
    return (name if name else address, address)

def thread_snippet(thread):
    return thread['messages'][-1]['snippet']

def message_header(message, header_name):
    for item in message['payload']['headers']:
        if item['name'] == header_name:
            return item['value']
