import datetime

import pytz
import responses

from bugwarrior.config.load import BugwarriorConfigParser
from bugwarrior.services.gitlab import GitlabService, GitlabClient

from .base import ConfigTest, ServiceTest, AbstractServiceTest


class TestData():
    def __init__(self):
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
            'assignees': [
                {
                    "id": 2,
                    "username": "jack_smith",
                    "email": "jack@example.com",
                    "name": "Jack Smith",
                    "state": "active",
                    "created_at": "2012-05-23T08:01:01Z"
                },
            ],
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
            "work_in_progress": True
        }
        self.arbitrary_extra = {
            'issue_url': 'https://my-git.org/arbitrary_username/project/issues/3',
            'project': 'project',
            'namespace': 'arbitrary_namespace',
            'type': 'issue',
            'annotations': [],
        }
        self.arbitrary_todo = {
            "id": 42,
            "project": {
                "id": 2,
                "name": "project",
                "name_with_namespace": "arbitrary_namespace / project",
                "path": "project",
                "path_with_namespace": "arbitrary_namespace/project"
            },
            "author": {
                "id": 1,
                "username": "john_smith",
                "email": "john@example.com",
                "name": "John Smith",
                "state": "active",
                "created_at": "2012-05-23T08:00:58Z"
            },
            "action_name": "marked",
            "target_type": "Issue",
            "target": {
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
                "work_in_progress": True

            },
            "target_url": "https://my-git.org/arbitrary_username/project/issues/3",
            "body": "Add user settings",
            "state": "pending",
            "created_at": self.arbitrary_created.isoformat(),
            "updated_at": self.arbitrary_updated.isoformat(),
        }
        self.arbitrary_todo_extra = {
            'issue_url': 'https://my-git.org/arbitrary_username/project/issues/3',
            'project': 'project',
            'namespace': 'arbitrary_namespace',
            'type': 'todo',
            'annotations': [],
        }
        self.arbitrary_mr = {
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
            "work_in_progress": True
        }
        self.arbitrary_mr_extra = {
            'issue_url': 'https://my-git.org/arbitrary_username/project/merge_requests/3',
            'project': 'project',
            'namespace': 'arbitrary_namespace',
            'type': 'merge_request',
            'annotations': [],
        }
        self.arbitrary_project = {
            "id": 8,
            "description": "This is the description of an arbitrary project",
            "name": "Arbitrary Project",
            "name_with_namespace": "Arbitrary Namespace / Arbitrary Project",
            "path": "arbitrary_project",
            "path_with_namespace": "arbitrary_namespace/arbitrary_project",
            "created_at": self.arbitrary_created.isoformat(),
            "default_branch": "main",
            "tag_list": [],
            "topics": [],
            "ssh_url_to_repo": "git@my-git.org:arbitrary_namespace/arbitrary_project.git",
            "http_url_to_repo": "https://my-git.org/arbitrary_namespace/arbitrary_project.git",
            "web_url": "https://my-git.org/arbitrary_namespace/arbitrary_project",
            "readme_url":
                "https://my-git.org/arbitrary_namespace/arbitrary_project/-/blob/main/README.md",
            "avatar_url": None,
            "forks_count": 7,
            "star_count": 11,
            "last_activity_at": self.arbitrary_updated.isoformat(),
            "namespace": {
                "id": 2,
                "name": "Arbitrary Namespace",
                "path": "arbitrary_namespace",
                "kind": "group",
                "full_path": "arbitrary_namespace",
                "parent_id": None,
                "avatar_url": None,
                "web_url": "https://my-git.org/groups/arbitrary_namespace"
            },
            "container_registry_image_prefix":
                "my-git.org:5555/arbitrary_namespace/arbitrary_project",
            "_links": {
                "self": "https://my-git.org/api/v4/projects/8",
                "issues": "https://my-git.org/api/v4/projects/8/issues",
                "merge_requests": "https://my-git.org/api/v4/projects/8/merge_requests",
                "repo_branches": "https://my-git.org/api/v4/projects/8/repository/branches",
                "labels": "https://my-git.org/api/v4/projects/8/labels",
                "events": "https://my-git.org/api/v4/projects/8/events",
                "members": "https://my-git.org/api/v4/projects/8/members"
            },
            "packages_enabled": None,
            "empty_repo": False,
            "archived": False,
            "visibility": "private",
            "resolve_outdated_diff_discussions": False,
            "issues_enabled": True,
            "merge_requests_enabled": True,
            "wiki_enabled": True,
            "jobs_enabled": True,
            "snippets_enabled": False,
            "container_registry_enabled": True,
            "service_desk_enabled": False,
            "service_desk_address": None,
            "can_create_merge_request_in": True,
            "issues_access_level": "enabled",
            "repository_access_level": "enabled",
            "merge_requests_access_level": "enabled",
            "forking_access_level": "enabled",
            "wiki_access_level": "enabled",
            "builds_access_level": "private",
            "snippets_access_level": "disabled",
            "pages_access_level": "public",
            "operations_access_level": "enabled",
            "analytics_access_level": "enabled",
            "container_registry_access_level": "enabled",
            "emails_disabled": False,
            "shared_runners_enabled": True,
            "lfs_enabled": True,
            "creator_id": 22,
            "import_status": "finished",
            "import_error": None,
            "open_issues_count": 22,
            "runners_token": None,
            "ci_default_git_depth": None,
            "ci_forward_deployment_enabled": False,
            "ci_job_token_scope_enabled": False,
            "public_jobs": True,
            "build_git_strategy": "fetch",
            "build_timeout": 3600,
            "auto_cancel_pending_pipelines": "enabled",
            "build_coverage_regex": "^TOTAL.+?()$",
            "ci_config_path": "",
            "shared_with_groups": [],
            "only_allow_merge_if_pipeline_succeeds": True,
            "allow_merge_on_skipped_pipeline": False,
            "restrict_user_defined_variables": False,
            "request_access_enabled": True,
            "only_allow_merge_if_all_discussions_are_resolved": True,
            "remove_source_branch_after_merge": True,
            "printing_merge_request_link_enabled": True,
            "merge_method": "ff",
            "squash_option": "default_off",
            "suggestion_commit_message": "",
            "merge_commit_template": None,
            "squash_commit_template": None,
            "auto_devops_enabled": False,
            "auto_devops_deploy_strategy": "continuous",
            "autoclose_referenced_issues": True,
            "repository_storage": "default",
            "keep_latest_artifact": False,
            "permissions": {
                "project_access": None,
                "group_access": None
            }

        }


