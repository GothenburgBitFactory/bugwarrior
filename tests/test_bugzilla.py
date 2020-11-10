import datetime
from builtins import next
from builtins import object
from unittest import mock
from collections import namedtuple
from six.moves import configparser

from bugwarrior.services.bz import BugzillaService

from .base import ConfigTest, ServiceTest, AbstractServiceTest
from bugwarrior.config import ServiceConfig


class FakeBugzillaLib(object):
    def __init__(self, records):
        self.records = records

    def query(self, query):
        return [namedtuple('Record', list(record.keys()))(**record)
                for record in self.records]


class TestBugzillaServiceConfig(ConfigTest):

    def setUp(self):
        super(TestBugzillaServiceConfig, self).setUp()
        self.config = configparser.RawConfigParser()
        self.config.add_section('general')
        self.config.add_section('mybz')
        self.service_config = ServiceConfig(
            BugzillaService.CONFIG_PREFIX, self.config, 'mybz')

    @mock.patch('bugwarrior.services.bz.die')
    def test_validate_config_username_password(self, die):
        self.config.set('mybz', 'bugzilla.base_uri', 'http://one.com/')
        self.config.set('mybz', 'bugzilla.username', 'me')
        self.config.set('mybz', 'bugzilla.password', 'mypas')
        BugzillaService.validate_config(self.service_config, 'mybz')
        die.assert_not_called()

    @mock.patch('bugwarrior.services.bz.die')
    def test_validate_config_api_key(self, die):
        self.config.set('mybz', 'bugzilla.base_uri', 'http://one.com/')
        self.config.set('mybz', 'bugzilla.username', 'me')
        self.config.set('mybz', 'bugzilla.api_key', '123')
        BugzillaService.validate_config(self.service_config, 'mybz')
        die.assert_not_called()

    @mock.patch('bugwarrior.services.bz.die')
    def test_validate_config_api_key_no_username(self, die):
        self.config.set('mybz', 'bugzilla.base_uri', 'http://one.com/')
        self.config.set('mybz', 'bugzilla.api_key', '123')
        BugzillaService.validate_config(self.service_config, 'mybz')
        die.assert_called_with("[mybz] has no 'bugzilla.username'")


