from __future__ import unicode_literals, print_function

import ConfigParser
import unittest2
from mock import patch

from bugwarrior.services.trello import TrelloService
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


class TestGitlabIssue(ServiceTest):
    pass

