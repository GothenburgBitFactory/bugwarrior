from __future__ import unicode_literals
from ConfigParser import NoOptionError

from jinja2 import Template
import requests

from bugwarrior.services import IssueService, Issue
from bugwarrior.config import die, asbool

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
            'priority': 'M',
            self.NAME: self.record['name'],
            self.CARDID: self.record['id'],
            self.BOARD: self.extra['boardname'],
            self.LIST: self.extra['listname'],
            self.SHORTLINK: self.record['shortLink'],
            self.SHORTURL: self.record['shortUrl'],
            self.URL: self.record['url'],
        }
        if self.origin['import_labels_as_tags']:
            twdict['tags'] = self.get_tags(twdict)
        return twdict


class TrelloService(IssueService):
    ISSUE_CLASS = TrelloIssue
    # What prefix should we use for this service's configuration values
    CONFIG_PREFIX = 'trello'

    @classmethod
    def validate_config(cls, config, target):
        def check_key(opt):
            """ Check that the given key exist in the configuration  """
            key = cls._get_key(opt)
            if not config.has_option(target, key):
                die("[{}] has no '{}'".format(target, key))
        super(TrelloService, cls).validate_config(config, target)
        check_key('token')
        check_key('api_key')
        check_key('board')

    def get_service_metadata(self):
        """
        Return extra config options to be passed to the TrelloIssue class
        """
        return {
            'import_labels_as_tags':
            self.config_get_default('import_labels_as_tags', False, asbool),
            'label_template':
            self.config_get_default('label_template', DEFAULT_LABEL_TEMPLATE),
            }

    def issues(self):
        """
        Returns a list of dicts representing issues from a remote service.
        """
        # First, we get the board name
        board_id = self.config_get('board')
        board = self.api_request(
            "/1/boards/{board_id}".format(board_id=board_id), fields='name')
        for lst in self.get_lists(board_id):
            listextra = dict(boardname=board['name'], listname=lst['name'])
            for card in self.get_cards(lst['id']):
                yield self.get_issue_for_record(card, extra=listextra)

    def get_lists(self, board):
        """
        Returns a list of the filtered lists for the given board
        This filters the trello lists according to the configuration values of
        trello.include_lists and trello.exclude_lists.
        """
        lists = self.api_request(
            "/1/boards/{board_id}/lists/open".format(board_id=board),
            fields='name')
        try:
            include_lists = self.config_get_list('include_lists')
            lists = [l for l in lists if l['name'] in include_lists]
        except NoOptionError:
            pass
        try:
            exclude_lists = self.config_get_list('exclude_lists')
            lists = [l for l in lists if l['name'] not in exclude_lists]
        except NoOptionError:
            pass
        return lists

    def get_cards(self, list_id):
        """ Returns an iterator for the cards in a given list, filtered
        according to configuration value trello.only_if_member """
        params = {'fields': 'name,idShort,shortLink,shortUrl,url,labels'}
        member = self.config_get_default('only_if_member', None)
        if member is not None:
            params['members'] = 'true'
            params['member_fields'] = 'username'
        cards = self.api_request(
            "/1/lists/{list_id}/cards/open".format(list_id=list_id),
            **params)
        for card in cards:
            if (member is None
                    or member in [m['username'] for m in card['members']]):
                yield card

    def api_request(self, url, **params):
        """
        Make a trello API request. This takes an absolute url (without protocol
        and host) and a list of argumnets and return a GET request with the
        key and token from the configuration
        """
        params['key'] = self.config_get('api_key'),
        params['token'] = self.config_get('token'),
        url = "https://api.trello.com" + url
        return requests.get(url, params=params).json()

    def config_get_list(self, key):
        """ Helper function similar to config_get but parse the resulting
        string into a list by splitting on commas """
        return [
            item.strip() for item in self.config_get(key).strip().split(',')]