class TestGitlabClient(ServiceTest):
    def setUp(self):
        super().setUp()
        self.client = GitlabClient('my-git.org',
                                   'XXXXXX',
                                   only_if_assigned='',
                                   also_unassigned=False,
                                   use_https=True,
                                   verify_ssl=True)
        self.data = TestData()

    def test_init(self):
        http_client = GitlabClient('my-git.org',
                                   '12345',
                                   only_if_assigned='',
                                   also_unassigned=False,
                                   use_https=False,
                                   verify_ssl=False)
        expected_base_url = 'http://my-git.org/api/v4/'
        self.assertEqual(expected_base_url, http_client._base_url())
        http_client = GitlabClient('my-git.org',
                                   '12345',
                                   only_if_assigned='',
                                   also_unassigned=False,
                                   use_https=False,
                                   verify_ssl=True)
        expected_base_url = 'http://my-git.org/api/v4/'
        self.assertEqual(expected_base_url, http_client._base_url())
        http_client = GitlabClient('my-git.org',
                                   '12345',
                                   only_if_assigned='',
                                   also_unassigned=False,
                                   use_https=True,
                                   verify_ssl=False)
        expected_base_url = 'https://my-git.org/api/v4/'
        self.assertEqual(expected_base_url, http_client._base_url())
        http_client = GitlabClient('my-git.org',
                                   '12345',
                                   only_if_assigned='',
                                   also_unassigned=False,
                                   use_https=True,
                                   verify_ssl=True)
        expected_base_url = 'https://my-git.org/api/v4/'
        self.assertEqual(expected_base_url, http_client._base_url())

    @responses.activate
    def test_get_repo(self):
        self.add_response(
            'https://my-git.org/api/v4/projects/8',
            json=self.data.arbitrary_project)
        result = self.client.get_repo_cached(repo_id=8)
        self.assertEqual(result, self.data.arbitrary_project)

    @responses.activate
    def test_get_repos(self):
        self.add_response(
            'https://my-git.org/api/v4/projects?simple=True&archived=False&page=1&per_page=100',
            json=[self.data.arbitrary_project])
        self.add_response(
            'https://my-git.org/api/v4/projects' +
            '?simple=True&archived=False&membership=True&page=1&per_page=100',
            json=[self.data.arbitrary_project])
        self.add_response(
            'https://my-git.org/api/v4/projects' +
            '?simple=True&archived=False&owned=True&page=1&per_page=100',
            json=[])
        self.add_response(
            'https://my-git.org/api/v4/projects/' +
            'arbitrary_namespace%2Farbitrary_project?simple=true',
            json=self.data.arbitrary_project)
        self.add_response(
            'https://my-git.org/api/v4/projects/8?simple=true',
            json=self.data.arbitrary_project)
        self.add_response(
            'https://my-git.org/api/v4/projects/non_existing?simple=true',
            json=[])
        self.add_response(
            'https://my-git.org/api/v4/projects' +
            '?simple=True&membership=True&owned=False&page=1&per_page=100',
            json=[self.data.arbitrary_project])
        self.add_response(
            'https://my-git.org/api/v4/projects' +
            '?simple=True&archived=False&membership=True&owned=True&page=1&per_page=100',
            json=[])

        result = self.client.get_repos(include_repos=[], only_membership=False, only_owned=False)
        self.assertEqual(result, [self.data.arbitrary_project])

        result = self.client.get_repos(include_repos=[], only_membership=True, only_owned=False)
        self.assertEqual(result, [self.data.arbitrary_project])

        result = self.client.get_repos(include_repos=[], only_membership=True, only_owned=True)
        self.assertEqual(result, [])

        result = self.client.get_repos(include_repos=['arbitrary_namespace/arbitrary_project'],
                                       only_membership=False, only_owned=False)
        self.assertEqual(result, [self.data.arbitrary_project])

        result = self.client.get_repos(include_repos=['id:8'],
                                       only_membership=False, only_owned=False)
        self.assertEqual(result, [self.data.arbitrary_project])

        result = self.client.get_repos(include_repos=['non_existing'],
                                       only_membership=False, only_owned=False)
        self.assertRaises(OSError)

    @responses.activate
    def test_get_notes(self):
        self.add_response(
            'https://my-git.org/api/v4/projects/8/issues/3/notes?page=1&per_page=100',
            json=[{
                'author': {'username': 'john_smith'},
                'body': 'Some comment.'
            }])
        expected = [{
            'author': {'username': 'john_smith'},
            'body': 'Some comment.'
        }]
        result = self.client.get_notes(
            self.data.arbitrary_issue['project_id'], 'issues', self.data.arbitrary_issue['iid'])
        self.assertEqual(result, expected)

    @responses.activate
    def test_get_repo_issues(self):
        self.add_response(
            'https://my-git.org/api/v4/projects/8/issues?state=opened&page=1&per_page=100',
            json=[self.data.arbitrary_issue])
        self.assertEqual(
            self.client.get_repo_issues(self.data.arbitrary_issue['project_id']),
            {self.data.arbitrary_issue['id']: (
                self.data.arbitrary_issue['project_id'], self.data.arbitrary_issue)}
        )

        client = GitlabClient('old_my-git.org', 'XXXXXX', '', False, True, True)
        self.assertEqual({}, client.get_repo_issues(42))

    @responses.activate
    def test_get_repo_merge_requests(self):
        self.add_response(
            'https://my-git.org/api/v4/projects/8/merge_requests?state=opened&page=1&per_page=100',
            json=[self.data.arbitrary_mr])
        self.assertEqual(
            self.client.get_repo_merge_requests(self.data.arbitrary_issue['project_id']),
            {self.data.arbitrary_mr['id']: (
                self.data.arbitrary_issue['project_id'], self.data.arbitrary_mr)}
        )

        client = GitlabClient('old_my-git.org', 'XXXXXX', '', False, True, True)
        self.assertEqual({}, client.get_repo_merge_requests(42))

    @responses.activate
    def test_get_issues_from_query(self):
        self.add_response(
            'https://my-git.org/api/v4/' +
            'issues?assignee_id=2&state=opened&scope=all&page=1&per_page=100',
            json=[self.data.arbitrary_issue])
        self.assertEqual(
            self.client.get_issues_from_query('issues?assignee_id=2&state=opened&scope=all'),
            {self.data.arbitrary_issue['id']: (
                self.data.arbitrary_issue['project_id'], self.data.arbitrary_issue)}
        )
        self.assertEqual(
            self.client.get_issues_from_query('issues?assignee_id=42&state=opened&scope=all'),
            {}
        )

    @responses.activate
    def test_get_todos(self):
        self.add_response(
            'https://my-git.org/api/v4/todos?state=pending&page=1&per_page=100',
            json=[self.data.arbitrary_todo])
        self.assertEqual(
            self.client.get_todos('todos?state=pending'),
            [(self.data.arbitrary_todo['project'], self.data.arbitrary_todo)]
        )
        # completely unappropriate URL
        self.assertEqual(
            self.client.get_todos('hello'),
            []
        )

        client = GitlabClient('old_my-git.org', 'XXXXXX', '', False, True, True)
        self.assertEqual([], client.get_todos('todos?state=pending'))


