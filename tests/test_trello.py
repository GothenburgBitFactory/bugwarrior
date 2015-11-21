from __future__ import unicode_literals, print_function

import ConfigParser
import unittest2
from mock import patch

from bugwarrior.services.trello import TrelloService, TrelloIssue
from .base import ServiceTest


def mkConfig(data):
    """ Create a configuration object to use in tests """
    config = ConfigParser.RawConfigParser()
    for section in data:
        config.add_section(section)
        for opt in data[section]:
            config.set(section, opt, data[section][opt])
    return config


class MkConfigTest(unittest2.TestCase):
    """ Test the mkConfig test utility """

    def setUp(self):
        self.testconf = mkConfig({'mysection': {'foo': 'bar'}})

    def test_section(self):
        conf = mkConfig({'mysection': {'foo': 'bar', 'fooo': 'baar'}})
        self.assertTrue(conf.has_section('mysection'))

    def test_option(self):
        self.assertTrue(self.testconf.has_option('mysection', 'foo'))
        self.assertEqual(self.testconf.get('mysection', 'foo'), 'bar')


class ValidateConfigTest(unittest2.TestCase):

    def setUp(self):
        self.arbitrary_config = mkConfig({'mytrello': {
            'trello.token': 'aaaabbbbccccddddeeeeffff',
            'trello.api_key': '000011112222333344445555',
            'trello.board': 'foobar',
        }})

    @patch('bugwarrior.services.trello.die')
    def test_valid_config(self, die):
        TrelloService.validate_config(self.arbitrary_config, 'mytrello')
        die.assert_not_called()

    @patch('bugwarrior.services.trello.die')
    def test_no_access_token(self, die):
        self.arbitrary_config.remove_option('mytrello', 'trello.token')
        TrelloService.validate_config(self.arbitrary_config, 'mytrello')
        die.assert_called_with("[mytrello] has no 'trello.token'")

    @patch('bugwarrior.services.trello.die')
    def test_no_api_key(self, die):
        self.arbitrary_config.remove_option('mytrello', 'trello.api_key')
        TrelloService.validate_config(self.arbitrary_config, 'mytrello')
        die.assert_called_with("[mytrello] has no 'trello.api_key'")

    @patch('bugwarrior.services.trello.die')
    def test_no_board(self, die):
        self.arbitrary_config.remove_option('mytrello', 'trello.board')
        TrelloService.validate_config(self.arbitrary_config, 'mytrello')
        die.assert_called_with("[mytrello] has no 'trello.board'")


class TestTrelloIssue(ServiceTest):
    JSON = {
        "id": "542bbb6583d705eb05bbe491",
        "idShort": 42,
        "name": "So long, and thanks for all the fish!",
        "shortLink": "AAaaBBbb",
        "shortUrl": "https://trello.com/c/AAaaBBbb",
        "url": "https://trello.com/c/AAaBBbb/42-so-long",
        }

    def setUp(self):
        origin = dict(inline_links=True, description_length=31)
        extra = {'boardname': 'Hyperspatial express route'}
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
