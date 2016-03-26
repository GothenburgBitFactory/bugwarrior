import datetime

import pytz
import responses

from bugwarrior.services.github import GithubService

from .base import ServiceTest


class TestGithubIssue(ServiceTest):
    maxDiff = None
    SERVICE_CONFIG = {
        'github.login': 'arbitrary_login',
        'github.password': 'arbitrary_password',
        'github.username': 'arbitrary_username',
    }
    arbitrary_created = (
        datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    ).replace(tzinfo=pytz.UTC, microsecond=0)
    arbitrary_updated = datetime.datetime.utcnow().replace(
        tzinfo=pytz.UTC, microsecond=0)
    arbitrary_issue = {
        'title': 'Hallo',
        'html_url': 'http://whanot.com/',
        'url': 'https://api.github.com/repos/arbitrary_username/arbitrary_repo/issues/1',
        'number': 10,
        'body': 'Something',
        'milestone': {'id': 'alpha'},
        'labels': [{'name': 'bugfix'}],
        'created_at': arbitrary_created.isoformat(),
        'updated_at': arbitrary_updated.isoformat(),
        'repo': 'ralphbean/bugwarrior',
    }
    arbitrary_extra = {
        'project': 'one',
        'type': 'issue',
        'annotations': [],
    }

    def setUp(self):
        self.service = self.get_mock_service(GithubService)

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
            'tags': ['bugfix'],
            issue.URL: self.arbitrary_issue['html_url'],
            issue.REPO: self.arbitrary_issue['repo'],
            issue.TYPE: self.arbitrary_extra['type'],
            issue.TITLE: self.arbitrary_issue['title'],
            issue.NUMBER: self.arbitrary_issue['number'],
            issue.UPDATED_AT: self.arbitrary_updated,
            issue.CREATED_AT: self.arbitrary_created,
            issue.BODY: self.arbitrary_issue['body'],
            issue.MILESTONE: self.arbitrary_issue['milestone']['id'],
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

    @responses.activate
    def test_issues(self):
        responses.add(
            responses.GET,
            'https://api.github.com/users/arbitrary_username/repos?per_page=100',
            match_querystring=True,
            json=[{'name': 'arbitrary_repo'}])

        responses.add(
            responses.GET,
            'https://api.github.com/repos/arbitrary_username/arbitrary_repo/issues?per_page=100',
            match_querystring=True,
            json=[self.arbitrary_issue])

        responses.add(
            responses.GET,
            'https://api.github.com/user/issues?per_page=100',
            match_querystring=True,
            json=[self.arbitrary_issue])

        responses.add(
            responses.GET,
            'https://api.github.com/repos/arbitrary_username/arbitrary_repo/issues/10/comments?per_page=100',
            match_querystring=True,
            json=[{
                'user': {'login': 'arbitrary_login'},
                'body': 'Arbitrary comment.'
            }])

        issue = next(self.service.issues())

        self.assertEqual(issue['project'], 'arbitrary_repo')
        self.assertEqual(issue['githubcreatedon'], self.arbitrary_created)
        self.assertEqual(issue['githubnumber'], 10)
        self.assertEqual(issue['githubtitle'], 'Hallo')
        self.assertEqual(issue['tags'], [])
        self.assertEqual(issue['githubtype'], 'issue')
        self.assertEqual(issue['githubbody'], 'Something')
        self.assertEqual(issue['priority'], 'M')
        self.assertEqual(issue['githuburl'], 'http://whanot.com/')
        self.assertEqual(issue['githubupdatedat'], self.arbitrary_updated)
        self.assertEqual(
            issue['githubrepo'], 'arbitrary_username/arbitrary_repo')
        self.assertEqual(issue['githubmilestone'], 'alpha')
        self.assertEqual(
            issue['annotations'], ['@arbitrary_login - Arbitrary comment.'])
        self.assertEqual(
            issue['description'], '(bw)Is#10 - Hallo .. http://whanot.com/')
