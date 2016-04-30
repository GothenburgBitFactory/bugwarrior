import json

import responses

from bugwarrior.services.gerrit import GerritService
from .base import ServiceTest


class TestGerritIssue(ServiceTest):
    SERVICE_CONFIG = {
        'gerrit.base_uri': 'https://one',
        'gerrit.username': 'two',
        'gerrit.password': 'three',
    }

    record = {
        'project': 'nova',
        '_number': 1,
        'subject': 'this is a title',
        'messages': [{'author': {'username': 'Iam Author'},
                      'message': 'this is a message',
                      '_revision_number': 1}],
    }

    def setUp(self):
        self.service = self.get_mock_service(GerritService)

    def test_to_taskwarrior(self):
        extra = {
            'annotations': [
                # TODO - test annotations?
            ],
            'url': 'this is a url',
        }

        issue = self.service.get_issue_for_record(self.record, extra)
        actual = issue.to_taskwarrior()
        expected = {
            'annotations': [],
            'priority': 'M',
            'project': 'nova',
            'gerritid': 1,
            'gerritsummary': 'this is a title',
            'gerriturl': 'this is a url',
            'tags': [],
        }

        self.assertEqual(actual, expected)

    @responses.activate
    def test_issues(self):
        responses.add(
            responses.GET,
            'https://one/a/changes/?q=is:open+is:reviewer&o=MESSAGES&o=DETAILED_ACCOUNTS',
            match_querystring=True,
            # The response has some ")]}'" garbage prefixed.
            body=")]}'" + json.dumps([self.record]))

        issue = next(self.service.issues())

        expected = [
            ('project', u'nova'),
            ('description',
             u'(bw)PR#1 - this is a title .. https://one/#/c/1/'),
            ('tags', []),
            ('gerritsummary', u'this is a title'),
            ('gerriturl', 'https://one/#/c/1/'),
            ('priority', 'M'),
            ('gerritid', 1),
            ('annotations', [u'@Iam Author - is is a message'])]

        self.assertEqual(issue.items(), expected)
