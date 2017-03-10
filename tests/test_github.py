from builtins import next
import datetime
from unittest import TestCase
from configparser import RawConfigParser

import pytz
import responses

from bugwarrior.services.github import GithubService

from .base import ServiceTest, AbstractServiceTest


ARBITRARY_CREATED = (
    datetime.datetime.utcnow() - datetime.timedelta(hours=1)
).replace(tzinfo=pytz.UTC, microsecond=0)
ARBITRARY_UPDATED = datetime.datetime.utcnow().replace(
    tzinfo=pytz.UTC, microsecond=0)
ARBITRARY_ISSUE = {
    'title': 'Hallo',
    'html_url': 'https://github.com/arbitrary_username/arbitrary_repo/pull/1',
    'url': 'https://api.github.com/repos/arbitrary_username/arbitrary_repo/issues/1',
    'number': 10,
    'body': 'Something',
    'user': {'login': 'arbitrary_login'},
    'milestone': {'title': 'alpha'},
    'labels': [{'name': 'bugfix'}],
    'created_at': ARBITRARY_CREATED.isoformat(),
    'updated_at': ARBITRARY_UPDATED.isoformat(),
    'repo': 'ralphbean/bugwarrior',
}
ARBITRARY_EXTRA = {
    'project': 'one',
    'type': 'issue',
    'annotations': [],
}


class TestGithubIssue(AbstractServiceTest, ServiceTest):
    maxDiff = None
    SERVICE_CONFIG = {
        'github.login': 'arbitrary_login',
        'github.password': 'arbitrary_password',
        'github.username': 'arbitrary_username',
    }

    def setUp(self):
        super(TestGithubIssue, self).setUp()
        self.service = self.get_mock_service(GithubService)

    def test_normalize_label_to_tag(self):
        issue = self.service.get_issue_for_record(
            ARBITRARY_ISSUE,
            ARBITRARY_EXTRA
        )
        self.assertEqual(issue._normalize_label_to_tag('needs work'),
                         'needs_work')

    def test_to_taskwarrior(self):
        self.service.import_labels_as_tags = True
        issue = self.service.get_issue_for_record(
            ARBITRARY_ISSUE,
            ARBITRARY_EXTRA
        )

        expected_output = {
            'project': ARBITRARY_EXTRA['project'],
            'priority': self.service.default_priority,
            'annotations': [],
            'tags': ['bugfix'],
            issue.URL: ARBITRARY_ISSUE['html_url'],
            issue.REPO: ARBITRARY_ISSUE['repo'],
            issue.TYPE: ARBITRARY_EXTRA['type'],
            issue.TITLE: ARBITRARY_ISSUE['title'],
            issue.NUMBER: ARBITRARY_ISSUE['number'],
            issue.UPDATED_AT: ARBITRARY_UPDATED,
            issue.CREATED_AT: ARBITRARY_CREATED,
            issue.BODY: ARBITRARY_ISSUE['body'],
            issue.MILESTONE: ARBITRARY_ISSUE['milestone']['title'],
            issue.USER: ARBITRARY_ISSUE['user']['login'],
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

    @responses.activate
    def test_issues(self):
        self.add_response(
            'https://api.github.com/user/repos?per_page=100',
            json=[{
                'name': 'some_repo',
                'owner': {'login': 'some_username'}
            }])

        self.add_response(
            'https://api.github.com/users/arbitrary_username/repos?per_page=100',
            json=[{
                'name': 'arbitrary_repo',
                'owner': {'login': 'arbitrary_username'}
            }])

        self.add_response(
            'https://api.github.com/repos/arbitrary_username/arbitrary_repo/issues?per_page=100',
            json=[ARBITRARY_ISSUE])

        self.add_response(
            'https://api.github.com/user/issues?per_page=100',
            json=[ARBITRARY_ISSUE])

        self.add_response(
            'https://api.github.com/repos/arbitrary_username/arbitrary_repo/issues/10/comments?per_page=100',
            json=[{
                'user': {'login': 'arbitrary_login'},
                'body': 'Arbitrary comment.'
            }])

        issue = next(self.service.issues())

        expected = {
            'annotations': [u'@arbitrary_login - Arbitrary comment.'],
            'description': u'(bw)Is#10 - Hallo .. https://github.com/arbitrary_username/arbitrary_repo/pull/1',
            'githubbody': u'Something',
            'githubcreatedon': ARBITRARY_CREATED,
            'githubmilestone': u'alpha',
            'githubnumber': 10,
            'githubrepo': 'arbitrary_username/arbitrary_repo',
            'githubtitle': u'Hallo',
            'githubtype': 'issue',
            'githubupdatedat': ARBITRARY_UPDATED,
            'githuburl': u'https://github.com/arbitrary_username/arbitrary_repo/pull/1',
            'githubuser': u'arbitrary_login',
            'priority': 'M',
            'project': 'arbitrary_repo',
            'tags': []}

        self.assertEqual(issue.get_taskwarrior_record(), expected)


class TestGithubIssueQuery(AbstractServiceTest, ServiceTest):
    maxDiff = None
    SERVICE_CONFIG = {
        'github.login': 'arbitrary_login',
        'github.password': 'arbitrary_password',
        'github.username': 'arbitrary_username',
        'github.query': 'is:open reviewer:octocat',
        'github.include_user_repos': 'False',
        'github.include_user_issues': 'False',
    }

    def setUp(self):
        super(TestGithubIssueQuery, self).setUp()
        self.service = self.get_mock_service(GithubService)

    def test_to_taskwarrior(self):
        pass

    @responses.activate
    def test_issues(self):
        self.add_response(
            'https://api.github.com/search/issues?q=is%3Aopen+reviewer%3Aoctocat&per_page=100',
            json={'items': [ARBITRARY_ISSUE]})

        self.add_response(
            'https://api.github.com/repos/arbitrary_username/arbitrary_repo/issues/10/comments?per_page=100',
            json=[{
                'user': {'login': 'arbitrary_login'},
                'body': 'Arbitrary comment.'
            }])

        issue = list(self.service.issues())[0]

        expected = {
            'annotations': [u'@arbitrary_login - Arbitrary comment.'],
            'description': u'(bw)Is#10 - Hallo .. https://github.com/arbitrary_username/arbitrary_repo/pull/1',
            'githubbody': u'Something',
            'githubcreatedon': ARBITRARY_CREATED,
            'githubmilestone': u'alpha',
            'githubnumber': 10,
            'githubrepo': 'arbitrary_username/arbitrary_repo',
            'githubtitle': u'Hallo',
            'githubtype': 'issue',
            'githubupdatedat': ARBITRARY_UPDATED,
            'githuburl': u'https://github.com/arbitrary_username/arbitrary_repo/pull/1',
            'githubuser': u'arbitrary_login',
            'priority': 'M',
            'project': 'arbitrary_repo',
            'tags': []}

        self.assertEqual(issue.get_taskwarrior_record(), expected)


class TestGithubService(TestCase):

    def test_token_authorization_header(self):
        config = RawConfigParser()
        config.interactive = False
        config.add_section('general')
        config.add_section('mygithub')
        config.set('mygithub', 'service', 'github')
        config.set('mygithub', 'github.login', 'tintin')
        config.set('mygithub', 'github.username', 'tintin')
        config.set('mygithub', 'github.token',
                   '@oracle:eval:echo 1234567890ABCDEF')
        service = GithubService(config, 'general', 'mygithub')
        self.assertEqual(service.client.session.headers['Authorization'],
                         "token 1234567890ABCDEF")
