import datetime

import pytest
import responses

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.pagure import PagureService

from .base import get_mock_service

SERVICE_CONFIG = {'service': 'pagure', 'base_url': 'https://pagure.io', 'repo': 'repo'}


@pytest.fixture
def record():
    return {
        'html_url': 'https://pagure.io/repo/issue/1',
        'repo': 'repo',
        'title': 'Hello World',
        'id': 1,
        'date_created': '0',
        'tags': ['Bug', 'Needs Work'],
        'comments': [],
    }


@pytest.fixture
def extra():
    return {'type': 'issue', 'project': 'repo', 'annotations': []}


class TestPagureIssue:
    @pytest.fixture
    def service(self):
        return get_mock_service(PagureService, SERVICE_CONFIG)

    def make_legacy_tags_service(self):
        return get_mock_service(
            PagureService,
            {**SERVICE_CONFIG, 'import_tags': True, 'tag_template': 'pg_{{label}}'},
        )

    def test_to_taskwarrior(self, service, record, extra):
        issue = service.get_issue_for_record(record, extra)

        expected = {
            'annotations': [],
            'priority': 'M',
            'project': 'repo',
            'tags': [],
            issue.URL: 'https://pagure.io/repo/issue/1',
            issue.REPO: 'repo',
            issue.TYPE: 'issue',
            issue.TITLE: 'Hello World',
            issue.ID: 1,
            issue.DATE_CREATED: datetime.datetime(
                1970, 1, 1, tzinfo=datetime.timezone.utc
            ),
        }
        assert issue.to_taskwarrior() == expected

    @responses.activate
    def test_issues(self, service):
        responses.get(
            'https://pagure.io/api/0/repo/issues',
            json={
                'issues': [
                    {
                        'id': 1,
                        'title': 'Hello World',
                        'date_created': '0',
                        'tags': ['Bug', 'Needs Work'],
                        'comments': [],
                    }
                ]
            },
        )
        responses.get(
            'https://pagure.io/api/0/repo/pull-requests', json={'requests': []}
        )

        issue = next(service.issues())

        expected = {
            'annotations': [],
            'description': '(bw)Is#1 - Hello World .. https://pagure.io/repo/issue/1',
            'priority': 'M',
            'project': 'repo',
            'tags': [],
            issue.URL: 'https://pagure.io/repo/issue/1',
            issue.REPO: 'repo',
            issue.TYPE: 'issue',
            issue.TITLE: 'Hello World',
            issue.ID: 1,
            issue.DATE_CREATED: datetime.datetime(
                1970, 1, 1, tzinfo=datetime.timezone.utc
            ),
        }
        assert TaskConstructor(issue).get_taskwarrior_record() == expected

    def test_get_tags_from_labels_uses_legacy_tag_options(self, caplog, record, extra):
        service = self.make_legacy_tags_service()
        issue = service.get_issue_for_record(record, extra)

        assert issue.get_tags() == ['pg_Bug', 'pg_Needs_Work']
        assert (
            'import_tags is deprecated in favor of import_labels_as_tags' in caplog.text
        )
        assert 'tag_template is deprecated in favor of label_template' in caplog.text

    def test_refine_record_does_not_apply_legacy_tag_template_as_field_template(
        self, record, extra
    ):
        service = self.make_legacy_tags_service()
        issue = service.get_issue_for_record(record, extra)

        assert issue.config.templates == {}
        assert TaskConstructor(issue).get_taskwarrior_record()['tags'] == [
            'pg_Bug',
            'pg_Needs_Work',
        ]
