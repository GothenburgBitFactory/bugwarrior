import os.path
import pickle
from copy import copy
from datetime import datetime, timedelta
from unittest import mock
from unittest.mock import patch

import responses

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
        "description": "Minimum task",
        "uuid": "9ce52fe2-ec48-000d-ba00-c30f463fc422"
    }
]

MIN_TASK = {
    'priority': u'L',
    'project': 'IDK',
    'tags': ['add', 'tags'],
    "entry": None,
    'description': 'Minimum task',
    'http_uuid': '9ce52fe2-ec48-000d-ba00-c30f463fc422',
    'http_url': 'https://example.com/tasks'
};

MAX_TASK = {
    'description': 'Attempting to scare those annoying cats away',
    'entry': datetime(2020, 7, 9, 14, 19, 33, tzinfo=tzutc()),
    'tags': ['home', 'garden', 'add', 'tags'],
    'project': 'AnnoyingCats',
    'priority': u'H',
    'http_uuid': '8ce52fe2-ec48-489d-ba00-c30f463fc422',
    'http_url': 'https://example.com/tasks'
}

class TestHttpIssue(AbstractServiceTest, ServiceTest):
    maxDiff = None
    SERVICE_CONFIG = {
        'http.url': 'https://example.com/tasks',
        'http.add_tags': "add,tags",
        'http.project_name': 'IDK',
        'http.default_priority': "L"
    }

    def setUp(self):
        super(TestHttpIssue, self).setUp()

        self.service = self.get_mock_service(HttpService, section='test_section')

    @responses.activate
    def test_issues(self):
        """
        Test: conversion from HTTP to taskwarrior tasks.
        """
        responses.add(
            responses.GET,
            'https://example.com/tasks',
            json=TEST_RESPONSE,
            status=200
        )

        self.assertEqual(self.service.request(), TEST_RESPONSE)

        issues = [ issue.get_taskwarrior_record() for issue in self.service.issues() ]

        self.assertEqual(issues[0], MAX_TASK)
        self.assertEqual(issues[1], MIN_TASK)

        """

        responses.add(
            responses.GET,
            'https://example.com/tasks',
            json=TEST_RESPONSE,
            status=200
        )

        issues = list(self.service.issues())

        print(issues)

        self.assertEqual(len(issues), 2)

        self.assertTrue(MAX_TASK in issues)
        self.assertEqual(issues[1], MIN_TASK)
        """

    def test_to_taskwarrior(self):
        issue = self.service.convert_to_issue(TEST_RESPONSE[0])

        taskwarrior = issue.get_taskwarrior_record()

        self.assertEqual(taskwarrior, MAX_TASK)