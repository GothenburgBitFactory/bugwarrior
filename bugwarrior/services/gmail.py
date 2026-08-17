from collections.abc import Iterator
from datetime import datetime, timezone
import email
import email.utils
import logging
import multiprocessing
import os
from pathlib import Path
import pickle
import re
import typing
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import googleapiclient.discovery
from pydantic import Field

from bugwarrior import config
from bugwarrior.services import Issue, Service
from bugwarrior.task import Task, Udas

log = logging.getLogger(__name__)


class GmailConfig(config.ServiceConfig):
    service: typing.Literal['gmail']
    KEYRING_SERVICE = 'gmail://{login_name}'

    client_secret_path: config.ExpandedPath = Path('~/.gmail_client_secret.json')
    query: str = 'label:Starred'
    login_name: str = 'me'
    thread_limit: int = 100

    only_if_assigned: config.UnsupportedOption[str] = ''
    also_unassigned: config.UnsupportedOption[bool] = False


class GmailUdas(Udas):
    """Service-specific UDAs contributed by GMail."""

    UNIQUE_KEY = ('gmailthreadid',)

    gmailthreadid: str = Field(title='GMail Thread Id')
    gmailsubject: str = Field(title='GMail Subject')
    gmailurl: str = Field(title='GMail URL')
    gmaillastsender: str = Field(title='GMail last sender name')
    gmaillastsenderaddr: str = Field(title='GMail last sender address')
    gmaillastmessageid: str | None = Field(title='Last RFC2822 Message-ID')
    gmailsnippet: str = Field(title='GMail snippet')
    gmaillabels: str = Field(title='GMail labels')


class GmailTask(Task):
    udas: GmailUdas


class GmailIssue(Issue):
    EXCLUDE_LABELS = [
        'IMPORTANT',
        'CATEGORY_PERSONAL',
        'CATEGORY_PROMOTIONS',
        'CATEGORY_UPDATES',
        'CATEGORY_FORUMS',
        'SENT',
    ]

    def to_taskwarrior(self) -> GmailTask:
        return GmailTask(
            annotations=self.get_annotations(),
            entry=self.get_entry(),
            tags=[
                label
                for label in self.extra['labels']
                if label not in self.EXCLUDE_LABELS
            ],
            priority=self.config.default_priority,
            udas=GmailUdas(
                gmailthreadid=self.record['id'],
                gmailsubject=self.extra['subject'],
                gmailurl=self.extra['url'],
                gmaillastsender=self.extra['last_sender_name'],
                gmaillastsenderaddr=self.extra['last_sender_address'],
                gmaillastmessageid=self.extra['last_message_id'],
                gmailsnippet=self.extra['snippet'],
                gmaillabels=" ".join(sorted(self.extra['labels'])),
            ),
        )

    def get_default_description(self) -> str:
        return self.build_default_description(
            title=self.extra['subject'],
            url=self.extra['url'],
            number=self.record['id'],
            cls='issue',
        )

    def get_annotations(self) -> list[str]:
        return self.extra.get('annotations', [])

    def get_entry(self) -> datetime:
        # internal_date is in milliseconds, convert to seconds and create UTC datetime
        timestamp_seconds = int(self.extra['internal_date']) / 1000
        return datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)


