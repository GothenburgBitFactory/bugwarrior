import email
import logging
import multiprocessing
import os
import pickle
import re
import time

import googleapiclient.discovery
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

from bugwarrior.services import IssueService, Issue

log = logging.getLogger(__name__)


class GmailIssue(Issue):
    THREAD_ID = 'gmailthreadid'
    SUBJECT = 'gmailsubject'
    URL = 'gmailurl'
    LAST_SENDER = 'gmaillastsender'
    LAST_SENDER_ADDR = 'gmaillastsenderaddr'
    LAST_MESSAGE_ID = 'gmaillastmessageid'
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
        LAST_MESSAGE_ID: {
            'type': 'string',
            'label': 'Last RFC2822 Message-ID',
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
            'annotations': self.get_annotations(),
            'entry': self.get_entry(),
            'tags': [label for label in self.extra['labels'] if label not in self.EXCLUDE_LABELS],
            'priority': self.origin['default_priority'],
            self.THREAD_ID: self.record['id'],
            self.SUBJECT: self.extra['subject'],
            self.URL: self.extra['url'],
            self.LAST_SENDER: self.extra['last_sender_name'],
            self.LAST_SENDER_ADDR: self.extra['last_sender_address'],
            self.LAST_MESSAGE_ID: self.extra['last_message_id'],
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

    def get_annotations(self):
        return self.extra.get('annotations', [])

    def get_entry(self):
        date_string = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(self.extra['internal_date']) / 1000))
        return self.parse_date(date_string)


class GmailService(IssueService):
    APPLICATION_NAME = 'Bugwarrior Gmail Service'
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
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

        credentials_name = clean_filename(self.login_name if self.login_name != 'me' else self.target)
        self.credentials_path = os.path.join(
            self.config.data.path,
            'gmail_credentials_%s.pickle' % (credentials_name,))
        self.gmail_api = self.build_api()

    def get_config_path(self, varname, default_path=None):
        return os.path.expanduser(self.config.get(varname, default_path))

    def build_api(self):
        credentials = self.get_credentials()
        return googleapiclient.discovery.build('gmail', 'v1', credentials=credentials, cache_discovery=False)

    def get_credentials(self):
        """Gets valid user credentials from storage.

        If nothing has been stored, or if the stored credentials are invalid,
        the OAuth2 flow is completed to obtain the new credentials.

        Returns:
            Credentials, the obtained credential.
        """
        with self.AUTHENTICATION_LOCK:
            log.info('Starting authentication for %s', self.target)
            credentials = None
            # The self.credentials_path file stores the user's access and refresh
            # tokens as a pickle, and is created automatically when the
            # authorization flow completes for the first time.
            if os.path.exists(self.credentials_path):
                with open(self.credentials_path, 'rb') as token:
                    credentials = pickle.load(token)

            # If there are no (valid) credentials available, let the user log in.
            if not credentials or not credentials.valid:
                log.info("No valid login. Starting OAUTH flow.")
                if credentials and credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.client_secret_path, self.SCOPES)
                    credentials = flow.run_local_server(port=0)
                # Save the credentials for the next run
                with open(self.credentials_path, 'wb') as token:
                    pickle.dump(credentials, token)
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

    def annotations(self, issue):
        sender = issue.extra['last_sender_name']
        subj = issue.extra['subject']
        issue_url = issue.get_processed_url(issue.extra['url'])
        return self.build_annotations([(sender, subj)], issue_url)

    def issues(self):
        labels = self.get_labels()
        for thread in self.get_threads():
            issue = self.get_issue_for_record(thread, thread_extras(thread, labels))
            extra = {
                'annotations': self.annotations(issue),
            }
            issue.update_extra(extra)
            yield issue


def thread_extras(thread, labels):
    name, address = thread_last_sender(thread)
    last_message_id = thread_last_message_id(thread)
    return {
        'internal_date': thread_timestamp(thread),
        'labels': [labels[label_id] for label_id in thread_labels(thread)],
        'last_sender_address': address,
        'last_sender_name': name,
        'last_message_id': last_message_id,
        'snippet': thread_snippet(thread),
        'subject': thread_subject(thread),
        'url': thread_url(thread),
    }


def thread_labels(thread):
    return {label for message in thread['messages'] for label in message['labelIds']}


def thread_subject(thread):
    return message_header(thread['messages'][0], 'Subject')


def thread_last_sender(thread):
    from_header = message_header(thread['messages'][-1], 'From')
    name, address = email.utils.parseaddr(from_header)
    return name if name else address, address


def thread_last_message_id(thread):
    message_id_header = message_header(thread['messages'][-1], 'Message-ID')
    if not message_id_header or message_id_header == '':
        return ''
    return message_id_header[1:-1]  # remove the enclosing < >.


def thread_timestamp(thread):
    return thread['messages'][-1]['internalDate']


def thread_snippet(thread):
    return thread['messages'][-1]['snippet']


def thread_url(thread):
    return "https://mail.google.com/mail/u/0/#all/%s" % (thread['id'],)


def message_header(message, header_name):
    for item in message['payload']['headers']:
        if item['name'] == header_name:
            return item['value']


def clean_filename(name):
    return re.sub(r'[^A-Za-z0-9_]+', '_', name)
