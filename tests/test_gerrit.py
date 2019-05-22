from builtins import next
import json

import responses

from bugwarrior.services.gerrit import GerritService
from .base import ServiceTest, AbstractServiceTest


class TestGerritIssue(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        'gerrit.base_uri': 'https://one.com',
        'gerrit.username': 'two',
        'gerrit.password': 'three',
    }

    record = {
        'project': 'nova',
        '_number': 1,
        'branch': 'master',
        'topic': 'test-topic',
        'subject': 'this is a title',
        'messages': [{'author': {'username': 'Iam Author'},
                      'message': 'this is a message',
                      '_revision_number': 1}],
    }

    def setUp(self):
        super(TestGerritIssue, self).setUp()

        responses.add(
            responses.HEAD,
            self.SERVICE_CONFIG['gerrit.base_uri'] + '/a/',
            headers={'www-authenticate': 'digest'})
        with responses.mock:
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
            'gerritbranch': 'master',
            'gerrittopic': 'test-topic',
            'tags': [],
        }

        self.assertEqual(actual, expected)

    @responses.activate
    def test_issues(self):
        self.add_response(
            'https://one.com/a/changes/?q=is:open+is:reviewer&o=MESSAGES&o=DETAILED_ACCOUNTS',
            # The response has some ")]}'" garbage prefixed.
            body=")]}'" + json.dumps([self.record]))

        issue = next(self.service.issues())

        expected = {
            'annotations': [u'@Iam Author - is is a message'],
            'description': u'(bw)PR#1 - this is a title .. https://one.com/#/c/1/',
            'gerritid': 1,
            'gerritsummary': u'this is a title',
            'gerriturl': 'https://one.com/#/c/1/',
            'gerritbranch': 'master',
            'gerrittopic': 'test-topic',
            'priority': 'M',
            'project': u'nova',
            'tags': []}

        self.assertEqual(issue.get_taskwarrior_record(), expected)
