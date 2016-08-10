from ConfigParser import NoOptionError
import re
import requests
import six

from jinja2 import Template

from bugwarrior.config import asbool, die
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
            'type': 'numeric',
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
    }
    UNIQUE_KEY = (REPO, TYPE, NUMBER,)

    def _normalize_label_to_tag(self, label):
        return re.sub(r'[^a-zA-Z0-9]', '_', label)

    def to_taskwarrior(self):
        if self.extra['type'] == 'todo':
            #title = see below.
            description = self.record['body']
            priority = 'H'
            milestone = None
            created = self.record['created_at']
            updated = None
            state = self.record['state']
            upvotes = 0
            downvotes = 0
            work_in_progress = 0
            author = self.record['author']
            assignee = None
            duedate = None
            number = self.record['id']
        elif self.extra['type'] == 'merge_request':
            title = self.record['title']
            description = self.record['description']
            priority = 'H'
            milestone = self.record['milestone']
            created = self.record['created_at']
            updated = self.record['updated_at']
            state = self.record['state']
            upvotes = self.record['upvotes']
            downvotes = self.record['downvotes']
            work_in_progress = self.record.get('work_in_progress', 0)
            author = self.record['author']
            assignee = self.record['assignee']
            duedate = self.record.get('due_date')
            if duedate is None and milestone:
                duedate = milestone['due_date']
            number = self.record['iid']
        else: # 'issue'
            title = self.record['title']
            description = self.record['description']
            priority = self.origin['default_priority']
            milestone = self.record['milestone']
            created = self.record['created_at']
            updated = self.record['updated_at']
            state = self.record['state']
            upvotes = self.record.get('upvotes', 0)
            downvotes = self.record.get('downvotes', 0)
            work_in_progress = 0
            author = self.record['author']
            assignee = self.record['assignee']
            duedate = None
            if milestone:
                duedate = milestone['due_date']
            number = self.record['iid']

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

        # Generate the title for todo items.
        if self.extra['type'] == 'todo':
            title = 'Todo from %s for %s' % (
                    author,
                    self.extra['project'],
                )

        self.title = title

        return {
            'project': self.extra['project'],
            'priority': priority,
            'annotations': self.extra.get('annotations', []),
            'tags': self.get_tags(),

            self.URL: self.extra['issue_url'],
            self.REPO: self.extra['project'],
            self.TYPE: self.extra['type'],
            self.TITLE: title,
            self.DESCRIPTION: description,
            self.MILESTONE: milestone,
            self.NUMBER: number,
            self.CREATED_AT: created,
            self.UPDATED_AT: updated,
            self.DUEDATE: duedate,
            self.STATE: state,
            self.UPVOTES: upvotes,
            self.DOWNVOTES: downvotes,
            self.WORK_IN_PROGRESS: work_in_progress,
            self.AUTHOR: author,
            self.ASSIGNEE: assignee,
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

        host = self.config_get_default(
            'host', default='gitlab.com', to_type=six.text_type)
        login = self.config_get('login')
        token = self.config_get_password('token', login)
        self.auth = (host, token)

        if self.config_get_default('use_https', default=True, to_type=asbool):
            self.scheme = 'https'
        else:
            self.scheme = 'http'

        self.verify_ssl = self.config_get_default(
            'verify_ssl', default=True, to_type=asbool
        )

        self.exclude_repos = []
        if self.config_get_default('exclude_repos', None):
            self.exclude_repos = [
                item.strip() for item in
                self.config_get('exclude_repos').strip().split(',')
            ]

        self.include_repos = []
        if self.config_get_default('include_repos', None):
            self.include_repos = [
                item.strip() for item in
                self.config_get('include_repos').strip().split(',')
            ]

        self.import_labels_as_tags = self.config_get_default(
            'import_labels_as_tags', default=False, to_type=asbool
        )
        self.label_template = self.config_get_default(
            'label_template', default='{{label}}', to_type=six.text_type
        )
        self.filter_merge_requests = self.config_get_default(
            'filter_merge_requests', default=False, to_type=asbool
        )
        self.include_todos = self.config_get_default(
            'include_todos', default=False, to_type=asbool
        )
        self.include_all_todos = self.config_get_default(
            'include_all_todos', default=True, to_type=asbool
        )

    @classmethod
    def get_keyring_service(cls, config, section):
        login = config.get(section, cls._get_key('login'))
        try:
            host = config.get(section, cls._get_key('host'))
        except NoOptionError:
            host = 'gitlab.com'
        return "gitlab://%s@%s" % (login, host)

    def get_service_metadata(self):
        return {
            'import_labels_as_tags': self.import_labels_as_tags,
            'label_template': self.label_template,
        }


    def get_owner(self, issue):
        if issue[1]['assignee'] != None and issue[1]['assignee']['username']:
            return issue[1]['assignee']['username']

    def filter_repos(self, repo):
        if self.exclude_repos:
            if repo['path_with_namespace'] in self.exclude_repos:
                return False

        if self.include_repos:
            if repo['path_with_namespace'] in self.include_repos:
                return True
            else:
                return False

        return True

    def _get_notes(self, rid, issue_type, issueid):
        tmpl = '{scheme}://{host}/api/v3/projects/%d/%s/%d/notes' % (rid, issue_type, issueid)
        return self._fetch_paged(tmpl)

    def annotations(self, repo, url, issue_type, issue, issue_obj):
        notes = self._get_notes(repo['id'], issue_type, issue['id'])
        return self.build_annotations(
            ((
                n['author']['username'],
                n['body']
            ) for n in notes),
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
        tmpl = '{scheme}://{host}/api/v3/projects/%d/issues' % rid
        issues = {}
        try:
            repo_issues = self._fetch_paged(tmpl)
        except IOError:
            # Projects may have issues disabled.
            return {}
        for issue in repo_issues:
            if issue['state'] not in ('opened', 'reopened'):
                continue
            issues[issue['id']] = (rid, issue)
        return issues

    def get_repo_merge_requests(self, rid):
        tmpl = '{scheme}://{host}/api/v3/projects/%d/merge_requests' % rid
        issues = {}
        try:
            repo_merge_requests = self._fetch_paged(tmpl)
        except IOError:
            # Projects may have merge requests disabled.
            return {}
        for issue in repo_merge_requests:
            if issue['state'] not in ('opened', 'reopened'):
                continue
            issues[issue['id']] = (rid, issue)
        return issues

    def get_todos(self):
        tmpl = '{scheme}://{host}/api/v3/todos'
        todos = {}
        try:
            fetched_todos = self._fetch_paged(tmpl)
        except IOError:
            # Older gitlab versions do not have todo items.
            return {}
        for todo in fetched_todos:
            if todo['state'] == 'done':
                continue
            todos[todo['id']] = (todo.get('project'), todo)
        return todos

    def include_todo(self, repos):
        ids = list(r['id'] for r in repos)

        def include_todo(todo):
            project, todo = todo
            return project is None or project['id'] in ids
        return include_todo

    def issues(self):
        tmpl = '{scheme}://{host}/api/v3/projects'
        all_repos = self._fetch_paged(tmpl)
        repos = filter(self.filter_repos, all_repos)

        repo_map = {}
        issues = {}
        for repo in repos:
            rid = repo['id']
            repo_map[rid] = repo
            issues.update(
                self.get_repo_issues(rid)
            )
        log.debug(" Found %i issues.", len(issues))
        issues = filter(self.include, issues.values())
        log.debug(" Pruned down to %i issues.", len(issues))

        for rid, issue in issues:
            repo = repo_map[rid]
            issue['repo'] = repo['path']

            issue_obj = self.get_issue_for_record(issue)
            issue_url = '%s/issues/%d' % (repo['web_url'], issue['iid'])
            extra = {
                'issue_url': issue_url,
                'project': repo['path'],
                'type': 'issue',
                'annotations': self.annotations(repo, issue_url, 'issues', issue, issue_obj)
            }
            issue_obj.update_extra(extra)
            yield issue_obj

        if not self.filter_merge_requests:
            merge_requests = {}
            for repo in repos:
                rid = repo['id']
                merge_requests.update(
                    self.get_repo_merge_requests(rid)
                )
            log.debug(" Found %i merge requests.", len(merge_requests))
            merge_requests = filter(self.include, merge_requests.values())
            log.debug(" Pruned down to %i merge requests.", len(merge_requests))

            for rid, issue in merge_requests:
                repo = repo_map[rid]
                issue['repo'] = repo['path']

                issue_obj = self.get_issue_for_record(issue)
                issue_url = '%s/merge_requests/%d' % (repo['web_url'], issue['iid'])
                extra = {
                    'issue_url': issue_url,
                    'project': repo['path'],
                    'type': 'merge_request',
                    'annotations': self.annotations(repo, issue_url, 'merge_requests', issue, issue_obj)
                }
                issue_obj.update_extra(extra)
                yield issue_obj

        if self.include_todos:
            todos = self.get_todos()
            log.debug(" Found %i todo items.", len(todos))
            if not self.include_all_todos:
                todos = filter(self.include_todo(repos), todos.values())
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
                extra = {
                    'issue_url': todo_url,
                    'project': repo['path'],
                    'type': 'todo',
                    'annotations': [],
                }
                todo_obj.update_extra(extra)
                yield todo_obj

    @classmethod
    def validate_config(cls, config, target):
        if not config.has_option(target, 'gitlab.host'):
            die("[%s] has no 'gitlab.host'" % target)

        if not config.has_option(target, 'gitlab.login'):
            die("[%s] has no 'gitlab.login'" % target)

        if not config.has_option(target, 'gitlab.token'):
            die("[%s] has no 'gitlab.token'" % target)

        super(GitlabService, cls).validate_config(config, target)
