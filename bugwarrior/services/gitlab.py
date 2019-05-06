# coding: utf-8
from future import standard_library
standard_library.install_aliases()
from builtins import map
from builtins import filter

try:
    from urllib import quote, urlencode  # Python 2.X
except ImportError:
    from urllib.parse import quote, urlencode # Python 3+
from six.moves.configparser import NoOptionError
import re
import requests
import six

from jinja2 import Template

from bugwarrior.config import asbool, aslist, die
from bugwarrior.services import IssueService, Issue, ServiceClient

import logging
log = logging.getLogger(__name__)


class GitlabIssue(Issue):
    TITLE = 'gitlabtitle'
    DESCRIPTION = 'gitlabdescription'
    CREATED_AT = 'gitlabcreatedon'
    UPDATED_AT = 'gitlabupdatedat'
    DUEDATE = 'gitlabduedate'
    MILESTONE = 'gitlabmilestone'
    URL = 'gitlaburl'
    REPO = 'gitlabrepo'
    TYPE = 'gitlabtype'
    NUMBER = 'gitlabnumber'
    STATE = 'gitlabstate'
    UPVOTES = 'gitlabupvotes'
    DOWNVOTES = 'gitlabdownvotes'
    WORK_IN_PROGRESS = 'gitlabwip'
    AUTHOR = 'gitlabauthor'
    ASSIGNEE = 'gitlabassignee'
    NAMESPACE = 'gitlabnamespace'
    WEIGHT = 'gitlabweight'

    UDAS = {
        TITLE: {
            'type': 'string',
            'label': 'Gitlab Title',
        },
        DESCRIPTION: {
            'type': 'string',
            'label': 'Gitlab Description',
        },
        CREATED_AT: {
            'type': 'date',
            'label': 'Gitlab Created',
        },
        UPDATED_AT: {
            'type': 'date',
            'label': 'Gitlab Updated',
        },
        DUEDATE: {
            'type': 'date',
            'label': 'Gitlab Due Date',
        },
        MILESTONE: {
            'type': 'string',
            'label': 'Gitlab Milestone',
        },
        URL: {
            'type': 'string',
            'label': 'Gitlab URL',
        },
        REPO: {
            'type': 'string',
            'label': 'Gitlab Repo Slug',
        },
        TYPE: {
            'type': 'string',
            'label': 'Gitlab Type',
        },
        NUMBER: {
            'type': 'string',
            'label': 'Gitlab Issue/MR #',
        },
        STATE: {
            'type': 'string',
            'label': 'Gitlab Issue/MR State',
        },
        UPVOTES: {
            'type': 'numeric',
            'label': 'Gitlab Upvotes',
        },
        DOWNVOTES: {
            'type': 'numeric',
            'label': 'Gitlab Downvotes',
        },
        WORK_IN_PROGRESS: {
            'type': 'numeric',
            'label': 'Gitlab MR Work-In-Progress Flag',
        },
        AUTHOR: {
            'type': 'string',
            'label': 'Gitlab Author',
        },
        ASSIGNEE: {
            'type': 'string',
            'label': 'Gitlab Assignee',
        },
        NAMESPACE: {
            'type': 'string',
            'label': 'Gitlab Namespace',
        },
        WEIGHT: {
            'type': 'numeric',
            'label': 'Gitlab Weight',
        },
    }
    UNIQUE_KEY = (REPO, TYPE, NUMBER,)

    def _normalize_label_to_tag(self, label):
        return re.sub(r'[^a-zA-Z0-9]', '_', label)

    def to_taskwarrior(self):
        author = self.record['author']
        milestone = self.record.get('milestone')
        created = self.record['created_at']
        updated = self.record.get('updated_at')
        state = self.record['state']
        upvotes = self.record.get('upvotes', 0)
        downvotes = self.record.get('downvotes', 0)
        work_in_progress = int(asbool(self.record.get('work_in_progress', 0)))
        assignee = self.record.get('assignee')
        duedate = self.record.get('due_date')
        weight = self.record.get('weight')
        number = (
            self.record['id'] if self.extra['type'] == 'todo'
            else self.record['iid'])
        priority = (
            self.origin['default_priority'] if self.extra['type'] == 'issue'
            else 'H')
        title = (
            'Todo from %s for %s' % (author['name'], self.extra['project'])
            if self.extra['type'] == 'todo' else self.record['title'])
        description = (
            self.record['body'] if self.extra['type'] == 'todo'
            else self.record['description'])

        if milestone and (
                self.extra['type'] == 'issue' or
                (self.extra['type'] == 'merge_request' and duedate is None)):
            duedate = milestone['due_date']
        if milestone:
            milestone = milestone['title']
        if created:
            created = self.parse_date(created).replace(microsecond=0)
        if updated:
            updated = self.parse_date(updated).replace(microsecond=0)
        if duedate:
            duedate = self.parse_date(duedate)
        if author:
            author = author['username']
        if assignee:
            assignee = assignee['username']


        self.title = title

        return {
            'project': self.extra['project'],
            'priority': priority,
            'annotations': self.extra.get('annotations', []),
            'tags': self.get_tags(),
            'due': duedate,
            'entry': created,

            self.URL: self.extra['issue_url'],
            self.REPO: self.extra['project'],
            self.TYPE: self.extra['type'],
            self.TITLE: title,
            self.DESCRIPTION: description,
            self.MILESTONE: milestone,
            self.NUMBER: str(number),
            self.CREATED_AT: created,
            self.UPDATED_AT: updated,
            self.DUEDATE: duedate,
            self.STATE: state,
            self.UPVOTES: upvotes,
            self.DOWNVOTES: downvotes,
            self.WORK_IN_PROGRESS: work_in_progress,
            self.AUTHOR: author,
            self.ASSIGNEE: assignee,
            self.NAMESPACE: self.extra['namespace'],
            self.WEIGHT: weight,
        }

    def get_tags(self):
        tags = []

        if not self.origin['import_labels_as_tags']:
            return tags

        context = self.record.copy()
        label_template = Template(self.origin['label_template'])

        for label in self.record.get('labels', []):
            context.update({
                'label': self._normalize_label_to_tag(label)
            })
            tags.append(
                label_template.render(context)
            )

        return tags

    def get_default_description(self):
        return self.build_default_description(
            title=self.title,
            url=self.get_processed_url(self.extra['issue_url']),
            number=self.record.get('iid', ''),
            cls=self.extra['type'],
        )


