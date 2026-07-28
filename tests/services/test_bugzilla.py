from collections import namedtuple
import datetime
from unittest import mock

import pytest

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.bz import BugzillaService

from ..base import validate
from .base import get_mock_service

SERVICE_CONFIG = {
    'service': 'bugzilla',
    'base_uri': 'https://one.com/',
    'username': 'hello',
    'password': 'there',
}


class FakeBugzillaLib:
    def __init__(self, records):
        self.records = records

    def query(self, query):
        return [
            namedtuple('Record', list(record.keys()))(**record)
            for record in self.records
        ]


class TestBugzillaConfig:
    @pytest.fixture
    def config(self):
        return {
            'general': {'targets': ['myservice']},
            'myservice': {'service': 'bugzilla'},
        }

    def test_validate_config_username_password(self, config):
        config['myservice'].update(
            {'base_uri': 'https://one.com/', 'username': 'me', 'password': 'mypas'}
        )

        # no error expected
        validate(config)

    def test_validate_config_api_key(self, config):
        config['myservice'].update(
            {'base_uri': 'https://one.com/', 'username': 'me', 'api_key': '123'}
        )

        # no error expected
        validate(config)

    def test_validate_config_api_key_no_username(self, config, assert_validation_error):
        config['myservice'].update({'base_uri': 'https://one.com/', 'api_key': '123'})

        assert_validation_error(config, '[myservice]\nusername  <- Field required')

    def test_validate_warns_when_scheme_missing_in_uri(self, config, caplog):
        config['myservice'].update(
            {'base_uri': 'one.com/', 'username': 'me', 'password': 'mypas'}
        )

        validate(config)

        assert len(caplog.records) == 1
        assert (
            'bugzilla.base_uri should include the scheme' in caplog.records[0].message
        )


@pytest.fixture
def record():
    return {
        'product': 'Product',
        'component': 'Something',
        'priority': 'urgent',
        'status': 'NEW',
        'summary': 'This is the issue summary',
        'id': 1234567,
        'flags': [],
        'assigned_to': None,
    }


ASSIGNED_DATE = datetime.datetime.now(tz=datetime.UTC).replace(microsecond=0)


@pytest.fixture
def make_service(record):
    def make(**overrides):
        with mock.patch('bugzilla.Bugzilla'):
            service = get_mock_service(BugzillaService, {**SERVICE_CONFIG, **overrides})
        service.bz = FakeBugzillaLib([record])
        service._get_assigned_date = lambda issues: ASSIGNED_DATE.isoformat()
        return service

    return make


@pytest.fixture
def service(make_service):
    return make_service()


class TestBugzillaService:
    def test_api_key_supplied(self, make_service):
        make_service(base_uri='https://one.com/', username='me', api_key='123')

    def test_to_taskwarrior(self, service, record):
        arbitrary_extra = {'url': 'http://path/to/issue/', 'annotations': ['Two']}

        issue = service.get_issue_for_record(record, arbitrary_extra)

        expected_output = {
            'project': record['component'],
            'priority': issue.PRIORITY_MAP[record['priority']],
            'annotations': arbitrary_extra['annotations'],
            issue.STATUS: record['status'],
            issue.URL: arbitrary_extra['url'],
            issue.SUMMARY: record['summary'],
            issue.BUG_ID: record['id'],
            issue.PRODUCT: record['product'],
            issue.COMPONENT: record['component'],
        }
        actual_output = issue.to_taskwarrior()

        assert actual_output == expected_output

    def test_issues(self, service):
        issue = next(service.issues())

        expected = {
            'annotations': [],
            'bugzillabugid': 1234567,
            'bugzillastatus': 'NEW',
            'bugzillasummary': 'This is the issue summary',
            'bugzillaurl': 'https://one.com/show_bug.cgi?id=1234567',
            'bugzillaproduct': 'Product',
            'bugzillacomponent': 'Something',
            'description': (
                '(bw)Is#1234567 - This is the issue summary .. '
                'https://one.com/show_bug.cgi?id=1234567'
            ),
            'priority': 'H',
            'project': 'Something',
            'tags': [],
        }

        assert TaskConstructor(issue).get_taskwarrior_record() == expected

    def test_only_if_assigned(self, make_service):
        service = make_service(only_if_assigned='hello')

        assigned_records = [
            {
                'product': 'Product',
                'component': 'Something',
                'priority': 'urgent',
                'status': 'ASSIGNED',
                'summary': 'This is the issue summary',
                'id': 1234568,
                'flags': [],
                'assigned_to': 'hello',
            },
            {
                'product': 'Product',
                'component': 'Something',
                'priority': 'urgent',
                'status': 'ASSIGNED',
                'summary': 'This is the issue summary',
                'id': 1234569,
                'flags': [],
                'assigned_to': 'somebodyelse',
            },
        ]
        service.bz.records.extend(assigned_records)

        issues = service.issues()

        expected = {
            'annotations': [],
            'bugzillaassignedon': ASSIGNED_DATE,
            'bugzillabugid': 1234568,
            'bugzillastatus': 'ASSIGNED',
            'bugzillasummary': 'This is the issue summary',
            'bugzillaurl': 'https://one.com/show_bug.cgi?id=1234568',
            'bugzillaproduct': 'Product',
            'bugzillacomponent': 'Something',
            'description': (
                '(bw)Is#1234568 - This is the issue summary .. '
                'https://one.com/show_bug.cgi?id=1234568'
            ),
            'priority': 'H',
            'project': 'Something',
            'tags': [],
        }

        assert TaskConstructor(next(issues)).get_taskwarrior_record() == expected

        # Only one issue is assigned.
        with pytest.raises(StopIteration):
            next(issues)

    def test_also_unassigned(self, make_service):
        service = make_service(only_if_assigned='hello', also_unassigned=True)

        assigned_records = [
            {
                'product': 'Product',
                'component': 'Something',
                'priority': 'urgent',
                'status': 'ASSIGNED',
                'summary': 'This is the issue summary',
                'id': 1234568,
                'flags': [],
                'assigned_to': 'hello',
            },
            {
                'product': 'Product',
                'component': 'Something',
                'priority': 'urgent',
                'status': 'ASSIGNED',
                'summary': 'This is the issue summary',
                'id': 1234569,
                'flags': [],
                'assigned_to': 'somebodyelse',
            },
        ]
        service.bz.records.extend(assigned_records)

        issues = service.issues()

        assert TaskConstructor(next(issues)).get_taskwarrior_record()[
            'bugzillabugid'
        ] in [1234567, 1234568]
        assert TaskConstructor(next(issues)).get_taskwarrior_record()[
            'bugzillabugid'
        ] in [1234567, 1234568]
        # Only two issues are assigned to the user or unassigned.
        with pytest.raises(StopIteration):
            next(issues)
