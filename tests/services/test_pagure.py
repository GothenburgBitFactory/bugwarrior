import datetime

import pytest
import responses

from bugwarrior.services.pagure import PagureService

SERVICE_CLASS = PagureService

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
    def test_to_taskwarrior(self, service, record, extra):
        issue = service.get_issue_for_record(record, extra)

        expected = {
            'annotations': [],
            'priority': 'M',
            'project': 'repo',
            'tags': [],
            'pagureurl': 'https://pagure.io/repo/issue/1',
            'pagurerepo': 'repo',
            'paguretype': 'issue',
            'paguretitle': 'Hello World',
            'pagureid': 1,
            'paguredatecreated': datetime.datetime(
                1970, 1, 1, tzinfo=datetime.timezone.utc
            ),
        }
        assert issue.to_taskwarrior().to_taskwarrior_data() == expected

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

        task = next(service.issues())

        expected = {
            'annotations': [],
            'description': '(bw)Is#1 - Hello World .. https://pagure.io/repo/issue/1',
            'priority': 'M',
            'project': 'repo',
            'tags': [],
            'pagureurl': 'https://pagure.io/repo/issue/1',
            'pagurerepo': 'repo',
            'paguretype': 'issue',
            'paguretitle': 'Hello World',
            'pagureid': 1,
            'paguredatecreated': datetime.datetime(
                1970, 1, 1, tzinfo=datetime.timezone.utc
            ),
        }
        assert task.to_taskwarrior_data() == expected

    def test_get_tags_from_labels_uses_legacy_tag_options(
        self, caplog, make_service, record, extra
    ):
        service = make_service(import_tags=True, tag_template='pg_{{label}}')
        issue = service.get_issue_for_record(record, extra)

        assert issue.get_tags() == ['pg_Bug', 'pg_Needs_Work']
        assert (
            'import_tags is deprecated in favor of import_labels_as_tags' in caplog.text
        )
        assert 'tag_template is deprecated in favor of label_template' in caplog.text

    def test_refine_record_does_not_apply_legacy_tag_template_as_field_template(
        self, make_service, record, extra
    ):
        service = make_service(import_tags=True, tag_template='pg_{{label}}')

        assert service.config.templates == {}
        assert service.process_record(record, extra).tags == ['pg_Bug', 'pg_Needs_Work']
