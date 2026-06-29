import responses

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.youtrack import YoutrackService

from .base import ConfigTest, ServiceIssueTest


class TestYoutrackService(ConfigTest):
    def setUp(self):
        super().setUp()
        self.config = {
            'general': {'targets': ['myservice']},
            'myservice': {'service': 'youtrack', 'login': 'foobar', 'token': 'XXXXXX'},
        }

    def test_keyring_service(self):
        self.config['myservice']['host'] = 'youtrack.example.com'
        service_config = self.validate().service_configs[0]
        self.assertEqual(
            service_config.keyring_service, 'youtrack://foobar@youtrack.example.com'
        )


class TestYoutrackIssue(ServiceIssueTest):
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

    def setUp(self):
        super().setUp()
        self.service = self.get_mock_service(YoutrackService)

    def test_get_tags_from_labels_uses_legacy_tag_options(self):
        service = self.get_mock_service(
            YoutrackService,
            config_overrides={'import_tags': True, 'tag_template': 'yt_{{tag|lower}}'},
        )
        issue = service.get_issue_for_record(self.arbitrary_issue, self.arbitrary_extra)

        self.assertEqual(service.config.label_template, 'yt_{{label|lower}}')
        self.assertEqual(issue.get_tags(), ['yt_bug', 'yt_new_feature'])
        self.assertIn(
            'import_tags is deprecated in favor of import_labels_as_tags',
            self.caplog.text,
        )
        self.assertIn(
            'tag_template is deprecated in favor of label_template', self.caplog.text
        )
        self.assertIn(
            "The 'tag' variable in YouTrack label templates is deprecated in favor of 'label'.",
            self.caplog.text,
        )

    def test_refine_record_does_not_apply_legacy_tag_template_as_field_template(self):
        service = self.get_mock_service(
            YoutrackService,
            config_overrides={'import_tags': True, 'tag_template': 'yt_{{tag|lower}}'},
        )
        issue = service.get_issue_for_record(self.arbitrary_issue, self.arbitrary_extra)

        self.assertEqual(service.config.templates, {})
        self.assertEqual(
            TaskConstructor(issue).get_taskwarrior_record()['tags'],
            ['yt_bug', 'yt_new_feature'],
        )

    def test_to_taskwarrior(self):
        self.service.import_tags = True
        issue = self.service.get_issue_for_record(
            self.arbitrary_issue, self.arbitrary_extra
        )

        expected_output = {
            'project': 'TEST',
            'priority': self.service.config.default_priority,
            'tags': ['bug', 'new_feature'],
            issue.ISSUE: 'TEST-1',
            issue.SUMMARY: 'Hello World',
            issue.URL: 'https://youtrack.example.com:443/issue/TEST-1',
            issue.PROJECT: 'TEST',
            issue.NUMBER: 1,
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

    @responses.activate
    def test_issues(self):
        responses.get(
            'https://youtrack.example.com:443/api/issues?query=for%3Ame+%23Unresolved&max=100&fields=id,summary,project(shortName),numberInProject,tags(name)',  # noqa: E501
            json=[self.arbitrary_issue],
        )

        issue = next(self.service.issues())

        expected = {
            'description': '(bw)Is#TEST-1 - Hello World .. https://youtrack.example.com:443/issue/TEST-1',
            'project': 'TEST',
            'priority': self.service.config.default_priority,
            'tags': ['bug', 'new_feature'],
            'youtrackissue': 'TEST-1',
            'youtracksummary': 'Hello World',
            'youtrackurl': 'https://youtrack.example.com:443/issue/TEST-1',
            'youtrackproject': 'TEST',
            'youtracknumber': 1,
        }

        self.assertEqual(TaskConstructor(issue).get_taskwarrior_record(), expected)