class TestBugzillaService(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        'bugzilla.base_uri': 'http://one.com/',
        'bugzilla.username': 'hello',
        'bugzilla.password': 'there',
    }

    arbitrary_record = {
        'product': 'Product',
        'component': 'Something',
        'priority': 'urgent',
        'status': 'NEW',
        'summary': 'This is the issue summary',
        'id': 1234567,
        'flags': [],
        'assigned_to': None,
    }

    arbitrary_datetime = datetime.datetime.now(tz=datetime.timezone.utc)

    def setUp(self):
        super(TestBugzillaService, self).setUp()
        with mock.patch('bugzilla.Bugzilla'):
            self.service = self.get_mock_service(BugzillaService)

    def get_mock_service(self, *args, **kwargs):
        service = super(TestBugzillaService, self).get_mock_service(
            *args, **kwargs)
        service.bz = FakeBugzillaLib([self.arbitrary_record])
        service._get_assigned_date = (
            lambda issues: self.arbitrary_datetime.isoformat())
        return service

    def test_api_key_supplied(self):
        with mock.patch('bugzilla.Bugzilla'):
            self.service = self.get_mock_service(
                BugzillaService,
                config_overrides={
                    'bugzilla.base_uri': 'http://one.com/',
                    'bugzilla.username': 'me',
                    'bugzilla.api_key': '123',
                })

    def test_to_taskwarrior(self):
        arbitrary_extra = {
            'url': 'http://path/to/issue/',
            'annotations': [
                'Two',
            ],
        }

        issue = self.service.get_issue_for_record(
            self.arbitrary_record,
            arbitrary_extra,
        )

        expected_output = {
            'project': self.arbitrary_record['component'],
            'priority': issue.PRIORITY_MAP[self.arbitrary_record['priority']],
            'annotations': arbitrary_extra['annotations'],

            issue.STATUS: self.arbitrary_record['status'],
            issue.URL: arbitrary_extra['url'],
            issue.SUMMARY: self.arbitrary_record['summary'],
            issue.BUG_ID: self.arbitrary_record['id'],
            issue.PRODUCT: self.arbitrary_record['product'],
            issue.COMPONENT: self.arbitrary_record['component'],
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

    def test_issues(self):
        issue = next(self.service.issues())

        expected = {
            'annotations': [],
            'bugzillabugid': 1234567,
            'bugzillastatus': 'NEW',
            'bugzillasummary': 'This is the issue summary',
            'bugzillaurl': u'https://http://one.com//show_bug.cgi?id=1234567',
            'bugzillaproduct': 'Product',
            'bugzillacomponent': 'Something',
            'description': u'(bw)Is#1234567 - This is the issue summary .. https://http://one.com//show_bug.cgi?id=1234567',
            'priority': 'H',
            'project': 'Something',
            'tags': []}

        self.assertEqual(issue.get_taskwarrior_record(), expected)

    def test_only_if_assigned(self):
        with mock.patch('bugzilla.Bugzilla'):
            self.service = self.get_mock_service(
                BugzillaService,
                config_overrides={
                    'bugzilla.only_if_assigned': 'hello',
                })

        assigned_records = [
            {
                'product': 'Product',
                'component': 'Something',
                'priority': 'urgent',
                'status': 'ASSIGNED',
                'summary': 'This is the issue summary',
                'id': 1234568,
                'flags': [],
                'assigned_to': 'hello'
            },
            {
                'product': 'Product',
                'component': 'Something',
                'priority': 'urgent',
                'status': 'ASSIGNED',
                'summary': 'This is the issue summary',
                'id': 1234569,
                'flags': [],
                'assigned_to': 'somebodyelse'
            },
        ]
        self.service.bz.records.extend(assigned_records)

        issues = self.service.issues()

        expected = {
            'annotations': [],
            'bugzillaassignedon': self.arbitrary_datetime,
            'bugzillabugid': 1234568,
            'bugzillastatus': 'ASSIGNED',
            'bugzillasummary': 'This is the issue summary',
            'bugzillaurl': u'https://http://one.com//show_bug.cgi?id=1234568',
            'bugzillaproduct': 'Product',
            'bugzillacomponent': 'Something',
            'description': u'(bw)Is#1234568 - This is the issue summary .. https://http://one.com//show_bug.cgi?id=1234568',
            'priority': 'H',
            'project': 'Something',
            'tags': []}

        self.assertEqual(next(issues).get_taskwarrior_record(), expected)

        # Only one issue is assigned.
        self.assertRaises(StopIteration, lambda: next(issues))

    def test_also_unassigned(self):
        with mock.patch('bugzilla.Bugzilla'):
            self.service = self.get_mock_service(
                BugzillaService,
                config_overrides={
                    'bugzilla.only_if_assigned': 'hello',
                    'bugzilla.also_unassigned': True,
                })

        assigned_records = [
            {
                'product': 'Product',
                'component': 'Something',
                'priority': 'urgent',
                'status': 'ASSIGNED',
                'summary': 'This is the issue summary',
                'id': 1234568,
                'flags': [],
                'assigned_to': 'hello'
            },
            {
                'product': 'Product',
                'component': 'Something',
                'priority': 'urgent',
                'status': 'ASSIGNED',
                'summary': 'This is the issue summary',
                'id': 1234569,
                'flags': [],
                'assigned_to': 'somebodyelse'
            },
        ]
        self.service.bz.records.extend(assigned_records)

        issues = self.service.issues()

        self.assertIn(next(issues).get_taskwarrior_record()['bugzillabugid'],
                      [1234567, 1234568])
        self.assertIn(next(issues).get_taskwarrior_record()['bugzillabugid'],
                      [1234567, 1234568])
        # Only two issues are assigned to the user or unassigned.
        self.assertRaises(StopIteration, lambda: next(issues))
