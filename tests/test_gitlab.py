from future import standard_library
standard_library.install_aliases()
from builtins import next
from six.moves import configparser
import datetime

import pytz
import responses

from bugwarrior.config import ServiceConfig
from bugwarrior.services.gitlab import GitlabService

from .base import ConfigTest, ServiceTest, AbstractServiceTest


class TestGitlabService(ConfigTest):

    def setUp(self):
        super(TestGitlabService, self).setUp()
        self.config = configparser.RawConfigParser()
        self.config.add_section('general')
        self.config.add_section('myservice')
        self.config.set('myservice', 'gitlab.login', 'foobar')
        self.config.set('myservice', 'gitlab.token', 'XXXXXX')
        self.service_config = ServiceConfig(
            GitlabService.CONFIG_PREFIX, self.config, 'myservice')

    def test_get_keyring_service_default_host(self):
        self.assertEqual(
            GitlabService.get_keyring_service(self.service_config),
            'gitlab://foobar@gitlab.com')

    def test_get_keyring_service_custom_host(self):
        self.config.set('myservice', 'gitlab.host', 'gitlab.example.com')
        self.assertEqual(
            GitlabService.get_keyring_service(self.service_config),
            'gitlab://foobar@gitlab.example.com')

    def test_add_default_namespace_to_included_repos(self):
        self.config.set('myservice', 'gitlab.include_repos', 'baz, banana/tree')
        service = GitlabService(self.config, 'general', 'myservice')
        self.assertEqual(service.include_repos, ['foobar/baz', 'banana/tree'])

    def test_add_default_namespace_to_excluded_repos(self):
        self.config.set('myservice', 'gitlab.exclude_repos', 'baz, banana/tree')
        service = GitlabService(self.config, 'general', 'myservice')
        self.assertEqual(service.exclude_repos, ['foobar/baz', 'banana/tree'])