class GitlabService(IssueService, ServiceClient):
    ISSUE_CLASS = GitlabIssue
    CONFIG_PREFIX = 'gitlab'

    def __init__(self, *args, **kw):
        super(GitlabService, self).__init__(*args, **kw)

        host = self.config.get(
            'host', default='gitlab.com', to_type=six.text_type)
        self.login = self.config.get('login')
        token = self.get_password('token', self.login)
        self.auth = (host, token)

        if self.config.get('use_https', default=True, to_type=asbool):
            self.scheme = 'https'
        else:
            self.scheme = 'http'

        self.verify_ssl = self.config.get(
            'verify_ssl', default=True, to_type=asbool
        )

        self.membership = self.config.get('membership', False)

        self.owned = self.config.get('owned', False)

        self.exclude_repos = self.config.get('exclude_repos', [], aslist)
        self.include_repos = self.config.get('include_repos', [], aslist)
        self.exclude_regex = self.config.get('exclude_regex', None)
        self.include_regex = self.config.get('include_regex', None)

        self.include_repos = list(map(self.add_default_namespace, self.include_repos))
        self.exclude_repos = list(map(self.add_default_namespace, self.exclude_repos))
        self.include_regex = re.compile(self.include_regex) if self.include_regex else None
        self.exclude_regex = re.compile(self.exclude_regex) if self.exclude_regex else None

        self.import_labels_as_tags = self.config.get(
            'import_labels_as_tags', default=False, to_type=asbool
        )
        self.label_template = self.config.get(
            'label_template', default='{{label}}', to_type=six.text_type
        )
        self.filter_merge_requests = self.config.get(
            'filter_merge_requests', default=False, to_type=asbool
        )
        self.include_todos = self.config.get(
            'include_todos', default=False, to_type=asbool
        )
        self.include_all_todos = self.config.get(
            'include_all_todos', default=True, to_type=asbool
        )
        self.project_owner_prefix = self.config.get(
            'project_owner_prefix', default=False, to_type=asbool
        )

    def add_default_namespace(self, repo):
        """ Add a default namespace to a repository name.  If the name already
        contains a namespace, it will be returned unchanged:
            e.g. "foo/bar" → "foo/bar"
        otherwise, the loggin will be prepended as namespace:
            e.g. "bar" → "<login>/bar"
        """
        if repo.find('/') < 0:
            return self.login + '/' + repo
        else:
            return repo

    @staticmethod
    def get_keyring_service(service_config):
        login = service_config.get('login')
        host = service_config.get('host', default='gitlab.com')
        return "gitlab://%s@%s" % (login, host)

    def get_service_metadata(self):
        return {
            'import_labels_as_tags': self.import_labels_as_tags,
            'label_template': self.label_template,
        }


    def get_owner(self, issue):
        if issue[1]['assignee'] != None and issue[1]['assignee']['username']:
            return issue[1]['assignee']['username']

    def get_author(self, issue):
        if issue[1]['author'] != None and issue[1]['author']['username']:
            return issue[1]['author']['username']

    def filter_repos(self, repo):
        if self.exclude_repos:
            if repo['path_with_namespace'] in self.exclude_repos:
                return False

        if self.exclude_regex:
            if self.exclude_regex.match(repo['path_with_namespace']):
                return False

        # fallback if no filter is set
        is_included = True

        if self.include_repos:
            if repo['path_with_namespace'] in self.include_repos:
                return True
            else:
                is_included = False

        if self.include_regex:
            if self.include_regex.match(repo['path_with_namespace']):
                return True
            else:
                is_included = False

        return is_included

    def _get_notes(self, rid, issue_type, issueid):
        tmpl = '{scheme}://{host}/api/v4/projects/%d/%s/%d/notes' % (rid, issue_type, issueid)
        return self._fetch_paged(tmpl)

    def annotations(self, repo, url, issue_type, issue, issue_obj):
        annotations = []

        if self.annotation_comments:
            notes = self._get_notes(repo['id'], issue_type, issue['iid'])
            annotations = ((
                n['author']['username'],
                n['body']
            ) for n in notes)

        return self.build_annotations(
            annotations,
            issue_obj.get_processed_url(url)
        )

    def _fetch(self, tmpl, **kwargs):
        url = tmpl.format(scheme=self.scheme, host=self.auth[0])
        headers = {'PRIVATE-TOKEN': self.auth[1]}

        if not self.verify_ssl:
            requests.packages.urllib3.disable_warnings()
        response = requests.get(url, headers=headers, verify=self.verify_ssl, **kwargs)

        return self.json_response(response)

    def _fetch_paged(self, tmpl):
        params = {
            'page': 1,
            'per_page': 100,
        }

        full = []
        detect_broken_gitlab_pagination = []
        while True:
            items = self._fetch(tmpl, params=params)
            if not items:
                break

            # XXX: Some gitlab versions have a bug where pagination doesn't
            # work and instead return the entire result no matter what. Detect
            # this by seeing if the results are the same as the last time
            # around and bail if so. Unfortunately, while it is a GitLab bug,
            # we have to deal with instances where it exists.
            if items == detect_broken_gitlab_pagination:
                break
            detect_broken_gitlab_pagination = items

            full += items

            if len(items) < params['per_page']:
                break
            params['page'] += 1

        return full

    def get_repo_issues(self, rid):
        tmpl = '{scheme}://{host}/api/v4/projects/%d/issues?state=opened' % rid
        issues = {}
        try:
            repo_issues = self._fetch_paged(tmpl)
        except IOError:
            # Projects may have issues disabled.
            return {}
        for issue in repo_issues:
            issues[issue['id']] = (rid, issue)
        return issues

    def get_repo_merge_requests(self, rid):
        tmpl = '{scheme}://{host}/api/v4/projects/%d/merge_requests?state=opened' % rid
        issues = {}
        try:
            repo_merge_requests = self._fetch_paged(tmpl)
        except IOError:
            # Projects may have merge requests disabled.
            return {}
        for issue in repo_merge_requests:
            issues[issue['id']] = (rid, issue)
        return issues

    def get_todos(self):
        tmpl = '{scheme}://{host}/api/v4/todos?state=pending'
        todos = []
        try:
            fetched_todos = self._fetch_paged(tmpl)
        except IOError:
            # Older gitlab versions do not have todo items.
            return {}
        for todo in fetched_todos:
            todos.append((todo.get('project'), todo))
        return todos

    def include_todo(self, repos):
        ids = list(r['id'] for r in repos)

        def include_todo(todo):
            project, todo = todo
            return project is None or project['id'] in ids
        return include_todo

    def _get_issue_objs(self, issues, issue_type, repo_map):
        type_plural = issue_type + 's'

        for rid, issue in issues:
            repo = repo_map[rid]
            issue['repo'] = repo['path']
            projectName = repo['path']
            if self.project_owner_prefix:
                projectName = repo['namespace']['path'] + "." + projectName
            issue_obj = self.get_issue_for_record(issue)
            issue_url = '%s/%s/%d' % (repo['web_url'], type_plural, issue['iid'])
            extra = {
                'issue_url': issue_url,
                'project': repo['path'],
                'namespace': repo['namespace']['full_path'],
                'type': issue_type,
                'annotations': self.annotations(repo, issue_url, type_plural, issue, issue_obj)
            }
            issue_obj.update_extra(extra)
            yield issue_obj

    def issues(self):
        tmpl = '{scheme}://{host}/api/v4/projects'

        all_repos = []
        if self.include_repos and not self.include_regex:
            for repo in self.include_repos:
                indiv_tmpl = tmpl + '/' + quote(repo, '') + '?simple=true'
                item = self._fetch(indiv_tmpl)
                if not item:
                    break

                all_repos.append(item)

        else:
            querystring = { 'simple': True }
            if self.membership:
                querystring['membership'] = True
            if self.owned:
                querystring['owned'] = True
            all_repos = self._fetch_paged(tmpl + '?' + urlencode(querystring))

        repos = list(filter(self.filter_repos, all_repos))

        repo_map = {}
        issues = {}
        for repo in repos:
            rid = repo['id']
            repo_map[rid] = repo
            issues.update(
                self.get_repo_issues(rid)
            )
        log.debug(" Found %i issues.", len(issues))
        issues = list(filter(self.include, issues.values()))
        log.debug(" Pruned down to %i issues.", len(issues))

        for issue in self._get_issue_objs(issues, 'issue', repo_map):
            yield issue

        if not self.filter_merge_requests:
            merge_requests = {}
            for repo in repos:
                rid = repo['id']
                merge_requests.update(
                    self.get_repo_merge_requests(rid)
                )
            log.debug(" Found %i merge requests.", len(merge_requests))
            merge_requests = list(filter(self.include, merge_requests.values()))
            log.debug(" Pruned down to %i merge requests.", len(merge_requests))

            for issue in self._get_issue_objs(merge_requests,
                                              'merge_request',
                                              repo_map):
                yield issue

        if self.include_todos:
            todos = self.get_todos()
            log.debug(" Found %i todo items.", len(todos))
            if not self.include_all_todos:
                todos = list(filter(self.include_todo(repos), todos))
            log.debug(" Pruned down to %i todos.", len(todos))

            for project, todo in todos:
                if project is not None:
                    repo = project
                else:
                    repo = {
                        'path': 'the instance',
                    }
                todo['repo'] = repo['path']

                todo_obj = self.get_issue_for_record(todo)
                todo_url = todo['target_url']
                projectName = repo['path']
                if self.project_owner_prefix:
                    projectName = repo['namespace']['path'] + "." + projectName
                extra = {
                    'issue_url': todo_url,
                    'project': projectName,
                    'namespace': "todo",
                    'type': 'todo',
                    'annotations': [],
                }
                todo_obj.update_extra(extra)
                yield todo_obj

    @classmethod
    def validate_config(cls, service_config, target):
        if 'host' not in service_config:
            die("[%s] has no 'gitlab.host'" % target)

        if 'login' not in service_config:
            die("[%s] has no 'gitlab.login'" % target)

        if 'token' not in service_config:
            die("[%s] has no 'gitlab.token'" % target)

        super(GitlabService, cls).validate_config(service_config, target)
