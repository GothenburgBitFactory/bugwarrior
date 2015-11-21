from ConfigParser import NoOptionError
import re

import requests

from bugwarrior.services import IssueService, Issue
from bugwarrior.config import die


class TrelloIssue(Issue):
    NAME = 'trelloname'
    ID = 'trelloid'
    BOARD = 'trelloboard'
    LIST = 'trellolist'
    SHORTLINK = 'trelloshortlink'
    SHORTURL = 'trelloshorturl'
    URL = 'trellourl'

    UDAS = {
        NAME: {'type': 'string', 'label': 'Trello Name'},
        ID: {'type': 'string', 'label': 'Trello ID'},
        BOARD: {'type': 'string', 'label': 'Trello Board'},
        LIST: {'type': 'string', 'label': 'Trello List'},
        SHORTLINK: {'type': 'string', 'label': 'Trello Shortlink'},
        SHORTURL: {'type': 'string', 'label': 'Trello Shorturl'},
        URL: {'type': 'string', 'label': 'Trello URL'},
    }
    UNIQUE_KEY = (ID,)

    def get_default_description(self):
        """ Return the old-style verbose description from bugwarrior.
        """
        return self.build_default_description(
            title=self.record['name'],
            url=self.record['shortUrl'],
            number=self.record['idShort'],
            cls='task',
        )

    def to_taskwarrior(self):
        return {
            'project': self.extra['boardname'],
            'priority': 'M',
            self.NAME: self.record['name'],
            self.ID: self.record['id'],
            self.BOARD: self.extra['boardname'],
            self.LIST: self.extra['listname'],
            self.SHORTLINK: self.record['shortLink'],
            self.SHORTURL: self.record['shortUrl'],
            self.URL: self.record['url'],
        }

    def _sluggify(self, s):
        """
        Sluggify a string: remove spaces and non ascii alphanumeric characters
        """
        return re.sub(r'[^a-zA-Z0-9]', '_', s)


class TrelloService(IssueService):
    ISSUE_CLASS = TrelloIssue
    # What prefix should we use for this service's configuration values
    CONFIG_PREFIX = 'trello'

    @classmethod
    def validate_config(cls, config, target):
        def check_key(opt):
            key = cls._get_key(opt)
            if not config.has_option(target, key):
                die("[{}] has no '{}'".format(target, key))

        check_key('token')
        check_key('api_key')
        check_key('board')

        super(TrelloService, cls).validate_config(config, target)

    def issues(self):
        """
        Returns a list of dicts representing issues from a remote service.
        """
        # First, we get the board meta-data and the open lists
        board = self.api_request(
            "/1/boards/{board_id}".format(board_id=self.config_get('board')),
            fields='name', lists='open', list_fiels='name')
        lists = self.filter_lists(board['lists'])
        # For each of the remaining lists, we get the open cards
        for list in lists:
            listextra = dict(boardname=board['name'], listname=list['name'])
            cards = self.api_request(
                "/1/lists/{list_id}/cards/open".format(list_id=list['id']),
                fields='name,idShort,shortLink,shortUrl,url')
            for card in cards:
                yield self.get_issue_for_record(card, extra=listextra)

    def filter_lists(self, lists):
        """
        This filters the trello lists according to the configuration values of
        trello.include_lists and trello.exclude_lists.
        """
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
