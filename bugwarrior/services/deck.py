import datetime
import logging

import requests
import typing_extensions
from dateutil.tz import tzutc

from bugwarrior import config
from bugwarrior.services import IssueService, Issue, ServiceClient

log = logging.getLogger(__name__)


class NextcloudDeckConfig(config.ServiceConfig, prefix='deck'):
    service: typing_extensions.Literal['deck']
    base_uri: config.StrippedTrailingSlashUrl
    username: str

    # can be a password or an app-password
    password: str

    include_board_ids: config.ConfigList = config.ConfigList([])
    exclude_board_ids: config.ConfigList = config.ConfigList([])

    import_labels_as_tags: bool = False
    label_template: str = '{{label}}'


# relevant API docs can be found here: https://deck.readthedocs.io/en/latest/API/
# * Boards will be mapped to projects
# * Stacks will be mapped to an UDA
# * Cards will be mapped to tasks
# * Labels will be mapped to tags
class NextcloudDeckClient(ServiceClient):
    def __init__(self, base_uri, username, password):
        self.api_base_path = f'{base_uri}/index.php/apps/deck/api/v1.0'
        self.ocs_base_path = f'{base_uri}/ocs/v2.php/apps/deck/api/v1.0'

        self.session = requests.session()
        self.session.auth = (username, password)
        self.session.headers.update({
            'Accept': 'application/json',
            'OCS-APIRequest': 'true',
        })

    # see https://deck.readthedocs.io/en/latest/API/#boards for API docs
    def get_boards(self):
        response = self.session.get(f'{self.api_base_path}/boards')
        return response.json()

    # see https://deck.readthedocs.io/en/latest/API/#stacks for API docs
    def get_stacks(self, board_id):
        response = self.session.get(
            f'{self.api_base_path}/boards/{board_id}/stacks'
        )
        return response.json()

    # see https://deck.readthedocs.io/en/latest/API/#comments for API docs
    def get_comments(self, card_id):
        response = self.session.get(
            f'{self.ocs_base_path}/cards/{card_id}/comments?limit=100&offset=0'
        )
        return response.json()


class NextcloudDeckIssue(Issue):
    AUTHOR = 'nextclouddeckauthor'
    BOARD_ID = 'nextclouddeckboardid'
    BOARD_TITLE = 'nextclouddeckboardtitle'
    STACK_ID = 'nextclouddeckstackid'
    STACK_TITLE = 'nextclouddeckstacktitle'
    CARD_ID = 'nextclouddeckcardid'
    TITLE = 'nextclouddeckcardtitle'
    DESCRIPTION = 'nextclouddeckdescription'
    ORDER = 'nextclouddeckorder'
    ASSIGNEE = 'nextclouddeckassignee'

    UDAS = {
        AUTHOR: {
            'type': 'string',
            'label': 'Nextcloud Deck Issue Author',
        },
        BOARD_ID: {
            'type': 'numeric',
            'label': 'Nextcloud Deck Board ID',
        },
        BOARD_TITLE: {
            'type': 'string',
            'label': 'Nextcloud Deck Board Title',
        },
        STACK_ID: {
            'type': 'numeric',
            'label': 'Nextcloud Deck Stack ID',
        },
        STACK_TITLE: {
            'type': 'string',
            'label': 'Nextcloud Deck Stack Title',
        },
        CARD_ID: {
            'type': 'numeric',
            'label': 'Nextcloud Deck Card ID',
        },
        TITLE: {
            'type': 'string',
            'label': 'Nextcloud Deck Card Title',
        },
        DESCRIPTION: {
            'type': 'string',
            'label': 'Nextcloud Deck Card Description',
        },
        ORDER: {
            'type': 'numeric',
            'label': 'Nextcloud Deck Order',
        },
        ASSIGNEE: {
            'type': 'string',
            'label': 'Nextcloud Deck Assignee(s)',
        }
    }

    UNIQUE_KEY = (BOARD_ID, STACK_ID, CARD_ID,)

    def to_taskwarrior(self):
        return {
            'project': self.extra['board']['title'].lower().replace(' ', '_'),
            'priority': self.get_priority(),
            'annotations': self.extra['annotations'],
            'tags': self.get_tags(),
            'entry': datetime.datetime.fromtimestamp(self.record.get('createdAt'), tz=tzutc()),
            'due': self.parse_date(self.record.get('duedate')),

            self.AUTHOR: self.record['owner']['uid'],
            self.BOARD_ID: self.extra['board']['id'],
            self.BOARD_TITLE: self.extra['board']['title'],
            self.STACK_ID: self.extra['stack']['id'],
            self.STACK_TITLE: self.extra['stack']['title'],
            self.CARD_ID: self.record['id'],
            self.TITLE: self.record['title'],
            self.DESCRIPTION: self.record['description'],
            self.ORDER: self.record['order'],
            self.ASSIGNEE:
                self.record['assignedUsers'][0]['participant']['uid']
                if self.record['assignedUsers'] else None,
        }

    def get_tags(self):
        return self.get_tags_from_labels([label['title'] for label in self.record['labels']])

    def get_default_description(self):
        return self.build_default_description(title=self.record['title'])


class NextcloudDeckService(IssueService):
    ISSUE_CLASS = NextcloudDeckIssue
    CONFIG_SCHEMA = NextcloudDeckConfig

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.client = NextcloudDeckClient(
            base_uri=self.config.base_uri,
            username=self.config.username,
            password=self.config.password
        )

    def get_service_metadata(self):
        return {
            'import_labels_as_tags': self.config.import_labels_as_tags,
            'label_template': self.config.label_template,
            'only_if_assigned': self.config.only_if_assigned,
        }

    def get_owner(self, issue):
        return issue[issue.ASSIGNEE]

    def filter_boards(self, board):
        # include_board_ids takes precedence over exclude_board_ids
        if self.config.include_board_ids:
            return str(board['id']) in self.config.include_board_ids
        if self.config.exclude_board_ids:
            return str(board['id']) not in self.config.exclude_board_ids
        # no filters defined: then it's included
        return True

    def annotations(self, card):
        comments = (self.client.get_comments(card['id'])['ocs']['data']
                    if self.main_config.annotation_comments else [])
        return self.build_annotations(
            ((
                comment['actorDisplayName'],
                comment['message'],
            ) for comment in comments))

    def issues(self):
        for board in self.client.get_boards():
            if self.filter_boards(board):
                for stack in self.client.get_stacks(board['id']):
                    for card in stack.get('cards', []):
                        extra = {
                            'board': board,
                            'stack': stack,
                            'annotations': self.annotations(card)
                        }
                        issue = self.get_issue_for_record(card, extra)
                        if self.include(issue):
                            yield issue
