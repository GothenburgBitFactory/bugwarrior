"""
Trello service

Pulls trello cards as tasks.

Trello API documentation available at https://developers.trello.com/
"""

from collections.abc import Iterator
import typing
from typing import Any

from pydantic import Field
import requests

from bugwarrior import config
from bugwarrior.services import Client, Issue, Service
from bugwarrior.task import Task, Udas


class TrelloConfig(config.ServiceConfig):
    service: typing.Literal['trello']
    KEYRING_SERVICE = "trello://{api_key}@trello.com"
    api_key: str
    token: str

    include_boards: config.ConfigList = []
    include_lists: config.ConfigList = []
    exclude_lists: config.ConfigList = []
    import_labels_as_tags: bool = False
    label_template: str = "{{label|replace(' ', '_')}}"


class TrelloUdas(Udas):
    """Service-specific UDAs contributed by Trello."""

    UNIQUE_KEY = ('trellocardid',)

    trellocard: str = Field(title='Trello card name')
    trellocardid: str = Field(title='Trello card ID')
    trellocardidshort: int = Field(title='Trello short card ID')
    trellodescription: str | None = Field(title='Trello description')
    trelloboard: str = Field(title='Trello board name')
    trellolist: str = Field(title='Trello list name')
    trelloshortlink: str = Field(title='Trello shortlink')
    trelloshorturl: str = Field(title='Trello short URL')
    trellourl: str = Field(title='Trello URL')


class TrelloTask(Task):
    udas: TrelloUdas


class TrelloIssue(Issue):
    def get_default_description(self) -> str:
        """Return the old-style verbose description from bugwarrior."""
        return self.build_default_description(
            title=self.record['name'],
            url=self.record['shortUrl'],
            number=self.record['idShort'],
            cls='task',
        )

    def get_tags(self) -> list[str]:
        return self.get_tags_from_labels(
            [label['name'] for label in self.record['labels']]
        )

    def to_taskwarrior(self) -> TrelloTask:
        return TrelloTask(
            project=self.extra['boardname'],
            due=self.record['due'],
            priority=self.config.default_priority,
            tags=self.get_tags(),
            annotations=self.extra.get('annotations', []),
            udas=TrelloUdas(
                trellocard=self.record['name'],
                trellocardid=self.record['id'],
                trellocardidshort=self.record['idShort'],
                trellodescription=self.record['desc'],
                trelloboard=self.extra['boardname'],
                trellolist=self.extra['listname'],
                trelloshortlink=self.record['shortLink'],
                trelloshorturl=self.record['shortUrl'],
                trellourl=self.record['url'],
            ),
        )


class TrelloService(Service):
    API_VERSION = 2.0
    ISSUE_CLASS = TrelloIssue
    TASK_SCHEMA = TrelloTask
    CONFIG_SCHEMA = TrelloConfig

    def issues(self) -> Iterator[Task]:
        """
        Returns a list of dicts representing issues from a remote service.
        """
        for board in self.get_boards():
            for lst in self.get_lists(board['id']):
                for card in self.get_cards(lst['id']):
                    extra = {
                        'boardname': board['name'],
                        'listname': lst['name'],
                        'annotations': self.annotations(card),
                    }
                    yield self.process_record(card, extra)

    def annotations(self, card_json: dict[str, Any]) -> list[str]:
        """A wrapper around get_comments that build the taskwarrior
        annotations."""
        comments = self.get_comments(card_json['id'])
        annotations = self.build_annotations(
            ((c['memberCreator']['username'], c['data']['text']) for c in comments),
            card_json["shortUrl"],
        )
        return annotations

    def get_boards(self) -> Iterator[dict[str, Any]]:
        """
        Get the list of boards to pull cards from.  If the user gave a value to
        trello.include_boards use that, otherwise ask the Trello API for the
        user's boards.
        """
        if self.config.include_boards:
            for boardid in self.config.include_boards:
                # Get the board name
                yield self.api_request(f"/1/boards/{boardid}", fields='name')

        else:
            boards = self.api_request("/1/members/me/boards", fields='name')
            yield from boards

    def get_lists(self, board: str) -> list[dict[str, Any]]:
        """
        Returns a list of the filtered lists for the given board
        This filters the trello lists according to the configuration values of
        trello.include_lists and trello.exclude_lists.
        """
        lists = self.api_request(f"/1/boards/{board}/lists/open", fields='name')

        if self.config.include_lists:
            lists = [lst for lst in lists if lst['name'] in self.config.include_lists]

        if self.config.exclude_lists:
            lists = [
                lst for lst in lists if lst['name'] not in self.config.exclude_lists
            ]

        return lists

    def get_cards(self, list_id: str) -> Iterator[dict[str, Any]]:
        """Returns an iterator for the cards in a given list, filtered
        according to configuration values of trello.only_if_assigned and
        trello.also_unassigned"""
        params = {'fields': 'name,idShort,shortLink,shortUrl,url,labels,due,desc'}
        if self.config.only_if_assigned:
            params['members'] = 'true'
            params['member_fields'] = 'username'
        cards = self.api_request(f"/1/lists/{list_id}/cards/open", **params)
        for card in cards:
            cardmembers = [m['username'] for m in card.get('members', [])]
            if (
                not self.config.only_if_assigned
                or self.config.only_if_assigned in cardmembers
                or (self.config.also_unassigned and not cardmembers)
            ):
                yield card

    def get_comments(self, card_id: str) -> Iterator[dict[str, Any]]:
        """Returns an iterator for the comments on a certain card."""
        params = {'filter': 'commentCard', 'memberCreator_fields': 'username'}
        comments = self.api_request(f"/1/cards/{card_id}/actions", **params)
        for comment in comments:
            assert comment['type'] == 'commentCard'
            yield comment

    def api_request(self, url: str, **params: Any) -> Any:
        """
        Make a trello API request. This takes an absolute url (without protocol
        and host) and a list of argumnets and return a GET request with the
        key and token from the configuration
        """
        params['key'] = self.config.api_key
        params['token'] = self.get_secret('token')
        url = "https://api.trello.com" + url
        return Client.json_response(requests.get(url, params=params))