class TestGitlabService(ConfigTest):

    def setUp(self):
        super().setUp()
        self.config = BugwarriorConfigParser()
        self.config.add_section('general')
        self.config.set('general', 'targets', 'myservice')
        self.config.add_section('myservice')
        self.config.set('myservice', 'service', 'gitlab')
        self.config.set('myservice', 'gitlab.login', 'foobar')
        self.config.set('myservice', 'gitlab.token', 'XXXXXX')
        self.config.set('myservice', 'gitlab.host', 'gitlab.com')
        self.config.set('myservice', 'gitlab.also_unassigned', 'true')
        self.config.set('myservice', 'gitlab.owned', 'true')

    @property
    def service(self):
        conf = self.validate()
        service = GitlabService(conf['myservice'], conf['general'], 'myservice')
        service.gitlab_client.repo_cache = {1: {
            'id': 1,
            'path_with_namespace': 'arbitrary_namespace/arbitrary_project',
        }}
        return service

    def test_get_keyring_service_default_host(self):
        conf = self.validate()['myservice']
        self.assertEqual(
            GitlabService.get_keyring_service(conf),
            'gitlab://foobar@gitlab.com')

    def test_get_keyring_service_custom_host(self):
        self.config.set('myservice', 'gitlab.host', 'my-git.org')
        conf = self.validate()['myservice']
        self.assertEqual(
            GitlabService.get_keyring_service(conf),
            'gitlab://foobar@my-git.org')

    def test_filter_gitlab_dot_com(self):
        self.config.set('myservice', 'gitlab.host', 'gitlab.com')
        self.config.set('myservice', 'gitlab.owned', 'false')
        self.assertValidationError('You must set at least one of the '
                                   'configuration options to filter '
                                   'repositories')

        self.config.set('myservice', 'gitlab.issue_query', 'arbitrary_query')
        self.config.set('myservice', 'gitlab.merge_request_query', 'arbitrary_query')
        self.config.set('myservice', 'gitlab.todo_query', 'arbitrary_query')
        self.validate()

        self.config.set('myservice', 'gitlab.issue_query', '')
        self.assertValidationError('You must set at least one of the '
                                   'configuration options to filter '
                                   'repositories')

    def test_add_default_namespace_to_included_repos(self):
        self.config.set(
            'myservice', 'gitlab.include_repos', 'baz, banana/tree')
        self.assertEqual(self.service.config.include_repos,
                         ['foobar/baz', 'banana/tree'])

    def test_add_default_namespace_to_excluded_repos(self):
        self.config.set(
            'myservice', 'gitlab.exclude_repos', 'baz, banana/tree')
        self.assertEqual(self.service.config.exclude_repos,
                         ['foobar/baz', 'banana/tree'])

    def test_filter_repos_default(self):
        repo = {'path_with_namespace': 'foobar/baz', 'id': 1234}
        self.assertTrue(self.service.filter_repos(repo))

    def test_filter_repos_exclude(self):
        self.config.set('myservice', 'gitlab.exclude_repos', 'foobar/baz')
        repo = {'path_with_namespace': 'foobar/baz', 'id': 1234}
        self.assertFalse(self.service.filter_repos(repo))

    def test_filter_repos_exclude_id(self):
        self.config.set('myservice', 'gitlab.exclude_repos', 'id:1234')
        repo = {'path_with_namespace': 'foobar/baz', 'id': 1234}
        self.assertFalse(self.service.filter_repos(repo))

    def test_filter_repos_include(self):
        self.config.set('myservice', 'gitlab.include_repos', 'foobar/baz')
        repo = {'path_with_namespace': 'foobar/baz', 'id': 1234}
        self.assertTrue(self.service.filter_repos(repo))

    def test_filter_repos_include_id(self):
        self.config.set('myservice', 'gitlab.include_repos', 'id:1234')
        repo = {'path_with_namespace': 'foobar/baz', 'id': 1234}
        self.assertTrue(self.service.filter_repos(repo))

    def test_include_only_if_assigned(self):
        self.config.set('myservice', 'gitlab.only_if_assigned', 'jack_smith')
        data = TestData()
        self.assertTrue(self.service.include((1, data.arbitrary_issue)))
        self.config.set('myservice', 'gitlab.only_if_assigned', 'smack_jith')
        self.assertFalse(self.service.include((1, data.arbitrary_issue)))

    def test_default_priorities(self):
        self.config.set('myservice', 'gitlab.default_issue_priority', 'L')
        self.config.set('myservice', 'gitlab.default_mr_priority', 'M')
        self.config.set('myservice', 'gitlab.default_todo_priority', 'H')
        self.assertEqual('L', self.service.config.default_issue_priority)
        self.assertEqual('M', self.service.config.default_mr_priority)
        self.assertEqual('H', self.service.config.default_todo_priority)


