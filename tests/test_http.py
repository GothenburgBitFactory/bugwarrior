import os.path
import pickle
from copy import copy
from datetime import datetime, timedelta
from unittest import mock
from unittest.mock import patch

from dateutil.tz import tzutc
from six.moves import configparser

import bugwarrior.services.http as http
from bugwarrior.config import ServiceConfig
from bugwarrior.services.http import HttpService

from .base import AbstractServiceTest, ConfigTest, ServiceTest


TEST_RESPONSE = [
	{
		"tags": ["home", "garden"],
		"entry": "20200709T141933Z",
		"description": "Attempting to scare those annoying cats away",
		"uuid": "8ce52fe2-ec48-489d-ba00-c30f463fc422",
		"modified": "20200709T141933Z",
		"project": "AnnoyingCats",
        "priority": "H"
	},
    {
        "description": "Miniumum task",
        "uuid": "9ce52fe2-ec48-000d-ba00-c30f463fc422"
    }
]

class TestHttpIssue(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        'http.url': 'https://example.com/tasks',
        'http.add_tags': "add,tags",
        'http.default_project': 'IDK',
        'http.default_priority': "L"
    }

    def setUp(self):
        super(TestHttpIssue, self).setUp()

        mock_api = mock.Mock()
        mock_api().execute.return_value = TEST_RESPONSE
        HttpService.request = mock_api
        self.service = self.get_mock_service(HttpService, section='test_section')

    def test_to_taskwarrior_minimum(self):
        issue = self.service.convert_to_issue(TEST_RESPONSE[1])

        expected = {
            'priority': u'L',
            'project': 'IDK',
            'tags': {'add', 'tags'},
            'description': 'Minimum task',
            'http_uuid': '9ce52fe2-ec48-000d-ba00-c30f463fc422',
            'http_url': 'https://example.com/tasks'
        }

    def test_to_taskwarrior(self):
        issue = self.service.convert_to_issue(TEST_RESPONSE[0])

        expected = {
            'description': 'Attempting to scare those annoying cats away',
            'entry': "20200709T141933Z",
            'modified': "20200709T141933Z",
            'tags': {'home', 'garden', 'add', 'tags'},
            'project': 'AnnoyingCats',
            'priority': u'H',
            'http_uuid': '8ce52fe2-ec48-489d-ba00-c30f463fc422',
            'http_url': 'https://example.com/tasks'
        }

        taskwarrior = issue.to_taskwarrior()
        taskwarrior['tags'] = set(taskwarrior['tags'])

        self.assertEqual(taskwarrior, expected)