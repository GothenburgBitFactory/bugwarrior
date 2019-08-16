import json
import logging
import os

from O365 import Account, FileSystemTokenBackend

from bugwarrior.services import IssueService, Issue

log = logging.getLogger(__name__)


class Outlook365Issue(Issue):
    SUBJECT = 'outlook365subject'
    BODY = 'outlook365body'
    URL = 'outlook365weblink'
    PREVIEW = 'outlook365preview'
    CONVERSATION_ID = 'outlook365conversationid'

    UNIQUE_KEY = (CONVERSATION_ID, )

    UDAS = {
        CONVERSATION_ID: {
            'type': 'string',
            'label': 'Outlook 365 Conversation Id',
        },
        SUBJECT: {
            'type': 'string',
            'label': 'Outlook 365 Subject',
        },
        URL: {
            'type': 'string',
            'label': 'Outlook 365 Web Link',
        },
        PREVIEW: {
            'type': 'string',
            'label': 'Outlook 365 Body Preview',
        },
        BODY: {
            'type': 'string',
            'label': 'Outlook 365 Body Text',
        },
    }

    def to_taskwarrior(self):
        return {
            'annotations': [],
            'entry': self.record['created'],
            'tags': self.record['categories'],
            'priority': self.origin['default_priority'],
            self.CONVERSATION_ID: self.record['id'],
            self.SUBJECT: self.record['subject'],
            self.BODY: self.record['body'],
            self.URL: self.record['url'],
            self.PREVIEW: self.record['preview'],
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['subject'],
            url=self.record['url'],
            number=self.record['id'],
            cls='issue',
        )


class Outlook365Service(IssueService):
    APPLICATION_NAME = 'Bugwarrior Outlook 365 Service'
    SCOPES = ['basic', 'mailbox']
    DEFAULT_SECRETS_PATH = '~/.o365_client_secrets.json'
    DEFAULT_AUTHTOKEN_PATH = '~/.o365_authtoken.json'

    ISSUE_CLASS = Outlook365Issue
    CONFIG_PREFIX = 'outlook365'

    def __init__(self, *args, **kw):
        super(Outlook365Service, self).__init__(*args, **kw)

        self.query = self.config.get('query', 'isFlagged:true')
        self.account = self.get_account()

    def get_account(self):
        secrets_path = self.get_config_path('client_secret_path', self.DEFAULT_SECRETS_PATH)
        log.debug("Loading client secrets from {0}".format(secrets_path))
        secrets = json.loads(open(secrets_path, 'r').read())
        token_path = self.get_config_path('authtoken_path', self.DEFAULT_AUTHTOKEN_PATH)
        log.debug("Using {0} for auttoken storage".format(token_path))
        if os.path.isfile(token_path):
            log.debug("Token file {0} exists".format(token_path))
        token_dir, token_filename = os.path.dirname(token_path), os.path.basename(token_path)
        # The FileSystemTokenBackend expects a directory and a filename separately
        token_backend = FileSystemTokenBackend(token_path=token_dir, token_filename=token_filename)
        return Account(
            (secrets['client_id'], secrets['client_secret']),
            token_backend=token_backend,
        )

    def get_config_path(self, varname, default_path):
        return os.path.expanduser(self.config.get(varname, default_path))

    def issues(self):
        if not self.account.is_authenticated:
            # start the console based authentication
            self.account.authenticate(scopes=self.SCOPES)

        mailbox = self.account.mailbox()
        messages = mailbox.get_messages(query=mailbox.q().search(self.query))
        for msg in messages:
            issue = self.get_issue_for_record(to_record(msg))
            yield issue


def to_record(outlookMessage):
    return {
        'subject': outlookMessage.subject,
        'body': outlookMessage.get_body_text(),
        'preview': outlookMessage.body_preview,
        'created': outlookMessage.received,
        'id': outlookMessage.conversation_id,
        'categories': outlookMessage.categories,
        'url': outlookMessage.web_link,
    }
