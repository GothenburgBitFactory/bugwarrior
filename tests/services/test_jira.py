from collections import namedtuple
from datetime import UTC, datetime
from unittest import mock

import pytest

from bugwarrior.collect import TaskConstructor
from bugwarrior.config import validation
from bugwarrior.config.load import format_config
from bugwarrior.services.jira import JiraExtraFields, JiraService

SERVICE_CLASS = JiraService

SERVICE_CONFIG = {
    'service': 'jira',
    'username': 'one',
    'base_uri': 'https://two.org',
    'password': 'three',
    'extra_fields': [
        'jiraextra1:customfield_10000',
        'jiraextra2:namedfield.valueinside',
    ],
}


ESTIMATION = 3600
ARBITRARY_ID = '10'
ARBITRARY_SUBTASK_IDS = ['11', '12']
ARBITRARY_PARENT_ID = '13'
ARBITRARY_NAMEDFIELD_VALUEINSIDE = 77
PROJECT = 'DONUT'
SUMMARY = 'lkjaldsfjaldf'


@pytest.fixture
def record():
    return {
        'fields': {
            'priority': 'Blocker',
            'summary': SUMMARY,
            'timeestimate': ESTIMATION,
            'created': '2016-06-06T06:07:08.123-0700',
            'fixVersions': [{'name': '1.2.3'}],
            'issuetype': {'name': 'Epic'},
            'status': {'name': 'Open'},
            'subtasks': [
                {'key': f'DONUT-{subtask}'} for subtask in ARBITRARY_SUBTASK_IDS
            ],
            'parent': {'key': f'DONUT-{ARBITRARY_PARENT_ID}'},
            'customfield_10000': 'foo',
            'namedfield': {'valueinside': ARBITRARY_NAMEDFIELD_VALUEINSIDE},
        },
        'key': f'{PROJECT}-{ARBITRARY_ID}',
    }


@pytest.fixture
def record_with_due(record):
    record['fields']['Sprint'] = [
        'com.atlassian.greenhopper.service.sprint.Sprint@4c9c41a5[id=2322,rapidViewId=1173,\
                    state=ACTIVE,name=Sprint 1,startDate=2016-09-06T16:08:07.4\
                    55Z,endDate=2016-09-23T16:08:00.000Z,completeDate=<null>,sequence=2322]'
    ]
    return record


class FakeJiraClient:
    def __init__(self, record):
        self.record = record

    def search_issues(self, *args, **kwargs):
        Case = namedtuple('Case', ['raw', 'key'])
        return [Case(self.record, self.record['key'])]

    def comments(self, *args, **kwargs):
        return None


class TestJiraService:
    @pytest.fixture
    def config(self):
        return {
            'general': {'targets': ['myservice']},
            'myservice': {
                'service': 'jira',
                'base_uri': 'https://example.com',
                'username': 'milou',
                'password': 't0ps3cr3t',
                'extra_fields': [
                    'jiraextra1:customfield_10000',
                    'jiraextra2:namedfield.valueinside',
                ],
            },
        }

    def test_body_length_no_limit(self, config):
        description = "A very short issue body.  Fixes #828."
        config['myservice']['body_length'] = '5'
        formatted = format_config(config)
        conf = validation.validate_config(formatted, 'general', 'configpath')
        service = JiraService(conf.service_configs[0], conf.main, _skip_server=True)
        issue = mock.Mock()
        issue.record = {'fields': {'description': description}}
        assert description[:5] == service.body(issue)

    def test_body_length_limit(self, config):
        description = "A very short issue body.  Fixes #828."
        formatted = format_config(config)
        conf = validation.validate_config(formatted, 'general', 'configpath')
        service = JiraService(conf.service_configs[0], conf.main, _skip_server=True)
        issue = mock.Mock()
        issue.record = {'fields': {'description': description}}
        assert description == service.body(issue)


