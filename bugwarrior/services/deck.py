from collections.abc import Iterator
import datetime
import logging
import typing
from typing import Any

from pydantic import Field
import requests

from bugwarrior import config
from bugwarrior.services import Client, Issue, Service
from bugwarrior.task import Task, Udas

log = logging.getLogger(__name__)


class NextcloudDeckConfig(config.ServiceConfig):
    service: typing.Literal['deck']
    KEYRING_SERVICE = 'deck://{username}@{base_uri}'
    base_uri: config.StrippedTrailingSlashUrl
    username: str

    # can be a password or an app-password
    password: str

    include_board_ids: config.ConfigList = []
    exclude_board_ids: config.ConfigList = []

    import_labels_as_tags: bool = False
    label_template: str = '{{label}}'


# relevant API docs can be found here: https://deck.readthedocs.io/en/latest/API/
# * Boards will be mapped to projects
# * Stacks will be mapped to an UDA
# * Cards will be mapped to tasks
# * Labels will be mapped to tags
class NextcloudDeckClient(Client):
    def __init__(self, base_uri: str, username: str, password: str) -> None:
        self.api_base_path = f'{base_uri}/index.php/apps/deck/api/v1.0'
        self.ocs_base_path = f'{base_uri}/ocs/v2.php/apps/deck/api/v1.0'

        self.session = requests.session()
        self.session.auth = (username, password)
        self.session.headers.update(
            {'Accept': 'application/json', 'OCS-APIRequest': 'true'}
        )

    # see https://deck.readthedocs.io/en/latest/API/#boards for API docs
    def get_boards(self) -> list[dict[str, Any]]:
        response = self.session.get(f'{self.api_base_path}/boards')
        return response.json()

    # see https://deck.readthedocs.io/en/latest/API/#stacks for API docs
    def get_stacks(self, board_id: int) -> list[dict[str, Any]]:
        response = self.session.get(f'{self.api_base_path}/boards/{board_id}/stacks')
        return response.json()

    # see https://deck.readthedocs.io/en/latest/API/#comments for API docs
    def get_comments(self, card_id: int) -> dict[str, Any]:
        response = self.session.get(
            f'{self.ocs_base_path}/cards/{card_id}/comments?limit=100&offset=0'
        )
        return response.json()


class NextcloudDeckUdas(Udas):
    """Service-specific UDAs contributed by Nextcloud Deck."""

    UNIQUE_KEY = ('nextclouddeckboardid', 'nextclouddeckstackid', 'nextclouddeckcardid')

    nextclouddeckauthor: str = Field(title='Nextcloud Deck Issue Author')
    nextclouddeckboardid: int = Field(title='Nextcloud Deck Board ID')
    nextclouddeckboardtitle: str = Field(title='Nextcloud Deck Board Title')
    nextclouddeckstackid: int = Field(title='Nextcloud Deck Stack ID')
    nextclouddeckstacktitle: str = Field(title='Nextcloud Deck Stack Title')
    nextclouddeckcardid: int = Field(title='Nextcloud Deck Card ID')
    nextclouddeckcardtitle: str = Field(title='Nextcloud Deck Card Title')
    nextclouddeckdescription: str | None = Field(
        title='Nextcloud Deck Card Description'
    )
    nextclouddeckorder: int = Field(title='Nextcloud Deck Order')
    nextclouddeckassignee: str | None = Field(title='Nextcloud Deck Assignee(s)')


class NextcloudDeckTask(Task):
    udas: NextcloudDeckUdas


class NextcloudDeckIssue(Issue):
    PRIORITY_MAP = {}  # FIXME

    def to_taskwarrior(self) -> NextcloudDeckTask:
        return NextcloudDeckTask(
            project=self.extra['board']['title'].lower().replace(' ', '_'),
            priority=self.get_priority(),
            annotations=self.extra['annotations'],
            tags=self.get_tags(),
            entry=datetime.datetime.fromtimestamp(
                self.record['createdAt'], tz=datetime.timezone.utc
            ),
            due=self.record.get('duedate'),
            udas=NextcloudDeckUdas(
                nextclouddeckauthor=self.record['owner']['uid'],
                nextclouddeckboardid=self.extra['board']['id'],
                nextclouddeckboardtitle=self.extra['board']['title'],
                nextclouddeckstackid=self.extra['stack']['id'],
                nextclouddeckstacktitle=self.extra['stack']['title'],
                nextclouddeckcardid=self.record['id'],
                nextclouddeckcardtitle=self.record['title'],
                nextclouddeckdescription=self.record['description'],
                nextclouddeckorder=self.record['order'],
                nextclouddeckassignee=(
                    self.record['assignedUsers'][0]['participant']['uid']
                    if self.record['assignedUsers']
                    else None
                ),
            ),
        )

    def get_tags(self) -> list[str]:
        return self.get_tags_from_labels(
            [label['title'] for label in self.record['labels']]
        )

    def get_default_description(self) -> str:
        return self.build_default_description(title=self.record['title'])


class NextcloudDeckService(Service):
    API_VERSION = 2.0
    ISSUE_CLASS = NextcloudDeckIssue
    TASK_SCHEMA = NextcloudDeckTask
    CONFIG_SCHEMA = NextcloudDeckConfig

    def __init__(
        self, config: NextcloudDeckConfig, main_config: config.MainSectionConfig
    ) -> None:
        super().__init__(config, main_config)

        self.client = NextcloudDeckClient(
            base_uri=self.config.base_uri,
            username=self.config.username,
            password=self.config.password,
        )

    def get_owner(self, card: dict[str, Any]) -> str | None:
        if card.get('assignedUsers'):
            return card['assignedUsers'][0]['participant']['uid']
        return None

    def include(self, card: dict[str, Any]) -> bool:
        """Return true if the card in question should be included"""
        if self.config.only_if_assigned:
            owner = self.get_owner(card)
            include_owners: list[str | None] = [self.config.only_if_assigned]

            if self.config.also_unassigned:
                include_owners.append(None)

            return owner in include_owners

        return True

    def filter_boards(self, board: dict[str, Any]) -> bool:
        # include_board_ids takes precedence over exclude_board_ids
        if self.config.include_board_ids:
            return str(board['id']) in self.config.include_board_ids
        if self.config.exclude_board_ids:
            return str(board['id']) not in self.config.exclude_board_ids
        # no filters defined: then it's included
        return True

    def annotations(self, card: dict[str, Any]) -> list[str]:
        comments = (
            self.client.get_comments(card['id'])['ocs']['data']
            if self.main_config.annotation_comments
            else []
        )
        return self.build_annotations(
            ((comment['actorDisplayName'], comment['message']) for comment in comments)
        )

    def issues(self) -> Iterator[Task]:
        for board in self.client.get_boards():
            if self.filter_boards(board):
                for stack in self.client.get_stacks(board['id']):
                    for card in stack.get('cards', []):
                        extra = {
                            'board': board,
                            'stack': stack,
                            'annotations': self.annotations(card),
                        }
                        if self.include(card):
                            yield self.process_record(card, extra)