class TestGitlabIssue(AbstractServiceTest, ServiceTest):
    maxDiff = None
    SERVICE_CONFIG = {
        'gitlab.host': 'gitlab.example.com',
        'gitlab.login': 'arbitrary_login',
        'gitlab.token': 'arbitrary_token',
    }

    def setUp(self):
        super(TestGitlabIssue, self).setUp()
        self.service = self.get_mock_service(GitlabService)
        self.arbitrary_created = (
            datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        ).replace(tzinfo=pytz.UTC, microsecond=0)
        self.arbitrary_updated = datetime.datetime.utcnow().replace(
            tzinfo=pytz.UTC, microsecond=0)
        self.arbitrary_duedate = (
            datetime.datetime.combine(datetime.date.today(),
                                      datetime.datetime.min.time())
        ).replace(tzinfo=pytz.UTC)
        self.arbitrary_issue = {
            "id": 42,
            "iid": 3,
            "project_id": 8,
            "title": "Add user settings",
            "description": "",
            "labels": [
                "feature"
            ],
            "milestone": {
                "id": 1,
                "title": "v1.0",
                "description": "",
                "due_date": self.arbitrary_duedate.date().isoformat(),
                "state": "closed",
                "updated_at": "2012-07-04T13:42:48Z",
                "created_at": "2012-07-04T13:42:48Z"
            },
            "assignee": {
                "id": 2,
                "username": "jack_smith",
                "email": "jack@example.com",
                "name": "Jack Smith",
                "state": "active",
                "created_at": "2012-05-23T08:01:01Z"
            },
            "author": {
                "id": 1,
                "username": "john_smith",
                "email": "john@example.com",
                "name": "John Smith",
                "state": "active",
                "created_at": "2012-05-23T08:00:58Z"
            },
            "state": "opened",
            "updated_at": self.arbitrary_updated.isoformat(),
            "created_at": self.arbitrary_created.isoformat(),
            "weight": 3,
            "work_in_progress": "true"
        }
        self.arbitrary_extra = {
            'issue_url': 'https://gitlab.example.com/arbitrary_username/project/issues/3',
            'project': 'project',
            'namespace': 'arbitrary_namespace',
            'type': 'issue',
            'annotations': [],
        }

    def test_normalize_label_to_tag(self):
        issue = self.service.get_issue_for_record(
            self.arbitrary_issue,
            self.arbitrary_extra
        )
        self.assertEqual(issue._normalize_label_to_tag('needs work'),
                         'needs_work')

    def test_to_taskwarrior(self):
        self.service.import_labels_as_tags = True
        issue = self.service.get_issue_for_record(
            self.arbitrary_issue,
            self.arbitrary_extra
        )

        expected_output = {
            'project': self.arbitrary_extra['project'],
            'priority': self.service.default_priority,
            'annotations': [],
            'tags': [u'feature'],
            'due': self.arbitrary_duedate.replace(microsecond=0),
            'entry': self.arbitrary_created.replace(microsecond=0),
            issue.URL: self.arbitrary_extra['issue_url'],
            issue.REPO: 'project',
            issue.STATE: self.arbitrary_issue['state'],
            issue.TYPE: self.arbitrary_extra['type'],
            issue.TITLE: self.arbitrary_issue['title'],
            issue.NUMBER: str(self.arbitrary_issue['iid']),
            issue.UPDATED_AT: self.arbitrary_updated.replace(microsecond=0),
            issue.CREATED_AT: self.arbitrary_created.replace(microsecond=0),
            issue.DUEDATE: self.arbitrary_duedate,
            issue.DESCRIPTION: self.arbitrary_issue['description'],
            issue.MILESTONE: self.arbitrary_issue['milestone']['title'],
            issue.UPVOTES: 0,
            issue.DOWNVOTES: 0,
            issue.WORK_IN_PROGRESS: 1,
            issue.AUTHOR: 'john_smith',
            issue.ASSIGNEE: 'jack_smith',
            issue.NAMESPACE: 'arbitrary_namespace',
            issue.WEIGHT: 3,
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

    def test_work_in_progress(self):
        self.arbitrary_issue['work_in_progress'] = 'false'
        self.service.import_labels_as_tags = True
        issue = self.service.get_issue_for_record(
            self.arbitrary_issue,
            self.arbitrary_extra
        )

        expected_output = {
            'project': self.arbitrary_extra['project'],
            'priority': self.service.default_priority,
            'annotations': [],
            'tags': [u'feature'],
            'due': self.arbitrary_duedate.replace(microsecond=0),
            'entry': self.arbitrary_created.replace(microsecond=0),
            issue.URL: self.arbitrary_extra['issue_url'],
            issue.REPO: 'project',
            issue.STATE: self.arbitrary_issue['state'],
            issue.TYPE: self.arbitrary_extra['type'],
            issue.TITLE: self.arbitrary_issue['title'],
            issue.NUMBER: str(self.arbitrary_issue['iid']),
            issue.UPDATED_AT: self.arbitrary_updated.replace(microsecond=0),
            issue.CREATED_AT: self.arbitrary_created.replace(microsecond=0),
            issue.DUEDATE: self.arbitrary_duedate,
            issue.DESCRIPTION: self.arbitrary_issue['description'],
            issue.MILESTONE: self.arbitrary_issue['milestone']['title'],
            issue.UPVOTES: 0,
            issue.DOWNVOTES: 0,
            issue.WORK_IN_PROGRESS: 0,
            issue.AUTHOR: 'john_smith',
            issue.ASSIGNEE: 'jack_smith',
            issue.NAMESPACE: 'arbitrary_namespace',
            issue.WEIGHT: 3,
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

    @responses.activate
    def test_issues(self):
        self.add_response(
            'https://gitlab.example.com/api/v4/projects?simple=True&per_page=100&page=1',
            json=[{
                'id': 1,
                'path': 'arbitrary_username/project',
                'web_url': 'example.com',
                "namespace": {
                    "full_path": "arbitrary_username"
                }
            }])

        self.add_response(
            'https://gitlab.example.com/api/v4/projects/1/issues?state=opened&per_page=100&page=1',
            json=[self.arbitrary_issue])

        self.add_response(
            'https://gitlab.example.com/api/v4/projects/1/issues/3/notes?per_page=100&page=1',
            json=[{
                'author': {'username': 'john_smith'},
                'body': 'Some comment.'
            }])

        issue = next(self.service.issues())

        expected = {
            'annotations': [u'@john_smith - Some comment.'],
            'description':
                u'(bw)Is#3 - Add user settings .. example.com/issues/3',
            'due': self.arbitrary_duedate,
            'entry': self.arbitrary_created,
            'gitlabassignee': u'jack_smith',
            'gitlabauthor': u'john_smith',
            'gitlabcreatedon': self.arbitrary_created,
            'gitlabdescription': u'',
            'gitlabdownvotes': 0,
            'gitlabmilestone': u'v1.0',
            'gitlabnamespace': u'arbitrary_username',
            'gitlabnumber': '3',
            'gitlabrepo': u'arbitrary_username/project',
            'gitlabstate': u'opened',
            'gitlabtitle': u'Add user settings',
            'gitlabtype': 'issue',
            'gitlabupdatedat': self.arbitrary_updated,
            'gitlabduedate': self.arbitrary_duedate,
            'gitlabupvotes': 0,
            'gitlaburl': u'example.com/issues/3',
            'gitlabwip': 1,
            'gitlabweight': 3,
            'priority': 'M',
            'project': u'arbitrary_username/project',
            'tags': []}

        self.assertEqual(issue.get_taskwarrior_record(), expected)
