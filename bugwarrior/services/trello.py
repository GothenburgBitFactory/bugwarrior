"""
Trello service

Pulls trello cards as tasks.

Trello API documentation available at https://developers.trello.com/
"""
import requests
import typing_extensions

from bugwarrior.services import Service, Issue, ServiceClient
from bugwarrior import config


class TrelloConfig(config.ServiceConfig):
    service: typing_extensions.Literal['trello']
    api_key: str
    token: str

    include_boards: config.ConfigList = config.ConfigList([])
    include_lists: config.ConfigList = config.ConfigList([])
    exclude_lists: config.ConfigList = config.ConfigList([])
    import_labels_as_tags: bool = False
    label_template: str = "{{label|replace(' ', '_')}}"


class TrelloIssue(Issue):
    NAME = 'trellocard'
    CARDID = 'trellocardid'
    SHORTCARDID = 'trellocardidshort'
    DESCRIPTION = 'trellodescription'
    BOARD = 'trelloboard'
    LIST = 'trellolist'
    SHORTLINK = 'trelloshortlink'
    SHORTURL = 'trelloshorturl'
    URL = 'trellourl'

    UDAS = {
        NAME: {'type': 'string', 'label': 'Trello card name'},
        CARDID: {'type': 'string', 'label': 'Trello card ID'},
        SHORTCARDID: {'type': 'numeric', 'label': 'Trello short card ID'},
        DESCRIPTION: {'type': 'string', 'label': 'Trello description'},
        BOARD: {'type': 'string', 'label': 'Trello board name'},
        LIST: {'type': 'string', 'label': 'Trello list name'},
        SHORTLINK: {'type': 'string', 'label': 'Trello shortlink'},
        SHORTURL: {'type': 'string', 'label': 'Trello short URL'},
        URL: {'type': 'string', 'label': 'Trello URL'},
    }
    UNIQUE_KEY = (CARDID,)

    def get_default_description(self):
        """ Return the old-style verbose description from bugwarrior.
        """
        return self.build_default_description(
            title=self.record['name'],
            url=self.record['shortUrl'],
            number=self.record['idShort'],
            cls='task',
        )

    def get_tags(self):
        return self.get_tags_from_labels(
            [label['name'] for label in self.record['labels']])

    def to_taskwarrior(self):
        return {
            'project': self.extra['boardname'],
            'due': self.parse_date(self.record['due']),
            'priority': self.config.default_priority,
            'tags': self.get_tags(),
            self.NAME: self.record['name'],
            self.CARDID: self.record['id'],
            self.SHORTCARDID: self.record['idShort'],
            self.DESCRIPTION: self.record['desc'],
            self.BOARD: self.extra['boardname'],
            self.LIST: self.extra['listname'],
            self.SHORTLINK: self.record['shortLink'],
            self.SHORTURL: self.record['shortUrl'],
            self.URL: self.record['url'],
            'annotations': self.extra.get('annotations', []),
        }


class TrelloService(Service, ServiceClient):
    ISSUE_CLASS = TrelloIssue
    CONFIG_SCHEMA = TrelloConfig

    def get_owner(self, issue):
        # Issue filtering is implemented as part of the api query.
        pass

    @staticmethod
    def get_keyring_service(config):
        return f"trello://{config.api_key}@trello.com"

    def issues(self):
        """
        Returns a list of dicts representing issues from a remote service.
        """
        for board in self.get_boards():
            for lst in self.get_lists(board['id']):
                listextra = dict(boardname=board['name'], listname=lst['name'])
                for card in self.get_cards(lst['id']):
                    issue = self.get_issue_for_record(card, extra=listextra)
                    issue.extra.update({"annotations": self.annotations(card)})
                    yield issue

    def annotations(self, card_json):
        """ A wrapper around get_comments that build the taskwarrior
        annotations. """
        comments = self.get_comments(card_json['id'])
        annotations = self.build_annotations(
            ((c['memberCreator']['username'], c['data']['text']) for c in comments),
            card_json["shortUrl"])
        return annotations

    def get_boards(self):
        """
        Get the list of boards to pull cards from.  If the user gave a value to
        trello.include_boards use that, otherwise ask the Trello API for the
        user's boards.
        """
        if self.config.include_boards:
            for boardid in self.config.include_boards:
                # Get the board name
                yield self.api_request(
                    f"/1/boards/{boardid}", fields='name')
        else:
            boards = self.api_request("/1/members/me/boards", fields='name')
            yield from boards

    def get_lists(self, board):
        """
        Returns a list of the filtered lists for the given board
        This filters the trello lists according to the configuration values of
        trello.include_lists and trello.exclude_lists.
        """
        lists = self.api_request(
            f"/1/boards/{board}/lists/open",
            fields='name')

        if self.config.include_lists:
            lists = [lst for lst in lists
                     if lst['name'] in self.config.include_lists]

        if self.config.exclude_lists:
            lists = [lst for lst in lists
                     if lst['name'] not in self.config.exclude_lists]

        return lists

    def get_cards(self, list_id):
        """ Returns an iterator for the cards in a given list, filtered
        according to configuration values of trello.only_if_assigned and
        trello.also_unassigned """
        params = {'fields': 'name,idShort,shortLink,shortUrl,url,labels,due,desc'}
        if self.config.only_if_assigned:
            params['members'] = 'true'
            params['member_fields'] = 'username'
        cards = self.api_request(
            f"/1/lists/{list_id}/cards/open",
            **params)
        for card in cards:
            cardmembers = [m['username'] for m in card['members']]
            if (not self.config.only_if_assigned
                    or self.config.only_if_assigned in cardmembers
                    or (self.config.also_unassigned and not cardmembers)):
                yield card

    def get_comments(self, card_id):
        """ Returns an iterator for the comments on a certain card. """
        params = {'filter': 'commentCard', 'memberCreator_fields': 'username'}
        comments = self.api_request(
            f"/1/cards/{card_id}/actions",
            **params)
        for comment in comments:
            assert comment['type'] == 'commentCard'
            yield comment

    def api_request(self, url, **params):
        """
        Make a trello API request. This takes an absolute url (without protocol
        and host) and a list of argumnets and return a GET request with the
        key and token from the configuration
        """
        params['key'] = self.config.api_key,
        params['token'] = self.get_password('token'),
        url = "https://api.trello.com" + url
        return self.json_response(requests.get(url, params=params))