class TestJiraIssue:
    @pytest.fixture
    def service(self, record, make_service):
        with mock.patch('jira.client.JIRA._get_json'):
            service = make_service()
        service.jira = FakeJiraClient(record)
        service.sprint_field_names = ['Sprint']
        return service

    def get_extra_fields(self):
        return JiraExtraFields.validate(
            ['jiraextra1:customfield_10000', 'jiraextra2:namedfield.valueinside']
        )

    def test_to_taskwarrior(self, service, record):
        url = 'http://one'
        extra = {
            'annotations': ['an annotation'],
            'body': 'issue body',
            'sprint_field_names': [],
        }

        issue = service.get_issue_for_record(record, extra)

        expected_output = {
            'project': PROJECT,
            'priority': (issue.PRIORITY_MAP[record['fields']['priority']]),
            'annotations': extra['annotations'],
            'due': None,
            'tags': [],
            'entry': datetime(2016, 6, 6, 13, 7, 8, tzinfo=UTC),
            'jirafixversion': '1.2.3',
            'jiraissuetype': 'Epic',
            'jirastatus': 'Open',
            'jirasubtasks': 'DONUT-11,DONUT-12',
            'jiraparent': 'DONUT-13',
            'jiraextra1': 'foo',
            'jiraextra2': 77,
            issue.URL: url,
            issue.FOREIGN_ID: record['key'],
            issue.SUMMARY: SUMMARY,
            issue.DESCRIPTION: 'issue body',
            issue.ESTIMATE: ESTIMATION / 60 / 60,
        }

        def get_url(*args):
            return url

        with mock.patch.object(issue, 'get_url', side_effect=get_url):
            actual_output = issue.to_taskwarrior()

        assert actual_output == expected_output

    def test_to_taskwarrior_sprint_with_goal(self, service, record):
        record['fields']['Sprint'] = [
            'com.atlassian.greenhopper.service.sprint.Sprint@4c9c41a5[id=2322,rapidViewId=1173,\
            state=ACTIVE,name=Sprint 1,goal=Do foo, bar, baz,startDate=2016-09-06T16:08:07.4\
            55Z,endDate=2016-09-23T16:08:00.000Z,completeDate=<null>,sequence=2322]'
        ]
        url = 'http://one'
        extra = {
            'annotations': ['an annotation'],
            'sprint_field_names': service.sprint_field_names,
        }

        issue = service.get_issue_for_record(record, extra)

        expected_output = {
            'project': PROJECT,
            'priority': (issue.PRIORITY_MAP[record['fields']['priority']]),
            'annotations': extra['annotations'],
            'due': datetime(2016, 9, 23, 16, 8, tzinfo=UTC),
            'tags': [],
            'entry': datetime(2016, 6, 6, 13, 7, 8, tzinfo=UTC),
            'jirafixversion': '1.2.3',
            'jiraissuetype': 'Epic',
            'jirastatus': 'Open',
            'jirasubtasks': 'DONUT-11,DONUT-12',
            'jiraparent': 'DONUT-13',
            'jiraextra1': 'foo',
            'jiraextra2': 77,
            issue.URL: url,
            issue.FOREIGN_ID: record['key'],
            issue.SUMMARY: SUMMARY,
            issue.DESCRIPTION: None,
            issue.ESTIMATE: ESTIMATION / 60 / 60,
        }

        def get_url(*args):
            return url

        with mock.patch.object(issue, 'get_url', side_effect=get_url):
            actual_output = issue.to_taskwarrior()

        assert actual_output == expected_output

    def test_issues(self, service):
        issue = next(service.issues())

        expected = {
            'annotations': [],
            'due': None,
            'description': (
                '(bw)Is#10 - lkjaldsfjaldf .. https://two.org/browse/DONUT-10'
            ),
            'entry': datetime(2016, 6, 6, 13, 7, 8, tzinfo=UTC),
            'jiradescription': None,
            'jiraestimate': 1,
            'jirafixversion': '1.2.3',
            'jiraid': 'DONUT-10',
            'jiraissuetype': 'Epic',
            'jirastatus': 'Open',
            'jirasummary': 'lkjaldsfjaldf',
            'jiraurl': 'https://two.org/browse/DONUT-10',
            'jirasubtasks': 'DONUT-11,DONUT-12',
            'jiraparent': 'DONUT-13',
            'jiraextra1': 'foo',
            'jiraextra2': 77,
            'priority': 'H',
            'project': 'DONUT',
            'tags': [],
        }

        assert TaskConstructor(issue).get_taskwarrior_record() == expected

    def test_get_due(self, service, record_with_due):
        issue = service.get_issue_for_record(
            record_with_due, extra={'sprint_field_names': service.sprint_field_names}
        )

        assert issue.get_due() == datetime(2016, 9, 23, 16, 8, tzinfo=UTC)

    def test_get_due_sprint_dict_missing_end_date(self, service, record):
        record['fields']['Sprint'] = [{'id': 1, 'state': 'active', 'name': 'Sprint 1'}]

        issue = service.get_issue_for_record(
            record, extra={'sprint_field_names': service.sprint_field_names}
        )

        assert issue.get_due() is None
