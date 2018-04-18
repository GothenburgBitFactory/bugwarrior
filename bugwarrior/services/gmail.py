import httplib2
import os
import email
import re
import multiprocessing

import googleapiclient.discovery
import oauth2client.client
import oauth2client.tools
import oauth2client.file

from bugwarrior.services import IssueService, Issue

import logging
log = logging.getLogger(__name__)

class GmailIssue(Issue):
    THREAD_ID = 'gmailthreadid'
    SUBJECT = 'gmailsubject'
    URL = 'gmailurl'
    LAST_SENDER = 'gmaillastsender'
    LAST_SENDER_ADDR = 'gmaillastsenderaddr'
    SNIPPET = 'gmailsnippet'
    LABELS = 'gmaillabels'

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
        },
        LABELS: {
            'type': 'string',
            'label': 'GMail labels',
        },
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
            self.LABELS: " ".join(sorted(self.extra['labels'])),
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.extra['subject'],
            url=self.get_processed_url(self.extra['url']),
            number=self.record['id'],
            cls='issue',
        )

class GmailService(IssueService):
    APPLICATION_NAME = 'Bugwarrior Gmail Service'
    SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'
    DEFAULT_CLIENT_SECRET_PATH = '~/.gmail_client_secret.json'

    ISSUE_CLASS = GmailIssue
    CONFIG_PREFIX = 'gmail'
    AUTHENTICATION_LOCK = multiprocessing.Lock()

    def __init__(self, *args, **kw):
        super(GmailService, self).__init__(*args, **kw)

        self.query = self.config.get('query', 'label:Starred')
        self.login_name = self.config.get('login_name', 'me')
        self.client_secret_path = self.get_config_path(
                'client_secret_path',
                self.DEFAULT_CLIENT_SECRET_PATH)
        credentials_name = clean_filename(self.login_name
                if self.login_name != 'me' else self.target)
        self.credentials_path = os.path.join(
                self.config.data.path,
                'gmail_credentials_%s.json' % (credentials_name,))
        self.gmail_api = self.build_api()

    def get_config_path(self, varname, default_path=None):
        return os.path.expanduser(self.config.get(varname, default_path))

    def build_api(self):
        credentials = self.get_credentials()
        http = credentials.authorize(httplib2.Http())
        return googleapiclient.discovery.build('gmail', 'v1', http=http)

    def get_credentials(self):
        """Gets valid user credentials from storage.

        If nothing has been stored, or if the stored credentials are invalid,
        the OAuth2 flow is completed to obtain the new credentials.

        Returns:
            Credentials, the obtained credential.
        """
        with self.AUTHENTICATION_LOCK:
            log.info('Starting authentication for %s', self.target)
            store = oauth2client.file.Storage(self.credentials_path)
            credentials = store.get()
            if not credentials or credentials.invalid:
                log.info("No valid login. Starting OAUTH flow.")
                flow = oauth2client.client.flow_from_clientsecrets(self.client_secret_path, self.SCOPES)
                flow.user_agent = self.APPLICATION_NAME
                flags = oauth2client.tools.argparser.parse_args([])
                credentials = oauth2client.tools.run_flow(flow, store, flags)
                log.info('Storing credentials to %r', self.credentials_path)
            return credentials

    def get_labels(self):
        result = self.gmail_api.users().labels().list(userId=self.login_name).execute()
        return {label['id']: label['name'] for label in result['labels']}

    def get_threads(self):
        thread_service = self.gmail_api.users().threads()

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

def clean_filename(name):
    return re.sub(r'[^A-Za-z0-9_]+', '_', name)
