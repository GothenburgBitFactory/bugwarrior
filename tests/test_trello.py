from __future__ import unicode_literals, print_function

import ConfigParser
from unittest import TestCase
from mock import patch
import responses

from bugwarrior.services.trello import TrelloService, TrelloIssue
from .base import ServiceTest


class TestTrelloIssue(ServiceTest):
    JSON = {
        "id": "542bbb6583d705eb05bbe491",
        "idShort": 42,
        "name": "So long, and thanks for all the fish!",
        "shortLink": "AAaaBBbb",
        "shortUrl": "https://trello.com/c/AAaaBBbb",
        "url": "https://trello.com/c/AAaBBbb/42-so-long",
        "labels": [{'name': "foo"}, {"name": "bar"}],
        }

    def setUp(self):
        origin = dict(inline_links=True, description_length=31,
                      import_labels_as_tags=True)
        extra = {'boardname': 'Hyperspatial express route',
                 'listname': 'Something'}
        self.issue = TrelloIssue(self.JSON, origin, extra)

    def test_default_description(self):
        """ Test the generated description """
        expected_desc = "(bw)#42 - So long, and thanks for all the" \
                        " .. https://trello.com/c/AAaaBBbb"
        self.assertEqual(expected_desc, self.issue.get_default_description())

    def test_to_taskwarrior__project(self):
        """ By default, the project is the board name """
        expected_project = "Hyperspatial express route"
        self.assertEqual(expected_project,
                         self.issue.to_taskwarrior().get('project', None))


class TestTrelloService(TestCase):
    BOARD = {'id': 'B04RD', 'name': 'My Board'}
    CARD1 = {'id': 'C1', 'name': 'Card 1', 'members': [{'username': 'tintin'}],
             'idShort': 1,
             'shortLink': 'abcd',
             'shortUrl': 'https://trello.com/c/AAaaBBbb',
             'url': 'https://trello.com/c/AAaBBbb/42-so-long'}
    CARD2 = {'id': 'C2', 'name': 'Card 2', 'members': [{'username': 'mario'}]}
    CARD3 = {'id': 'C3', 'name': 'Card 3', 'members': []}
    LIST1 = {'id': 'L15T', 'name': 'List 1'}
    LIST2 = {'id': 'ZZZZ', 'name': 'List 2'}

    def setUp(self):
        self.config = ConfigParser.RawConfigParser()
        self.config.add_section('mytrello')
        self.config.set('mytrello', 'trello.api_key', 'XXXX')
        self.config.set('mytrello', 'trello.token', 'YYYY')
        responses.add(responses.GET,
                      'https://api.trello.com/1/lists/L15T/cards/open',
                      json=[self.CARD1, self.CARD2, self.CARD3])
        responses.add(responses.GET,
                      'https://api.trello.com/1/boards/B04RD/lists/open',
                      json=[self.LIST1, self.LIST2])
        responses.add(responses.GET,
                      'https://api.trello.com/1/boards/F00',
                      json={'id': 'F00', 'name': 'Foo Board'})
        responses.add(responses.GET,
                      'https://api.trello.com/1/boards/B4R',
                      json={'id': 'B4R', 'name': 'Bar Board'})
        responses.add(responses.GET,
                      'https://api.trello.com/1/members/me/boards',
                      json=[self.BOARD])

    @responses.activate
    def test_get_boards_config(self):
        self.config.set('mytrello', 'trello.include_boards', 'F00, B4R')
        service = TrelloService(self.config, 'general', 'mytrello')
        boards = service.get_boards()
        self.assertEqual(list(boards), [{'id': 'F00', 'name': 'Foo Board'},
                                        {'id': 'B4R', 'name': 'Bar Board'}])

    @responses.activate
    def test_get_boards_api(self):
        service = TrelloService(self.config, 'general', 'mytrello')
        boards = service.get_boards()
        self.assertEqual(list(boards), [self.BOARD])

    @responses.activate
    def test_get_lists(self):
        service = TrelloService(self.config, 'general', 'mytrello')
        lists = service.get_lists('B04RD')
        self.assertEqual(list(lists), [self.LIST1, self.LIST2])

    @responses.activate
    def test_get_lists_include(self):
        self.config.set('mytrello', 'trello.include_lists', 'List 1')
        service = TrelloService(self.config, 'general', 'mytrello')
        lists = service.get_lists('B04RD')
        self.assertEqual(list(lists), [self.LIST1])

    @responses.activate
    def test_get_lists_exclude(self):
        self.config.set('mytrello', 'trello.exclude_lists', 'List 1')
        service = TrelloService(self.config, 'general', 'mytrello')
        lists = service.get_lists('B04RD')
        self.assertEqual(list(lists), [self.LIST2])

    @responses.activate
    def test_get_cards(self):
        service = TrelloService(self.config, 'general', 'mytrello')
        cards = service.get_cards('L15T')
        self.assertEqual(list(cards), [self.CARD1, self.CARD2, self.CARD3])

    @responses.activate
    def test_get_cards_member(self):
        self.config.set('mytrello', 'trello.only_if_assigned', 'tintin')
        service = TrelloService(self.config, 'general', 'mytrello')
        cards = service.get_cards('L15T')
        self.assertEqual(list(cards), [self.CARD1])

    @responses.activate
    def test_issues(self):
        self.config.set('mytrello', 'trello.include_lists', 'List 1')
        self.config.set('mytrello', 'trello.only_if_assigned', 'tintin')
        service = TrelloService(self.config, 'general', 'mytrello')
        issues = service.issues()
        expected = {
            'description': u'(bw)#1 - Card 1 .. https://trello.com/c/AAaaBBbb',
            'priority': 'M',
            'project': 'My Board',
            'trelloboard': 'My Board',
            'trellolist': 'List 1',
            'trellocard': 'Card 1',
            'trellocardid': 'C1',
            'trelloshortlink': 'abcd',
            'trelloshorturl': 'https://trello.com/c/AAaaBBbb',
            'trellourl': 'https://trello.com/c/AAaBBbb/42-so-long',
            'tags': []}
        actual = next(issues).get_taskwarrior_record()
        self.assertEqual(expected, actual)

    maxDiff = None

    @patch('bugwarrior.services.trello.die')
    def test_validate_config(self, die):
        TrelloService.validate_config(self.config, 'mytrello')
        die.assert_not_called()

    @patch('bugwarrior.services.trello.die')
    def test_valid_config_no_access_token(self, die):
        self.config.remove_option('mytrello', 'trello.token')
        TrelloService.validate_config(self.config, 'mytrello')
        die.assert_called_with("[mytrello] has no 'trello.token'")

    @patch('bugwarrior.services.trello.die')
    def test_valid_config_no_api_key(self, die):
        self.config.remove_option('mytrello', 'trello.api_key')
        TrelloService.validate_config(self.config, 'mytrello')
        die.assert_called_with("[mytrello] has no 'trello.api_key'")
