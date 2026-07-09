import pytest
import responses

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.youtrack import YoutrackService

from ..base import validate
from .base import get_mock_service


class TestYoutrackService:
    @pytest.fixture
    def config(self):
        return {
            'general': {'targets': ['myservice']},
            'myservice': {'service': 'youtrack', 'login': 'foobar', 'token': 'XXXXXX'},
        }

    def test_keyring_service(self, config):
        config['myservice']['host'] = 'youtrack.example.com'
        service_config = validate(config).service_configs[0]
        assert (
            service_config.keyring_service == 'youtrack://foobar@youtrack.example.com'
        )


class TestYoutrackIssue:
    SERVICE_CONFIG = {
        'service': 'youtrack',
        'host': 'youtrack.example.com',
        'login': 'arbitrary_login',
        'token': 'arbitrary_token',
        'anonymous': True,
    }

    arbitrary_issue = {
        "id": "2-1",
        "$type": "Issue",
        "numberInProject": 1,
        "summary": "Hello World",
        "project": {"shortName": "TEST", "$type": "Project"},
        "tags": [
            {"$type": "IssueTag", "name": "bug"},
            {"$type": "IssueTag", "name": "New Feature"},
        ],
    }
    arbitrary_extra = {}

    @pytest.fixture
    def service(self):
        return get_mock_service(YoutrackService, self.SERVICE_CONFIG)

    def test_get_tags_from_labels_uses_legacy_tag_options(self, caplog):
        service = get_mock_service(
            YoutrackService,
            {
                **self.SERVICE_CONFIG,
                'import_tags': True,
                'tag_template': 'yt_{{tag|lower}}',
            },
        )
        issue = service.get_issue_for_record(self.arbitrary_issue, self.arbitrary_extra)

        assert service.config.label_template == 'yt_{{label|lower}}'
        assert issue.get_tags() == ['yt_bug', 'yt_new_feature']
        assert (
            'import_tags is deprecated in favor of import_labels_as_tags' in caplog.text
        )
        assert 'tag_template is deprecated in favor of label_template' in caplog.text
        assert (
            "The 'tag' variable in YouTrack label templates is deprecated in favor of 'label'."
            in caplog.text
        )

    def test_refine_record_does_not_apply_legacy_tag_template_as_field_template(self):
        service = get_mock_service(
            YoutrackService,
            {
                **self.SERVICE_CONFIG,
                'import_tags': True,
                'tag_template': 'yt_{{tag|lower}}',
            },
        )
        issue = service.get_issue_for_record(self.arbitrary_issue, self.arbitrary_extra)

        assert service.config.templates == {}
        assert TaskConstructor(issue).get_taskwarrior_record()['tags'] == [
            'yt_bug',
            'yt_new_feature',
        ]

    def test_to_taskwarrior(self, service):
        service.import_tags = True
        issue = service.get_issue_for_record(self.arbitrary_issue, self.arbitrary_extra)

        expected_output = {
            'project': 'TEST',
            'priority': service.config.default_priority,
            'tags': ['bug', 'new_feature'],
            issue.ISSUE: 'TEST-1',
            issue.SUMMARY: 'Hello World',
            issue.URL: 'https://youtrack.example.com:443/issue/TEST-1',
            issue.PROJECT: 'TEST',
            issue.NUMBER: 1,
        }
        actual_output = issue.to_taskwarrior()

        assert actual_output == expected_output

    @responses.activate
    def test_issues(self, service):
        responses.get(
            'https://youtrack.example.com:443/api/issues?query=for%3Ame+%23Unresolved&max=100&fields=id,summary,project(shortName),numberInProject,tags(name)',  # noqa: E501
            json=[self.arbitrary_issue],
        )

        issue = next(service.issues())

        expected = {
            'description': '(bw)Is#TEST-1 - Hello World .. https://youtrack.example.com:443/issue/TEST-1',
            'project': 'TEST',
            'priority': service.config.default_priority,
            'tags': ['bug', 'new_feature'],
            'youtrackissue': 'TEST-1',
            'youtracksummary': 'Hello World',
            'youtrackurl': 'https://youtrack.example.com:443/issue/TEST-1',
            'youtrackproject': 'TEST',
            'youtracknumber': 1,
        }

        assert TaskConstructor(issue).get_taskwarrior_record() == expected
