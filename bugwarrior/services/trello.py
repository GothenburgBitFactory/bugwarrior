"""
Trello service

Pulls trello cards as tasks.

Trello API documentation available at https://developers.trello.com/
"""
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from six.moves.configparser import NoOptionError

from jinja2 import Template
import requests

from bugwarrior.services import IssueService, Issue, ServiceClient
from bugwarrior.config import die, asbool, aslist

DEFAULT_LABEL_TEMPLATE = "{{label|replace(' ', '_')}}"


class TrelloIssue(Issue):
    NAME = 'trellocard'
    CARDID = 'trellocardid'
    BOARD = 'trelloboard'
    LIST = 'trellolist'
    SHORTLINK = 'trelloshortlink'
    SHORTURL = 'trelloshorturl'
    URL = 'trellourl'

    UDAS = {
        NAME: {'type': 'string', 'label': 'Trello card name'},
        CARDID: {'type': 'string', 'label': 'Trello card ID'},
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

    def get_tags(self, twdict):
        tmpl = Template(
            self.origin.get('label_template', DEFAULT_LABEL_TEMPLATE))
        return [tmpl.render(twdict, label=label['name'])
                for label in self.record['labels']]

    def to_taskwarrior(self):
        twdict = {
            'project': self.extra['boardname'],
            'due': self.parse_date(self.record['due']),
            'priority': self.origin['default_priority'],
            self.NAME: self.record['name'],
            self.CARDID: self.record['id'],
            self.BOARD: self.extra['boardname'],
            self.LIST: self.extra['listname'],
            self.SHORTLINK: self.record['shortLink'],
            self.SHORTURL: self.record['shortUrl'],
            self.URL: self.record['url'],
            'annotations': self.extra.get('annotations', []),
        }
        if self.origin['import_labels_as_tags']:
            twdict['tags'] = self.get_tags(twdict)
        return twdict


class TrelloService(IssueService, ServiceClient):
    ISSUE_CLASS = TrelloIssue
    # What prefix should we use for this service's configuration values
    CONFIG_PREFIX = 'trello'

    @classmethod
    def validate_config(cls, service_config, target):
        def check_key(opt):
            """ Check that the given key exist in the configuration  """
            if opt not in service_config:
                die("[{}] has no 'trello.{}'".format(target, opt))
        super(TrelloService, cls).validate_config(service_config, target)
        check_key('token')
        check_key('api_key')

    def get_service_metadata(self):
        """
        Return extra config options to be passed to the TrelloIssue class
        """
        return {
            'import_labels_as_tags':
            self.config.get('import_labels_as_tags', False, asbool),
            'label_template':
            self.config.get('label_template', DEFAULT_LABEL_TEMPLATE),
            }

    def issues(self):
        """
        Returns a list of dicts representing issues from a remote service.
        """
        for board in self.get_boards():
            for lst in self.get_lists(board['id']):
                listextra = dict(boardname=board['name'], listname=lst['name'])
                for card in self.get_cards(lst['id']):
                    issue = self.get_issue_for_record(card, extra=listextra)
                    issue.update_extra({"annotations": self.annotations(card)})
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
        if 'include_boards' in self.config:
            for boardid in self.config.get('include_boards', to_type=aslist):
                # Get the board name
                yield self.api_request(
                    "/1/boards/{id}".format(id=boardid), fields='name')
        else:
            boards = self.api_request("/1/members/me/boards", fields='name')
            for board in boards:
                yield board

    def get_lists(self, board):
        """
        Returns a list of the filtered lists for the given board
        This filters the trello lists according to the configuration values of
        trello.include_lists and trello.exclude_lists.
        """
        lists = self.api_request(
            "/1/boards/{board_id}/lists/open".format(board_id=board),
            fields='name')

        include_lists = self.config.get('include_lists', to_type=aslist)
        if include_lists:
            lists = [l for l in lists if l['name'] in include_lists]

        exclude_lists = self.config.get('exclude_lists', to_type=aslist)
        if exclude_lists:
            lists = [l for l in lists if l['name'] not in exclude_lists]

        return lists

    def get_cards(self, list_id):
        """ Returns an iterator for the cards in a given list, filtered
        according to configuration values of trello.only_if_assigned and
        trello.also_unassigned """
        params = {'fields': 'name,idShort,shortLink,shortUrl,url,labels,due'}
        member = self.config.get('only_if_assigned', None)
        unassigned = self.config.get('also_unassigned', False, asbool)
        if member is not None:
            params['members'] = 'true'
            params['member_fields'] = 'username'
        cards = self.api_request(
            "/1/lists/{list_id}/cards/open".format(list_id=list_id),
            **params)
        for card in cards:
            if (member is None
                    or member in [m['username'] for m in card['members']]
                    or (unassigned and not card['members'])):
                yield card

    def get_comments(self, card_id):
        """ Returns an iterator for the comments on a certain card. """
        params = {'filter': 'commentCard', 'memberCreator_fields': 'username'}
        comments = self.api_request(
            "/1/cards/{card_id}/actions".format(card_id=card_id),
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
        params['key'] = self.config.get('api_key'),
        params['token'] = self.config.get('token'),
        url = "https://api.trello.com" + url
        return self.json_response(requests.get(url, params=params))