class GmailService(Service):
    APPLICATION_NAME = 'Bugwarrior Gmail Service'
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

    API_VERSION = 2.0
    ISSUE_CLASS = GmailIssue
    TASK_SCHEMA = GmailTask
    CONFIG_SCHEMA = GmailConfig
    AUTHENTICATION_LOCK = multiprocessing.Lock()

    def __init__(
        self, config: GmailConfig, main_config: config.MainSectionConfig
    ) -> None:
        super().__init__(config, main_config)

        credentials_name = clean_filename(
            self.config.login_name
            if self.config.login_name != 'me'
            else self.config.target
        )
        self.credentials_path = os.path.join(
            self.main_config.data.path,
            'gmail_credentials_%s.pickle' % (credentials_name,),
        )
        self.gmail_api = self.build_api()

    def build_api(self) -> googleapiclient.discovery.Resource:
        credentials = self.get_credentials()
        return googleapiclient.discovery.build(
            'gmail', 'v1', credentials=credentials, cache_discovery=False
        )

    def get_credentials(self) -> Credentials:
        """Gets valid user credentials from storage.

        If nothing has been stored, or if the stored credentials are invalid,
        the OAuth2 flow is completed to obtain the new credentials.

        Returns:
            Credentials, the obtained credential.
        """
        with self.AUTHENTICATION_LOCK:
            log.info('Starting authentication for %s', self.config.target)
            credentials = None
            # The self.credentials_path file stores the user's access and refresh
            # tokens as a pickle, and is created automatically when the
            # authorization flow completes for the first time.
            if os.path.exists(self.credentials_path):
                with open(self.credentials_path, 'rb') as token:
                    credentials = pickle.load(token)
                os.chmod(self.credentials_path, 0o600)

            # If there are no (valid) credentials available, let the user log in.
            if not credentials or not credentials.valid:
                log.info("No valid login. Starting OAUTH flow.")
                if credentials and credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.config.client_secret_path, self.SCOPES
                    )
                    credentials = flow.run_local_server(port=0)
                # Save the credentials for the next run
                with open(self.credentials_path, 'wb') as token:
                    pickle.dump(credentials, token)
                log.info('Storing credentials to %r', self.credentials_path)
            return credentials

    def get_labels(self) -> dict[str, str]:
        result = (
            self.gmail_api.users()  # ty: ignore[unresolved-attribute]
            .labels()
            .list(userId=self.config.login_name)
            .execute()
        )
        return {label['id']: label['name'] for label in result['labels']}

    def get_threads(self) -> list[dict[str, Any]]:
        thread_service = self.gmail_api.users().threads()  # ty: ignore[unresolved-attribute]
        threads = []

        pageToken = None

        while len(threads) < self.config.thread_limit:
            maxResults = min(100, self.config.thread_limit - len(threads))

            result = thread_service.list(
                userId=self.config.login_name,
                q=self.config.query,
                maxResults=maxResults,
                pageToken=pageToken,
            ).execute()

            for thread in result.get('threads', []):
                threads.append(
                    thread_service.get(userId='me', id=thread['id']).execute()
                )

            pageToken = result.get('nextPageToken', None)
            if not pageToken:
                break

        return threads

    def annotations(self, extra: dict[str, Any]) -> list[str]:
        return self.build_annotations(
            [(extra['last_sender_name'], extra['subject'])], extra['url']
        )

    def issues(self) -> Iterator[Task]:
        labels = self.get_labels()
        for thread in self.get_threads():
            extra = thread_extras(thread, labels)
            extra['annotations'] = self.annotations(extra)
            yield self.process_record(thread, extra)


def thread_extras(thread: dict[str, Any], labels: dict[str, str]) -> dict[str, Any]:
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


def thread_labels(thread: dict[str, Any]) -> set[str]:
    return {label for message in thread['messages'] for label in message['labelIds']}


def thread_subject(thread: dict[str, Any]) -> str | None:
    return message_header(thread['messages'][0], 'Subject')


def thread_last_sender(thread: dict[str, Any]) -> tuple[str, str]:
    from_header = message_header(thread['messages'][-1], 'From')
    name, address = email.utils.parseaddr(from_header or "")
    return name if name else address, address


def thread_last_message_id(thread: dict[str, Any]) -> str:
    message_id_header = message_header(thread['messages'][-1], 'Message-ID')
    if not message_id_header or message_id_header == '':
        return ''
    return message_id_header[1:-1]  # remove the enclosing < >.


def thread_timestamp(thread: dict[str, Any]) -> str:
    return thread['messages'][-1]['internalDate']


def thread_snippet(thread: dict[str, Any]) -> str:
    return thread['messages'][-1]['snippet']


def thread_url(thread: dict[str, Any]) -> str:
    return "https://mail.google.com/mail/u/0/#all/%s" % (thread['id'],)


def message_header(message: dict[str, Any], header_name: str) -> str | None:
    for item in message['payload']['headers']:
        if item['name'] == header_name:
            return item['value']


def clean_filename(name: str) -> str:
    return re.sub(r'[^A-Za-z0-9_]+', '_', name)