class TestGitlabIssue(AbstractServiceTest, ServiceTest):
    maxDiff = None
    SERVICE_CONFIG = {
        'service': 'gitlab',
        'gitlab.host': 'my-git.org',
        'gitlab.login': 'arbitrary_login',
        'gitlab.token': 'arbitrary_token',
    }

    def setUp(self):
        super().setUp()
        self.service = self.get_mock_service(GitlabService)

        self.data = TestData()

    def test_to_taskwarrior(self):
        issue = self.service.get_issue_for_record(
            self.data.arbitrary_issue,
            self.data.arbitrary_extra
        )

        expected_output = {
            'project': self.data.arbitrary_extra['project'],
            'priority': self.service.config.default_priority,
            'annotations': [],
            'tags': [],
            'due': self.data.arbitrary_duedate.replace(microsecond=0),
            'entry': self.data.arbitrary_created.replace(microsecond=0),
            issue.URL: self.data.arbitrary_extra['issue_url'],
            issue.REPO: 'project',
            issue.STATE: self.data.arbitrary_issue['state'],
            issue.TYPE: self.data.arbitrary_extra['type'],
            issue.TITLE: self.data.arbitrary_issue['title'],
            issue.NUMBER: str(self.data.arbitrary_issue['iid']),
            issue.UPDATED_AT: self.data.arbitrary_updated.replace(microsecond=0),
            issue.CREATED_AT: self.data.arbitrary_created.replace(microsecond=0),
            issue.DUEDATE: self.data.arbitrary_duedate,
            issue.DESCRIPTION: self.data.arbitrary_issue['description'],
            issue.MILESTONE: self.data.arbitrary_issue['milestone']['title'],
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

    def test_custom_issue_priority(self):
        overrides = {
            'gitlab.default_issue_priority': 'L',
        }
        service = self.get_mock_service(GitlabService, config_overrides=overrides)
        issue = service.get_issue_for_record(
            self.data.arbitrary_issue,
            self.data.arbitrary_extra
        )
        expected_output = {
            'project': self.data.arbitrary_extra['project'],
            'priority': 'L',
            'annotations': [],
            'tags': [],
            'due': self.data.arbitrary_duedate.replace(microsecond=0),
            'entry': self.data.arbitrary_created.replace(microsecond=0),
            issue.URL: self.data.arbitrary_extra['issue_url'],
            issue.REPO: 'project',
            issue.STATE: self.data.arbitrary_issue['state'],
            issue.TYPE: self.data.arbitrary_extra['type'],
            issue.TITLE: self.data.arbitrary_issue['title'],
            issue.NUMBER: str(self.data.arbitrary_issue['iid']),
            issue.UPDATED_AT: self.data.arbitrary_updated.replace(microsecond=0),
            issue.CREATED_AT: self.data.arbitrary_created.replace(microsecond=0),
            issue.DUEDATE: self.data.arbitrary_duedate,
            issue.DESCRIPTION: self.data.arbitrary_issue['description'],
            issue.MILESTONE: self.data.arbitrary_issue['milestone']['title'],
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

    def test_custom_todo_priority(self):
        overrides = {
            'gitlab.default_todo_priority': 'H',
        }
        service = self.get_mock_service(GitlabService, config_overrides=overrides)
        service.import_labels_as_tags = True
        issue = service.get_issue_for_record(
            self.data.arbitrary_todo,
            self.data.arbitrary_todo_extra
        )
        expected_output = {
            'project': self.data.arbitrary_todo_extra['project'],
            'priority': overrides['gitlab.default_todo_priority'],
            'annotations': [],
            'tags': [],
            'due': None,  # currently not parsed for ToDos
            'entry': self.data.arbitrary_created.replace(microsecond=0),
            issue.URL: self.data.arbitrary_todo_extra['issue_url'],
            issue.REPO: 'project',
            issue.STATE: self.data.arbitrary_todo['state'],
            issue.TYPE: self.data.arbitrary_todo_extra['type'],
            issue.TITLE: 'Todo from %s for %s' % (self.data.arbitrary_todo['author']['name'],
                                                  self.data.arbitrary_todo['project']['path']),
            issue.NUMBER: str(self.data.arbitrary_todo['id']),
            issue.UPDATED_AT: self.data.arbitrary_updated.replace(microsecond=0),
            issue.CREATED_AT: self.data.arbitrary_created.replace(microsecond=0),
            issue.DUEDATE: None,  # Currently not parsed for ToDos
            issue.DESCRIPTION: self.data.arbitrary_todo['body'],
            issue.MILESTONE: None,
            issue.UPVOTES: 0,
            issue.DOWNVOTES: 0,
            issue.WORK_IN_PROGRESS: 0,
            issue.AUTHOR: 'john_smith',
            issue.ASSIGNEE: None,  # Currently not parsed for ToDos
            issue.NAMESPACE: 'arbitrary_namespace',
            issue.WEIGHT: None,  # Currently not parsed for ToDos
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

    def test_custom_mr_priority(self):
        overrides = {
            'gitlab.default_mr_priority': '',
            'gitlab.import_labels_as_tags': True,
        }
        service = self.get_mock_service(GitlabService, config_overrides=overrides)
        issue = service.get_issue_for_record(
            self.data.arbitrary_mr,
            self.data.arbitrary_mr_extra
        )
        expected_output = {
            'project': self.data.arbitrary_mr_extra['project'],
            'priority': overrides['gitlab.default_mr_priority'],
            'annotations': [],
            'tags': ['feature'],
            'due': self.data.arbitrary_duedate.replace(microsecond=0),
            'entry': self.data.arbitrary_created.replace(microsecond=0),
            issue.URL: self.data.arbitrary_mr_extra['issue_url'],
            issue.REPO: 'project',
            issue.STATE: self.data.arbitrary_mr['state'],
            issue.TYPE: self.data.arbitrary_mr_extra['type'],
            issue.TITLE: self.data.arbitrary_mr['title'],
            issue.NUMBER: str(self.data.arbitrary_mr['iid']),
            issue.UPDATED_AT: self.data.arbitrary_updated.replace(microsecond=0),
            issue.CREATED_AT: self.data.arbitrary_created.replace(microsecond=0),
            issue.DUEDATE: self.data.arbitrary_duedate,
            issue.DESCRIPTION: self.data.arbitrary_mr['description'],
            issue.MILESTONE: self.data.arbitrary_issue['milestone']['title'],
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
        self.data.arbitrary_issue['work_in_progress'] = False
        issue = self.service.get_issue_for_record(
            self.data.arbitrary_issue,
            self.data.arbitrary_extra
        )

        expected_output = {
            'project': self.data.arbitrary_extra['project'],
            'priority': self.service.config.default_priority,
            'annotations': [],
            'tags': [],
            'due': self.data.arbitrary_duedate.replace(microsecond=0),
            'entry': self.data.arbitrary_created.replace(microsecond=0),
            issue.URL: self.data.arbitrary_extra['issue_url'],
            issue.REPO: 'project',
            issue.STATE: self.data.arbitrary_issue['state'],
            issue.TYPE: self.data.arbitrary_extra['type'],
            issue.TITLE: self.data.arbitrary_issue['title'],
            issue.NUMBER: str(self.data.arbitrary_issue['iid']),
            issue.UPDATED_AT: self.data.arbitrary_updated.replace(microsecond=0),
            issue.CREATED_AT: self.data.arbitrary_created.replace(microsecond=0),
            issue.DUEDATE: self.data.arbitrary_duedate,
            issue.DESCRIPTION: self.data.arbitrary_issue['description'],
            issue.MILESTONE: self.data.arbitrary_issue['milestone']['title'],
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
    def test_issues_from_query(self):
        overrides = {
            'gitlab.issue_query': 'issues?state=opened',
        }
        service = self.get_mock_service(GitlabService, config_overrides=overrides)
        self.add_response(
            'https://my-git.org/api/v4/issues?state=opened&per_page=100&page=1',
            json=[self.data.arbitrary_issue])
        self.add_response(
            'https://my-git.org/api/v4/projects/8',
            json={
                'id': 8,
                'path': 'arbitrary_username/project',
                'web_url': 'example.com',
                "namespace": {
                    "full_path": "arbitrary_username"
                },
                'path_with_namespace': 'arbitrary_username/project'
            })
        self.add_response(
            'https://my-git.org/api/v4/projects/8/issues/3/notes?page=1&per_page=100',
            json=[{
                'author': {'username': 'john_smith'},
                'body': 'Some comment.'
            }])
        issue = next(service.issues())
        expected = {
            'annotations': ['@john_smith - Some comment.'],
            'description':
                '(bw)Is#3 - Add user settings .. example.com/issues/3',
            'due': self.data.arbitrary_duedate,
            'entry': self.data.arbitrary_created,
            'gitlabassignee': 'jack_smith',
            'gitlabauthor': 'john_smith',
            'gitlabcreatedon': self.data.arbitrary_created,
            'gitlabdescription': '',
            'gitlabdownvotes': 0,
            'gitlabmilestone': 'v1.0',
            'gitlabnamespace': 'arbitrary_username',
            'gitlabnumber': '3',
            'gitlabrepo': 'arbitrary_username/project',
            'gitlabstate': 'opened',
            'gitlabtitle': 'Add user settings',
            'gitlabtype': 'issue',
            'gitlabupdatedat': self.data.arbitrary_updated,
            'gitlabduedate': self.data.arbitrary_duedate,
            'gitlabupvotes': 0,
            'gitlaburl': 'example.com/issues/3',
            'gitlabwip': 1,
            'gitlabweight': 3,
            'priority': 'M',
            'project': 'arbitrary_username/project',
            'tags': []}
        self.assertEqual(issue.get_taskwarrior_record(), expected)

    @responses.activate
    def test_mrs_from_query(self):
        overrides = {
            'gitlab.include_issues': 'false',
            'gitlab.include_todos': 'false',
            'gitlab.include_merge_requests': 'true',
            'gitlab.merge_request_query': 'merge_requests?state=opened'
        }
        service = self.get_mock_service(GitlabService, config_overrides=overrides)
        self.add_response(
            'https://my-git.org/api/v4/merge_requests?state=opened&per_page=100&page=1',
            json=[self.data.arbitrary_mr])
        self.add_response(
            'https://my-git.org/api/v4/projects/8',
            json={
                'id': 8,
                'path': 'arbitrary_username/project',
                'web_url': 'example.com',
                "namespace": {
                    "full_path": "arbitrary_username"
                },
                'path_with_namespace': 'arbitrary_username/project'
            })
        self.add_response(
            'https://my-git.org/api/v4/projects/8/' +
            'merge_requests/3/notes?page=1&per_page=100',
            json=[{
                'author': {'username': 'john_smith'},
                'body': 'Some comment.'
            }])
        mr = next(service.issues())
        expected = {
            'annotations': ['@john_smith - Some comment.'],
            'description':
                '(bw)MR#3 - Add user settings .. example.com/merge_requests/3',
            'due': self.data.arbitrary_duedate,
            'entry': self.data.arbitrary_created,
            'gitlabassignee': 'jack_smith',
            'gitlabauthor': 'john_smith',
            'gitlabcreatedon': self.data.arbitrary_created,
            'gitlabdescription': '',
            'gitlabdownvotes': 0,
            'gitlabmilestone': 'v1.0',
            'gitlabnamespace': 'arbitrary_username',
            'gitlabnumber': '3',
            'gitlabrepo': 'arbitrary_username/project',
            'gitlabstate': 'opened',
            'gitlabtitle': 'Add user settings',
            'gitlabtype': 'merge_request',
            'gitlabupdatedat': self.data.arbitrary_updated,
            'gitlabduedate': self.data.arbitrary_duedate,
            'gitlabupvotes': 0,
            'gitlaburl': 'example.com/merge_requests/3',
            'gitlabwip': 1,
            'gitlabweight': 3,
            'priority': 'M',
            'project': 'arbitrary_username/project',
            'tags': []}
        self.assertEqual(mr.get_taskwarrior_record(), expected)

    @responses.activate
    def test_todos_from_query(self):
        overrides = {
            'gitlab.include_issues': 'false',
            'gitlab.include_merge_requests': 'false',
            'gitlab.include_todos': 'true',
            'gitlab.todo_query': 'todos?state=pending'
        }
        service = self.get_mock_service(GitlabService, config_overrides=overrides)
        self.add_response(
            'https://my-git.org/api/v4/todos?state=pending&per_page=100&page=1',
            json=[self.data.arbitrary_todo])
        self.add_response(
            'https://my-git.org/api/v4/projects/2',
            json={
                "id": 2,
                'path': 'arbitrary_namespace/project',
                'web_url': 'example.com',
                "namespace": {
                    "full_path": "arbitrary_namespace"
                },
                'path_with_namespace': 'arbitrary_namespace/project'
            })
        self.add_response(
            'https://my-git.org/api/v4/projects/arbitrary_namespace%2Fproject?simple=true',
            json={
                'id': 2,
                'path': 'arbitrary_namespace/project',
                'web_url': 'example.com',
                "namespace": {
                    "full_path": "arbitrary_namespace"
                },
                'path_with_namespace': 'arbitrary_namespace/project'
            })
        todo = next(service.issues())
        expected = {
            'annotations': [],
            'description': '(bw)# - Todo from John Smith for project .. '
                           'https://my-git.org/arbitrary_username/project/issues/3',
            'due': None,
            'entry': self.data.arbitrary_created,
            'gitlabassignee': None,
            'gitlabauthor': 'john_smith',
            'gitlabcreatedon': self.data.arbitrary_created,
            'gitlabdescription': 'Add user settings',
            'gitlabdownvotes': 0,
            'gitlabmilestone': None,
            'gitlabnamespace': 'todo',
            'gitlabnumber': '42',
            'gitlabrepo': 'project',
            'gitlabstate': 'pending',
            'gitlabtitle': 'Todo from John Smith for project',
            'gitlabtype': 'todo',
            'gitlabupdatedat': self.data.arbitrary_updated,
            'gitlabduedate': None,
            'gitlabupvotes': 0,
            'gitlaburl': 'https://my-git.org/arbitrary_username/project/issues/3',
            'gitlabwip': 0,
            'gitlabweight': None,
            'priority': 'M',
            'project': 'project',
            'tags': []}
        self.assertEqual(todo.get_taskwarrior_record(), expected)

        overrides = {
            'gitlab.include_issues': 'false',
            'gitlab.include_merge_requests': 'false',
            'gitlab.include_todos': 'true',
            'gitlab.include_repos': 'arbitrary_namespace/project',
            'gitlab.include_all_todos': 'false'
        }
        service = self.get_mock_service(GitlabService, config_overrides=overrides)
        todo = next(service.issues())
        self.assertEqual(todo.get_taskwarrior_record(), expected)

    @responses.activate
    def test_issues(self):
        self.add_response(
            'https://my-git.org/api/v4/projects?simple=True&archived=False&per_page=100&page=1',
            json=[{
                'id': 8,
                'path': 'arbitrary_username/project',
                'web_url': 'example.com',
                "namespace": {
                    "full_path": "arbitrary_username"
                },
                'path_with_namespace': 'arbitrary_username/project'
            }])

        self.add_response(
            'https://my-git.org/api/v4/projects/8/issues?state=opened&per_page=100&page=1',
            json=[self.data.arbitrary_issue])

        self.add_response(
            'https://my-git.org/api/v4/projects/8/issues/3/notes?per_page=100&page=1',
            json=[{
                'author': {'username': 'john_smith'},
                'body': 'Some comment.'
            }])

        issue = next(self.service.issues())

        expected = {
            'annotations': ['@john_smith - Some comment.'],
            'description':
                '(bw)Is#3 - Add user settings .. example.com/issues/3',
            'due': self.data.arbitrary_duedate,
            'entry': self.data.arbitrary_created,
            'gitlabassignee': 'jack_smith',
            'gitlabauthor': 'john_smith',
            'gitlabcreatedon': self.data.arbitrary_created,
            'gitlabdescription': '',
            'gitlabdownvotes': 0,
            'gitlabmilestone': 'v1.0',
            'gitlabnamespace': 'arbitrary_username',
            'gitlabnumber': '3',
            'gitlabrepo': 'arbitrary_username/project',
            'gitlabstate': 'opened',
            'gitlabtitle': 'Add user settings',
            'gitlabtype': 'issue',
            'gitlabupdatedat': self.data.arbitrary_updated,
            'gitlabduedate': self.data.arbitrary_duedate,
            'gitlabupvotes': 0,
            'gitlaburl': 'example.com/issues/3',
            'gitlabwip': 1,
            'gitlabweight': 3,
            'priority': 'M',
            'project': 'arbitrary_username/project',
            'tags': []}

        self.assertEqual(issue.get_taskwarrior_record(), expected)
