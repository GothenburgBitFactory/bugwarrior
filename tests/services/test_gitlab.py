from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
import responses

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.gitlab import GitlabClient, GitlabService

from ..base import get_validated_service, validate
from .base import get_mock_service


@pytest.fixture
def data():
    created = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(microsecond=0)
    updated = datetime.now(timezone.utc).replace(microsecond=0)
    duedate = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)
    issue = {
        "id": 42,
        "iid": 3,
        "project_id": 8,
        "title": "Add user settings",
        "description": "",
        "labels": ["feature"],
        "milestone": {
            "id": 1,
            "title": "v1.0",
            "description": "",
            "due_date": duedate.date().isoformat(),
            "state": "closed",
            "updated_at": "2012-07-04T13:42:48Z",
            "created_at": "2012-07-04T13:42:48Z",
        },
        "assignee": {
            "id": 2,
            "username": "jack_smith",
            "email": "jack@example.com",
            "name": "Jack Smith",
            "state": "active",
            "created_at": "2012-05-23T08:01:01Z",
        },
        'assignees': [
            {
                "id": 2,
                "username": "jack_smith",
                "email": "jack@example.com",
                "name": "Jack Smith",
                "state": "active",
                "created_at": "2012-05-23T08:01:01Z",
            }
        ],
        "author": {
            "id": 1,
            "username": "john_smith",
            "email": "john@example.com",
            "name": "John Smith",
            "state": "active",
            "created_at": "2012-05-23T08:00:58Z",
        },
        "state": "opened",
        "updated_at": updated.isoformat(),
        "created_at": created.isoformat(),
        "weight": 3,
        "work_in_progress": True,
    }
    extra = {
        'issue_url': 'https://my-git.org/arbitrary_username/project/issues/3',
        'project': 'project',
        'namespace': 'arbitrary_namespace',
        'type': 'issue',
        'annotations': [],
        'description': '',
    }
    todo = {
        "id": 42,
        "project": {
            "id": 2,
            "name": "project",
            "name_with_namespace": "arbitrary_namespace / project",
            "path": "project",
            "path_with_namespace": "arbitrary_namespace/project",
        },
        "author": {
            "id": 1,
            "username": "john_smith",
            "email": "john@example.com",
            "name": "John Smith",
            "state": "active",
            "created_at": "2012-05-23T08:00:58Z",
        },
        "action_name": "marked",
        "target_type": "Issue",
        "target": {
            "id": 42,
            "iid": 3,
            "project_id": 8,
            "title": "Add user settings",
            "description": "",
            "labels": ["feature"],
            "milestone": {
                "id": 1,
                "title": "v1.0",
                "description": "",
                "due_date": duedate.date().isoformat(),
                "state": "closed",
                "updated_at": "2012-07-04T13:42:48Z",
                "created_at": "2012-07-04T13:42:48Z",
            },
            "assignee": {
                "id": 2,
                "username": "jack_smith",
                "email": "jack@example.com",
                "name": "Jack Smith",
                "state": "active",
                "created_at": "2012-05-23T08:01:01Z",
            },
            "author": {
                "id": 1,
                "username": "john_smith",
                "email": "john@example.com",
                "name": "John Smith",
                "state": "active",
                "created_at": "2012-05-23T08:00:58Z",
            },
            "state": "opened",
            "updated_at": updated.isoformat(),
            "created_at": created.isoformat(),
            "weight": 3,
            "work_in_progress": True,
        },
        "target_url": "https://my-git.org/arbitrary_username/project/issues/3",
        "body": "Add user settings",
        "state": "pending",
        "created_at": created.isoformat(),
        "updated_at": updated.isoformat(),
    }
    todo_extra = {
        'issue_url': 'https://my-git.org/arbitrary_username/project/issues/3',
        'project': 'project',
        'namespace': 'arbitrary_namespace',
        'type': 'todo',
        'annotations': [],
    }
    mr = {
        "id": 42,
        "iid": 3,
        "project_id": 8,
        "title": "Add user settings",
        "description": "",
        "labels": ["feature"],
        "milestone": {
            "id": 1,
            "title": "v1.0",
            "description": "",
            "due_date": duedate.date().isoformat(),
            "state": "closed",
            "updated_at": "2012-07-04T13:42:48Z",
            "created_at": "2012-07-04T13:42:48Z",
        },
        "assignee": {
            "id": 2,
            "username": "jack_smith",
            "email": "jack@example.com",
            "name": "Jack Smith",
            "state": "active",
            "created_at": "2012-05-23T08:01:01Z",
        },
        "author": {
            "id": 1,
            "username": "john_smith",
            "email": "john@example.com",
            "name": "John Smith",
            "state": "active",
            "created_at": "2012-05-23T08:00:58Z",
        },
        "state": "opened",
        "updated_at": updated.isoformat(),
        "created_at": created.isoformat(),
        "weight": 3,
        "work_in_progress": True,
    }
    mr_extra = {
        'issue_url': 'https://my-git.org/arbitrary_username/project/merge_requests/3',
        'project': 'project',
        'namespace': 'arbitrary_namespace',
        'type': 'merge_request',
        'annotations': [],
        "description": "",
    }
    project = {
        "id": 8,
        "description": "This is the description of an arbitrary project",
        "name": "Arbitrary Project",
        "name_with_namespace": "Arbitrary Namespace / Arbitrary Project",
        "path": "arbitrary_project",
        "path_with_namespace": "arbitrary_namespace/arbitrary_project",
        "created_at": created.isoformat(),
        "default_branch": "main",
        "tag_list": [],
        "topics": [],
        "ssh_url_to_repo": "git@my-git.org:arbitrary_namespace/arbitrary_project.git",
        "http_url_to_repo": "https://my-git.org/arbitrary_namespace/arbitrary_project.git",
        "web_url": "https://my-git.org/arbitrary_namespace/arbitrary_project",
        "readme_url": "https://my-git.org/arbitrary_namespace/arbitrary_project/-/blob/main/README.md",
        "avatar_url": None,
        "forks_count": 7,
        "star_count": 11,
        "last_activity_at": updated.isoformat(),
        "namespace": {
            "id": 2,
            "name": "Arbitrary Namespace",
            "path": "arbitrary_namespace",
            "kind": "group",
            "full_path": "arbitrary_namespace",
            "parent_id": None,
            "avatar_url": None,
            "web_url": "https://my-git.org/groups/arbitrary_namespace",
        },
        "container_registry_image_prefix": (
            "my-git.org:5555/arbitrary_namespace/arbitrary_project"
        ),
        "_links": {
            "self": "https://my-git.org/api/v4/projects/8",
            "issues": "https://my-git.org/api/v4/projects/8/issues",
            "merge_requests": "https://my-git.org/api/v4/projects/8/merge_requests",
            "repo_branches": "https://my-git.org/api/v4/projects/8/repository/branches",
            "labels": "https://my-git.org/api/v4/projects/8/labels",
            "events": "https://my-git.org/api/v4/projects/8/events",
            "members": "https://my-git.org/api/v4/projects/8/members",
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
        "permissions": {"project_access": None, "group_access": None},
    }
    return SimpleNamespace(
        created=created,
        updated=updated,
        duedate=duedate,
        issue=issue,
        extra=extra,
        todo=todo,
        todo_extra=todo_extra,
        mr=mr,
        mr_extra=mr_extra,
        project=project,
    )


SERVICE_CONFIG = {
    'service': 'gitlab',
    'host': 'my-git.org',
    'login': 'arbitrary_login',
    'token': 'arbitrary_token',
}


class TestGitlabClient:
    @pytest.fixture
    def client(self):
        return GitlabClient(
            'my-git.org',
            'XXXXXX',
            only_if_assigned='',
            also_unassigned=False,
            use_https=True,
            verify_ssl=True,
        )

    def test_init(self):
        http_client = GitlabClient(
            'my-git.org',
            '12345',
            only_if_assigned='',
            also_unassigned=False,
            use_https=False,
            verify_ssl=False,
        )
        expected_base_url = 'http://my-git.org/api/v4/'
        assert expected_base_url == http_client._base_url()
        http_client = GitlabClient(
            'my-git.org',
            '12345',
            only_if_assigned='',
            also_unassigned=False,
            use_https=False,
            verify_ssl=True,
        )
        expected_base_url = 'http://my-git.org/api/v4/'
        assert expected_base_url == http_client._base_url()
        http_client = GitlabClient(
            'my-git.org',
            '12345',
            only_if_assigned='',
            also_unassigned=False,
            use_https=True,
            verify_ssl=False,
        )
        expected_base_url = 'https://my-git.org/api/v4/'
        assert expected_base_url == http_client._base_url()
        http_client = GitlabClient(
            'my-git.org',
            '12345',
            only_if_assigned='',
            also_unassigned=False,
            use_https=True,
            verify_ssl=True,
        )
        expected_base_url = 'https://my-git.org/api/v4/'
        assert expected_base_url == http_client._base_url()

    @responses.activate
    def test_get_repo(self, client, data):
        responses.get('https://my-git.org/api/v4/projects/8', json=data.project)
        result = client.get_repo_cached(repo_id=8)
        assert result == data.project

    @responses.activate
    def test_get_repos(self, client, data):
        responses.get(
            'https://my-git.org/api/v4/projects?simple=True&archived=False&page=1&per_page=100',
            json=[data.project],
        )
        responses.get(
            'https://my-git.org/api/v4/projects'
            + '?simple=True&archived=False&membership=True&page=1&per_page=100',
            json=[data.project],
        )
        responses.get(
            'https://my-git.org/api/v4/projects'
            + '?simple=True&archived=False&owned=True&page=1&per_page=100',
            json=[],
        )
        responses.get(
            'https://my-git.org/api/v4/projects/'
            + 'arbitrary_namespace%2Farbitrary_project?simple=true',
            json=data.project,
        )
        responses.get(
            'https://my-git.org/api/v4/projects/8?simple=true', json=data.project
        )
        responses.get(
            'https://my-git.org/api/v4/projects/non_existing?simple=true', json=[]
        )
        responses.get(
            'https://my-git.org/api/v4/projects'
            + '?simple=True&membership=True&owned=False&page=1&per_page=100',
            json=[data.project],
        )
        responses.get(
            'https://my-git.org/api/v4/projects'
            + '?simple=True&archived=False&membership=True&owned=True&page=1&per_page=100',
            json=[],
        )

        result = client.get_repos(
            include_repos=[], only_membership=False, only_owned=False
        )
        assert result == [data.project]

        result = client.get_repos(
            include_repos=[], only_membership=True, only_owned=False
        )
        assert result == [data.project]

        result = client.get_repos(
            include_repos=[], only_membership=True, only_owned=True
        )
        assert result == []

        result = client.get_repos(
            include_repos=['arbitrary_namespace/arbitrary_project'],
            only_membership=False,
            only_owned=False,
        )
        assert result == [data.project]

        result = client.get_repos(
            include_repos=['id:8'], only_membership=False, only_owned=False
        )
        assert result == [data.project]

        # A repo that cannot be fetched is skipped rather than included.
        result = client.get_repos(
            include_repos=['non_existing'], only_membership=False, only_owned=False
        )
        assert result == []

    @responses.activate
    def test_get_notes(self, client, data):
        responses.get(
            'https://my-git.org/api/v4/projects/8/issues/3/notes?page=1&per_page=100',
            json=[{'author': {'username': 'john_smith'}, 'body': 'Some comment.'}],
        )
        expected = [{'author': {'username': 'john_smith'}, 'body': 'Some comment.'}]
        result = client.get_notes(data.issue['project_id'], 'issues', data.issue['iid'])
        assert result == expected

    @responses.activate
    def test_get_repo_issues(self, client, data):
        responses.get(
            'https://my-git.org/api/v4/projects/8/issues?state=opened&page=1&per_page=100',
            json=[data.issue],
        )
        assert client.get_repo_issues(data.issue['project_id']) == {
            data.issue['id']: (data.issue['project_id'], data.issue)
        }

    @responses.activate
    def test_get_repo_merge_requests(self, client, data):
        responses.get(
            'https://my-git.org/api/v4/projects/8/merge_requests?state=opened&page=1&per_page=100',
            json=[data.mr],
        )
        assert client.get_repo_merge_requests(data.issue['project_id']) == {
            data.mr['id']: (data.issue['project_id'], data.mr)
        }

    @responses.activate
    def test_get_issues_from_query(self, client, data):
        responses.get(
            'https://my-git.org/api/v4/'
            + 'issues?assignee_id=2&state=opened&scope=all&page=1&per_page=100',
            json=[data.issue],
        )
        assert client.get_issues_from_query(
            'issues?assignee_id=2&state=opened&scope=all'
        ) == {data.issue['id']: (data.issue['project_id'], data.issue)}

    @responses.activate
    def test_get_todos(self, client, data):
        responses.get(
            'https://my-git.org/api/v4/todos?state=pending&page=1&per_page=100',
            json=[data.todo],
        )
        assert client.get_todos('todos?state=pending') == [
            (data.todo['project'], data.todo)
        ]


class TestGitlabService:
    @pytest.fixture
    def config(self):
        return {
            'general': {'targets': ['myservice']},
            'myservice': {
                'service': 'gitlab',
                'login': 'foobar',
                'token': 'XXXXXX',
                'host': 'gitlab.com',
                'also_unassigned': 'true',
                'owned': 'true',
            },
        }

    def get_service(self, config):
        service = get_validated_service(config)
        service.gitlab_client.repo_cache = {
            1: {'id': 1, 'path_with_namespace': 'arbitrary_namespace/arbitrary_project'}
        }
        return service

    def test_keyring_service_default_host(self, config):
        conf = validate(config)
        conf = conf.service_configs[0]
        assert conf.keyring_service == 'gitlab://foobar@gitlab.com'

    def test_keyring_service_custom_host(self, config):
        config['myservice']['host'] = 'my-git.org'
        conf = validate(config)
        conf = conf.service_configs[0]
        assert conf.keyring_service == 'gitlab://foobar@my-git.org'

    def test_filter_gitlab_dot_com(self, config, assert_validation_error):
        config['myservice'].update({'host': 'gitlab.com', 'owned': 'false'})
        assert_validation_error(
            config,
            'You must set at least one of the '
            'configuration options to filter '
            'repositories',
        )

        config['myservice'].update(
            {
                'issue_query': 'arbitrary_query',
                'merge_request_query': 'arbitrary_query',
                'todo_query': 'arbitrary_query',
            }
        )
        validate(config)

        config['myservice']['issue_query'] = ''
        assert_validation_error(
            config,
            'You must set at least one of the '
            'configuration options to filter '
            'repositories',
        )

    def test_add_default_namespace_to_included_repos(self, config):
        config['myservice']['include_repos'] = 'baz, banana/tree'
        service = self.get_service(config)
        assert service.config.include_repos == ['foobar/baz', 'banana/tree']

    def test_add_default_namespace_to_excluded_repos(self, config):
        config['myservice']['exclude_repos'] = 'baz, banana/tree'
        service = self.get_service(config)
        assert service.config.exclude_repos == ['foobar/baz', 'banana/tree']

    def test_filter_repos_default(self, config):
        repo = {'path_with_namespace': 'foobar/baz', 'id': 1234}
        assert self.get_service(config).filter_repos(repo)

    def test_filter_repos_exclude(self, config):
        config['myservice']['exclude_repos'] = 'foobar/baz'
        repo = {'path_with_namespace': 'foobar/baz', 'id': 1234}
        assert not self.get_service(config).filter_repos(repo)

    def test_filter_repos_exclude_id(self, config):
        config['myservice']['exclude_repos'] = 'id:1234'
        repo = {'path_with_namespace': 'foobar/baz', 'id': 1234}
        assert not self.get_service(config).filter_repos(repo)

    def test_filter_repos_include(self, config):
        config['myservice']['include_repos'] = 'foobar/baz'
        repo = {'path_with_namespace': 'foobar/baz', 'id': 1234}
        assert self.get_service(config).filter_repos(repo)

    def test_filter_repos_include_id(self, config):
        config['myservice']['include_repos'] = 'id:1234'
        repo = {'path_with_namespace': 'foobar/baz', 'id': 1234}
        assert self.get_service(config).filter_repos(repo)

    def test_include_only_if_assigned(self, config, data):
        config['myservice']['only_if_assigned'] = 'jack_smith'
        assert self.get_service(config).include((1, data.issue))
        config['myservice']['only_if_assigned'] = 'smack_jith'
        assert not self.get_service(config).include((1, data.issue))

    def test_default_priorities(self, config):
        config['myservice'].update(
            {
                'default_issue_priority': 'L',
                'default_mr_priority': 'M',
                'default_todo_priority': 'H',
            }
        )
        service = self.get_service(config)
        assert 'L' == service.config.default_issue_priority
        assert 'M' == service.config.default_mr_priority
        assert 'H' == service.config.default_todo_priority

    def test_default_priorities_fallback(self, config):
        config['myservice']['default_priority'] = 'H'
        service = self.get_service(config)
        assert 'H' == service.config.default_issue_priority
        assert 'H' == service.config.default_mr_priority
        assert 'H' == service.config.default_todo_priority

    def test_body_zero_limit(self, config):
        config['myservice']['body_length'] = 0
        issue = dict(description="A very short issue body.  Fixes #42.")
        assert "" == self.get_service(config).description(issue)

    def test_body_short_limit(self, config):
        size_limit = 5
        config['myservice']['body_length'] = size_limit
        issue = dict(description="A very short issue body.  Fixes #42.")
        assert issue["description"][:size_limit] == self.get_service(
            config
        ).description(issue)

    def test_body_no_limit(self, config):
        issue = dict(description="A very short issue body.  Fixes #42.")
        assert issue["description"] == self.get_service(config).description(issue)

    def test_undefined_owned_warning(self, config, caplog):
        config['myservice'].pop('owned')
        config['myservice']['membership'] = 'true'
        validate(config)
        assert len(caplog.records) == 1
        assert (
            "WARNING: Gitlab's 'owned' configuration field should be set "
            "explicitly. In a future release, this will be an error."
            in caplog.records[0].message
        )


class TestGitlabIssue:
    @pytest.fixture
    def service(self):
        return get_mock_service(GitlabService, SERVICE_CONFIG)

    def test_to_taskwarrior(self, service, data):
        issue = service.get_issue_for_record(data.issue, data.extra)

        expected_output = {
            'project': data.extra['project'],
            'priority': service.config.default_priority,
            'annotations': [],
            'tags': [],
            'due': data.duedate.replace(microsecond=0),
            'entry': data.created.replace(microsecond=0),
            issue.URL: data.extra['issue_url'],
            issue.REPO: 'project',
            issue.STATE: data.issue['state'],
            issue.TYPE: data.extra['type'],
            issue.TITLE: data.issue['title'],
            issue.NUMBER: str(data.issue['iid']),
            issue.UPDATED_AT: data.updated.replace(microsecond=0),
            issue.CREATED_AT: data.created.replace(microsecond=0),
            issue.DUEDATE: data.duedate,
            issue.DESCRIPTION: data.issue['description'],
            issue.MILESTONE: data.issue['milestone']['title'],
            issue.UPVOTES: 0,
            issue.DOWNVOTES: 0,
            issue.WORK_IN_PROGRESS: 1,
            issue.AUTHOR: 'john_smith',
            issue.ASSIGNEE: 'jack_smith',
            issue.NAMESPACE: 'arbitrary_namespace',
            issue.WEIGHT: 3,
        }
        actual_output = issue.to_taskwarrior()

        assert actual_output == expected_output

    def test_custom_issue_priority(self, data):
        overrides = {'default_issue_priority': 'L'}
        service = get_mock_service(GitlabService, {**SERVICE_CONFIG, **overrides})
        issue = service.get_issue_for_record(data.issue, data.extra)
        expected_output = {
            'project': data.extra['project'],
            'priority': 'L',
            'annotations': [],
            'tags': [],
            'due': data.duedate.replace(microsecond=0),
            'entry': data.created.replace(microsecond=0),
            issue.URL: data.extra['issue_url'],
            issue.REPO: 'project',
            issue.STATE: data.issue['state'],
            issue.TYPE: data.extra['type'],
            issue.TITLE: data.issue['title'],
            issue.NUMBER: str(data.issue['iid']),
            issue.UPDATED_AT: data.updated.replace(microsecond=0),
            issue.CREATED_AT: data.created.replace(microsecond=0),
            issue.DUEDATE: data.duedate,
            issue.DESCRIPTION: data.issue['description'],
            issue.MILESTONE: data.issue['milestone']['title'],
            issue.UPVOTES: 0,
            issue.DOWNVOTES: 0,
            issue.WORK_IN_PROGRESS: 1,
            issue.AUTHOR: 'john_smith',
            issue.ASSIGNEE: 'jack_smith',
            issue.NAMESPACE: 'arbitrary_namespace',
            issue.WEIGHT: 3,
        }
        actual_output = issue.to_taskwarrior()

        assert actual_output == expected_output

    def test_custom_todo_priority(self, data):
        overrides = {'default_todo_priority': 'H'}
        service = get_mock_service(GitlabService, {**SERVICE_CONFIG, **overrides})
        service.import_labels_as_tags = True
        issue = service.get_issue_for_record(data.todo, data.todo_extra)
        expected_output = {
            'project': data.todo_extra['project'],
            'priority': overrides['default_todo_priority'],
            'annotations': [],
            'tags': [],
            'due': None,  # currently not parsed for ToDos
            'entry': data.created.replace(microsecond=0),
            issue.URL: data.todo_extra['issue_url'],
            issue.REPO: 'project',
            issue.STATE: data.todo['state'],
            issue.TYPE: data.todo_extra['type'],
            issue.TITLE: 'Todo from %s for %s'
            % (data.todo['author']['name'], data.todo['project']['path']),
            issue.NUMBER: str(data.todo['id']),
            issue.UPDATED_AT: data.updated.replace(microsecond=0),
            issue.CREATED_AT: data.created.replace(microsecond=0),
            issue.DUEDATE: None,  # Currently not parsed for ToDos
            issue.DESCRIPTION: data.todo['body'],
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

        assert actual_output == expected_output

    def test_custom_mr_priority(self, data):
        overrides = {'default_mr_priority': '', 'import_labels_as_tags': True}
        service = get_mock_service(GitlabService, {**SERVICE_CONFIG, **overrides})
        issue = service.get_issue_for_record(data.mr, data.mr_extra)
        expected_output = {
            'project': data.mr_extra['project'],
            'priority': overrides['default_mr_priority'],
            'annotations': [],
            'tags': ['feature'],
            'due': data.duedate.replace(microsecond=0),
            'entry': data.created.replace(microsecond=0),
            issue.URL: data.mr_extra['issue_url'],
            issue.REPO: 'project',
            issue.STATE: data.mr['state'],
            issue.TYPE: data.mr_extra['type'],
            issue.TITLE: data.mr['title'],
            issue.NUMBER: str(data.mr['iid']),
            issue.UPDATED_AT: data.updated.replace(microsecond=0),
            issue.CREATED_AT: data.created.replace(microsecond=0),
            issue.DUEDATE: data.duedate,
            issue.DESCRIPTION: data.mr['description'],
            issue.MILESTONE: data.issue['milestone']['title'],
            issue.UPVOTES: 0,
            issue.DOWNVOTES: 0,
            issue.WORK_IN_PROGRESS: 1,
            issue.AUTHOR: 'john_smith',
            issue.ASSIGNEE: 'jack_smith',
            issue.NAMESPACE: 'arbitrary_namespace',
            issue.WEIGHT: 3,
        }
        actual_output = issue.to_taskwarrior()

        assert actual_output == expected_output

    def test_work_in_progress(self, service, data):
        data.issue['work_in_progress'] = False
        issue = service.get_issue_for_record(data.issue, data.extra)

        expected_output = {
            'project': data.extra['project'],
            'priority': service.config.default_priority,
            'annotations': [],
            'tags': [],
            'due': data.duedate.replace(microsecond=0),
            'entry': data.created.replace(microsecond=0),
            issue.URL: data.extra['issue_url'],
            issue.REPO: 'project',
            issue.STATE: data.issue['state'],
            issue.TYPE: data.extra['type'],
            issue.TITLE: data.issue['title'],
            issue.NUMBER: str(data.issue['iid']),
            issue.UPDATED_AT: data.updated.replace(microsecond=0),
            issue.CREATED_AT: data.created.replace(microsecond=0),
            issue.DUEDATE: data.duedate,
            issue.DESCRIPTION: data.issue['description'],
            issue.MILESTONE: data.issue['milestone']['title'],
            issue.UPVOTES: 0,
            issue.DOWNVOTES: 0,
            issue.WORK_IN_PROGRESS: 0,
            issue.AUTHOR: 'john_smith',
            issue.ASSIGNEE: 'jack_smith',
            issue.NAMESPACE: 'arbitrary_namespace',
            issue.WEIGHT: 3,
        }
        actual_output = issue.to_taskwarrior()

        assert actual_output == expected_output

    @responses.activate
    def test_issues_from_query(self, data):
        overrides = {'issue_query': 'issues?state=opened'}
        service = get_mock_service(GitlabService, {**SERVICE_CONFIG, **overrides})
        responses.get(
            'https://my-git.org/api/v4/issues?state=opened&per_page=100&page=1',
            json=[data.issue],
        )
        responses.get(
            'https://my-git.org/api/v4/projects/8',
            json={
                'id': 8,
                'path': 'arbitrary_username/project',
                'web_url': 'example.com',
                "namespace": {"full_path": "arbitrary_username"},
                'path_with_namespace': 'arbitrary_username/project',
            },
        )
        responses.get(
            'https://my-git.org/api/v4/projects/8/issues/3/notes?page=1&per_page=100',
            json=[{'author': {'username': 'john_smith'}, 'body': 'Some comment.'}],
        )
        issue = next(service.issues())
        expected = {
            'annotations': ['@john_smith - Some comment.'],
            'description': '(bw)Is#3 - Add user settings .. example.com/issues/3',
            'due': data.duedate,
            'entry': data.created,
            'gitlabassignee': 'jack_smith',
            'gitlabauthor': 'john_smith',
            'gitlabcreatedon': data.created,
            'gitlabdescription': '',
            'gitlabdownvotes': 0,
            'gitlabmilestone': 'v1.0',
            'gitlabnamespace': 'arbitrary_username',
            'gitlabnumber': '3',
            'gitlabrepo': 'arbitrary_username/project',
            'gitlabstate': 'opened',
            'gitlabtitle': 'Add user settings',
            'gitlabtype': 'issue',
            'gitlabupdatedat': data.updated,
            'gitlabduedate': data.duedate,
            'gitlabupvotes': 0,
            'gitlaburl': 'example.com/issues/3',
            'gitlabwip': 1,
            'gitlabweight': 3,
            'priority': 'M',
            'project': 'arbitrary_username/project',
            'tags': [],
        }
        assert TaskConstructor(issue).get_taskwarrior_record() == expected

    @responses.activate
    def test_mrs_from_query(self, data):
        overrides = {
            'include_issues': 'false',
            'include_todos': 'false',
            'include_merge_requests': 'true',
            'merge_request_query': 'merge_requests?state=opened',
        }
        service = get_mock_service(GitlabService, {**SERVICE_CONFIG, **overrides})
        responses.get(
            'https://my-git.org/api/v4/merge_requests?state=opened&per_page=100&page=1',
            json=[data.mr],
        )
        responses.get(
            'https://my-git.org/api/v4/projects/8',
            json={
                'id': 8,
                'path': 'arbitrary_username/project',
                'web_url': 'example.com',
                "namespace": {"full_path": "arbitrary_username"},
                'path_with_namespace': 'arbitrary_username/project',
            },
        )
        responses.get(
            'https://my-git.org/api/v4/projects/8/'
            + 'merge_requests/3/notes?page=1&per_page=100',
            json=[{'author': {'username': 'john_smith'}, 'body': 'Some comment.'}],
        )
        mr = next(service.issues())
        expected = {
            'annotations': ['@john_smith - Some comment.'],
            'description': '(bw)MR#3 - Add user settings .. example.com/merge_requests/3',
            'due': data.duedate,
            'entry': data.created,
            'gitlabassignee': 'jack_smith',
            'gitlabauthor': 'john_smith',
            'gitlabcreatedon': data.created,
            'gitlabdescription': '',
            'gitlabdownvotes': 0,
            'gitlabmilestone': 'v1.0',
            'gitlabnamespace': 'arbitrary_username',
            'gitlabnumber': '3',
            'gitlabrepo': 'arbitrary_username/project',
            'gitlabstate': 'opened',
            'gitlabtitle': 'Add user settings',
            'gitlabtype': 'merge_request',
            'gitlabupdatedat': data.updated,
            'gitlabduedate': data.duedate,
            'gitlabupvotes': 0,
            'gitlaburl': 'example.com/merge_requests/3',
            'gitlabwip': 1,
            'gitlabweight': 3,
            'priority': 'M',
            'project': 'arbitrary_username/project',
            'tags': [],
        }
        assert TaskConstructor(mr).get_taskwarrior_record() == expected

    @responses.activate
    def test_todos_from_query(self, data):
        overrides = {
            'include_issues': 'false',
            'include_merge_requests': 'false',
            'include_todos': 'true',
            'todo_query': 'todos?state=pending',
        }
        service = get_mock_service(GitlabService, {**SERVICE_CONFIG, **overrides})
        responses.get(
            'https://my-git.org/api/v4/todos?state=pending&per_page=100&page=1',
            json=[data.todo],
        )
        responses.get(
            'https://my-git.org/api/v4/projects/2',
            json={
                "id": 2,
                'path': 'arbitrary_namespace/project',
                'web_url': 'example.com',
                "namespace": {"full_path": "arbitrary_namespace"},
                'path_with_namespace': 'arbitrary_namespace/project',
            },
        )
        responses.get(
            'https://my-git.org/api/v4/projects/arbitrary_namespace%2Fproject?simple=true',
            json={
                'id': 2,
                'path': 'arbitrary_namespace/project',
                'web_url': 'example.com',
                "namespace": {"full_path": "arbitrary_namespace"},
                'path_with_namespace': 'arbitrary_namespace/project',
            },
        )
        todo = next(service.issues())
        expected = {
            'annotations': [],
            'description': '(bw)# - Todo from John Smith for project .. '
            'https://my-git.org/arbitrary_username/project/issues/3',
            'due': None,
            'entry': data.created,
            'gitlabassignee': None,
            'gitlabauthor': 'john_smith',
            'gitlabcreatedon': data.created,
            'gitlabdescription': 'Add user settings',
            'gitlabdownvotes': 0,
            'gitlabmilestone': None,
            'gitlabnamespace': 'todo',
            'gitlabnumber': '42',
            'gitlabrepo': 'project',
            'gitlabstate': 'pending',
            'gitlabtitle': 'Todo from John Smith for project',
            'gitlabtype': 'todo',
            'gitlabupdatedat': data.updated,
            'gitlabduedate': None,
            'gitlabupvotes': 0,
            'gitlaburl': 'https://my-git.org/arbitrary_username/project/issues/3',
            'gitlabwip': 0,
            'gitlabweight': None,
            'priority': 'M',
            'project': 'project',
            'tags': [],
        }
        assert TaskConstructor(todo).get_taskwarrior_record() == expected

        overrides = {
            'include_issues': 'false',
            'include_merge_requests': 'false',
            'include_todos': 'true',
            'include_repos': 'arbitrary_namespace/project',
            'include_all_todos': 'false',
        }
        service = get_mock_service(GitlabService, {**SERVICE_CONFIG, **overrides})
        todo = next(service.issues())
        assert TaskConstructor(todo).get_taskwarrior_record() == expected

    @responses.activate
    def test_issues(self, service, data):
        responses.get(
            'https://my-git.org/api/v4/projects?simple=True&archived=False&per_page=100&page=1',
            json=[
                {
                    'id': 8,
                    'path': 'arbitrary_username/project',
                    'web_url': 'example.com',
                    "namespace": {"full_path": "arbitrary_username"},
                    'path_with_namespace': 'arbitrary_username/project',
                }
            ],
        )

        responses.get(
            'https://my-git.org/api/v4/projects/8/issues?state=opened&per_page=100&page=1',
            json=[data.issue],
        )

        responses.get(
            'https://my-git.org/api/v4/projects/8/issues/3/notes?per_page=100&page=1',
            json=[{'author': {'username': 'john_smith'}, 'body': 'Some comment.'}],
        )

        issue = next(service.issues())

        expected = {
            'annotations': ['@john_smith - Some comment.'],
            'description': '(bw)Is#3 - Add user settings .. example.com/issues/3',
            'due': data.duedate,
            'entry': data.created,
            'gitlabassignee': 'jack_smith',
            'gitlabauthor': 'john_smith',
            'gitlabcreatedon': data.created,
            'gitlabdescription': '',
            'gitlabdownvotes': 0,
            'gitlabmilestone': 'v1.0',
            'gitlabnamespace': 'arbitrary_username',
            'gitlabnumber': '3',
            'gitlabrepo': 'arbitrary_username/project',
            'gitlabstate': 'opened',
            'gitlabtitle': 'Add user settings',
            'gitlabtype': 'issue',
            'gitlabupdatedat': data.updated,
            'gitlabduedate': data.duedate,
            'gitlabupvotes': 0,
            'gitlaburl': 'example.com/issues/3',
            'gitlabwip': 1,
            'gitlabweight': 3,
            'priority': 'M',
            'project': 'arbitrary_username/project',
            'tags': [],
        }

        assert TaskConstructor(issue).get_taskwarrior_record() == expected

    @responses.activate
    def test_only_if_assigned_user_lookup(self):
        """Test that only_if_assigned correctly looks up the user and uses first match"""
        # Mock the user lookup API call - WITH username in query string
        responses.get(
            'https://my-git.org/api/v4/users?username=jack_smith',
            json=[
                {
                    'id': 2,
                    'username': 'jack_smith',
                    'name': 'Jack Smith',
                    'state': 'active',
                }
            ],
        )

        overrides = {'only_if_assigned': 'jack_smith'}

        # Should not raise an error
        service = get_mock_service(GitlabService, {**SERVICE_CONFIG, **overrides})

        # Verify service was created successfully
        assert service is not None

    @responses.activate
    def test_only_if_assigned_user_not_found(self):
        """Test that empty user list causes SystemExit"""
        # Mock empty user lookup response
        responses.get(
            'https://my-git.org/api/v4/users?username=nonexistent_user', json=[]
        )

        overrides = {'only_if_assigned': 'nonexistent_user'}

        # Should exit with 1
        with pytest.raises(SystemExit) as cm:
            get_mock_service(GitlabService, {**SERVICE_CONFIG, **overrides})
        assert cm.value.code == 1

    @responses.activate
    def test_only_if_assigned_multiple_users(self):
        """Test that multiple users found causes SystemExit"""
        # Mock multiple users with similar names
        responses.get(
            'https://my-git.org/api/v4/users?username=smith',
            json=[
                {
                    'id': 10,
                    'username': 'smith',
                    'name': 'John Smith',
                    'state': 'active',
                },
                {
                    'id': 20,
                    'username': 'smithy',
                    'name': 'Jane Smith',
                    'state': 'active',
                },
            ],
        )

        overrides = {'only_if_assigned': 'smith'}

        # Should exit with 1
        with pytest.raises(SystemExit) as cm:
            get_mock_service(GitlabService, {**SERVICE_CONFIG, **overrides})
        assert cm.value.code == 1
