from urllib.parse import quote, urlencode
import requests
import typing

import pydantic
import sys
import typing_extensions

from bugwarrior import config
from bugwarrior.services import IssueService, Issue, ServiceClient

import logging
log = logging.getLogger(__name__)

DefaultPriority = typing_extensions.Literal['', 'L', 'M', 'H', 'unassigned']


class GitlabConfig(config.ServiceConfig):
    _DEPRECATE_FILTER_MERGE_REQUESTS = True
    filter_merge_requests: typing.Union[bool, typing_extensions.Literal['Undefined']] = 'Undefined'

    service: typing_extensions.Literal['gitlab']
    login: str
    token: str
    host: config.NoSchemeUrl

    include_repos: config.ConfigList = config.ConfigList([])
    exclude_repos: config.ConfigList = config.ConfigList([])
    include_regex: typing.Optional[typing.Pattern] = None
    exclude_regex: typing.Optional[typing.Pattern] = None
    membership: bool = False
    owned: typing.Optional[bool] = None
    import_labels_as_tags: bool = False
    label_template: str = '{{label}}'
    include_merge_requests: typing.Union[bool, typing_extensions.Literal['Undefined']] = 'Undefined'
    include_issues: bool = True
    include_todos: bool = False
    include_all_todos: bool = True
    only_if_author: str = ''
    default_issue_priority: DefaultPriority = 'unassigned'
    default_todo_priority: DefaultPriority = 'unassigned'
    default_mr_priority: DefaultPriority = 'unassigned'
    use_https: bool = True
    verify_ssl: typing.Union[bool, config.ExpandedPath] = True
    body_length: int = sys.maxsize
    project_owner_prefix: bool = False
    issue_query: str = ''
    merge_request_query: str = ''
    todo_query: str = ''

    @pydantic.root_validator
    def namespace_repo_lists(cls, values):
        """ Add a default namespace to a repository name.  If the name already
        contains a namespace, it will be returned unchanged:
            e.g. "foo/bar" → "foo/bar"
        otherwise, the login will be prepended as namespace:
            e.g. "bar" → "<login>/bar"
        """
        for repolist in ['include_repos', 'exclude_repos']:
            values[repolist] = [
                f"{values['login']}/{repo}"
                if not repo.startswith('id:') and repo.find('/') < 0
                else repo
                for repo in values[repolist]]
        return values

    @pydantic.root_validator
    def default_priorities(cls, values):
        for task_type in ['issue', 'todo', 'mr']:
            priority_field = f'default_{task_type}_priority'
            values[priority_field] = (
                values[priority_field]
                if values[priority_field] != 'unassigned'
                else values['default_priority'])
        return values

    @pydantic.root_validator
    def filter_gitlab_dot_com(cls, values):
        """
        There must be a repository filter if the host is gitlab.com.

        Otherwise we'll get a 405 error for exceeding gitlab's rate limit by
        trying to paginate through all public repositories.
        """
        if (values['host'] == 'gitlab.com'
                # Options which automatically apply a filter.
                and not (values['owned'] or
                         values['membership'] or
                         values['include_repos'])
                # Query options *may* apply a filter.
                and (
                    (values['include_issues'] and not values['issue_query'])
                    or (values['include_merge_requests'] and not values['merge_request_query'])
                    or (values['include_todos'] and not values['todo_query'])
                )):
            raise ValueError(
                "You must set at least one of the configuration options "
                "to filter repositories (e.g., 'owned') because there "
                "there are too many on gitlab.com to fetch them all.")
        return values

    @pydantic.validator('owned', always=True)
    def require_owned(cls, v):
        """
        Migrate 'owned' field from default False to default True.

        Migration plan:
            - [X] Warning if 'owned' is undefined.
            - [ ] Next major version: validation error if 'owned' is undefined.
            - [ ] Subsequent major version: 'owned' defaults to True.
        """
        if v is None:
            log.warning(
                "WARNING: Gitlab's 'owned' configuration field should be set "
                "explicitly. In a future release, this will be an error.")
            v = False
        return v


class GitlabClient(ServiceClient):
    """Abstraction of Gitlab API v4"""

    def __init__(self, host, token, only_if_assigned, also_unassigned, use_https, verify_ssl):
        if use_https:
            self.scheme = 'https'
        else:
            self.scheme = 'http'
        self.verify_ssl = verify_ssl

        self.host = host
        self.token = token

        self.repo_cache = {}

        # If we're only fetching assigned issues we can reduce requests by
        # filtering in the query.
        assignee_id = (
            self._fetch(f'users?username={only_if_assigned}')[-1]['id']
            if only_if_assigned and not also_unassigned else None)
        self.assignee_query = (
            f'assignee_id={assignee_id}' if assignee_id else '')

    def _base_url(self):
        return f"{self.scheme}://{self.host}/api/v4/"

    def _fetch(self, relative_url: str, skip_403: bool = False, **kwargs) -> dict:
        """Perform a fetch operation on the gitlab server

        :param relative_url: This part will be appended to the base api URL for the call
        :type relative_url: str
        :param skip_403: Do not raise an exception if a 403 is returned because
        it may simply indicate a disabled feature.
        :type skip_403: bool
        :param kwargs: will be sent alongside the request.get call
        :rtype: dict
        """
        headers = {'PRIVATE-TOKEN': self.token}
        url = self._base_url() + relative_url

        if not self.verify_ssl:
            requests.packages.urllib3.disable_warnings()
        response = requests.get(
            url, headers=headers, verify=self.verify_ssl, **kwargs)

        if skip_403 and response.status_code == 403:
            log.debug(f'Skipping {relative_url}. (Is feature disabled?)')
            return {}
        return self.json_response(response)

    def _fetch_paged(
            self,
            relative_url: str,
            page_size: int = 100,
            skip_403: bool = False
            ) -> list:
        """Make a gitlab REST API call with pagination. Calls will be buffered on pages with size
        ``page_size``.

        :param relative_url:
        :type relative_url: str
        :param page_size: Size of fetch pages. Defaults to 100
        :type page_size: int
        :rtype: list
        """
        params = {
            'page': 1,
            'per_page': page_size,
        }

        full = []
        detect_broken_gitlab_pagination = []
        while True:
            items = self._fetch(relative_url, skip_403=skip_403, params=params)
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

    def get_repos(self, include_repos: list, only_membership: bool, only_owned: bool) -> list:
        """Returns a list of repo objects for all repositories accessible. Respects
        config.include_repos.

        :param include_repos: If set, only those particular repositories will be queried. If a
        non-empty list is passed, the parameters
        ``only_membership`` and ``only_owned`` don't have any effect.
        :type include_repos: list
        :param only_membership: If set to True, only repos where the user is member to are fetched.
        :type only_membership: bool
        :param only_owned: If set to True, only repos the user owns are fetched
        :type only_owned: bool
        :rtype: list
        """

        all_repos = []
        if include_repos:
            for repo in include_repos:
                if repo.startswith("id:"):
                    repo = repo[3:]
                indiv_tmpl = 'projects' + '/' + quote(repo, '') + '?simple=true'
                item = self._fetch(indiv_tmpl)
                if not item:
                    break

                all_repos.append(item)

        else:
            querystring = {'simple': True, 'archived': False}
            if only_membership:
                querystring['membership'] = True
            if only_owned:
                querystring['owned'] = True
            all_repos = self._fetch_paged('projects' + '?' + urlencode(querystring))
        for item in all_repos:
            self.repo_cache[item['id']] = item
        return all_repos

    def _get_repo(self, repo_id: int) -> dict:
        """Queries information about a single repository as JSON dictionary

        :param repo_id: Project ID in the Gitlab instance
        :type repo_id: int
        :rtype: dict
        """
        return self._fetch('projects/' + str(repo_id))

    def get_repo_cached(self, repo_id: int) -> dict:
        """Get repo information with a repo cache. Repo information will only be fetched the first
        time information about a certain repository is fetched.

        :param repo_id: numeric id of the project on the Gitlab server
        :type repo_id: int
        :rtype: dict
        """
        if repo_id not in self.repo_cache:
            self.repo_cache[repo_id] = self._get_repo(repo_id)

        return self.repo_cache[repo_id]

    def get_notes(self, rid: int, issue_type: str, issueid: int) -> list:
        """Get notes attached to a certain issue / merge_request as list of JSON dictionaries

        :param rid: Project ID in the Gitlab instance
        :type rid: int
        :param issue_type: "issues" / "merge_requests / snippets / epics"
        :type issue_type: str
        :param issueid: ID of issue
        :type issueid: int
        :rtype: list
        """
        return self._fetch_paged(f'projects/{rid}/{issue_type}/{issueid}/notes')

    def get_repo_issues(self, rid: int) -> dict:
        """Get all issues from a repository as JSON dictionary

        :param rid: Project ID in the Gitlab instance
        :type rid: int
        :rtype: list
        """
        return self.get_issues_from_query(
            f'projects/{rid}/issues?state=opened&{self.assignee_query}')

    def get_repo_merge_requests(self, rid: int) -> dict:
        """Get all merge_requests from a repository as JSON dictionary

        :param rid: Project ID in the Gitlab instance
        :type rid: int
        :rtype: dict
        """
        return self.get_issues_from_query(
            f'projects/{rid}/merge_requests?state=opened&{self.assignee_query}',
            skip_403=True)

    def get_issues_from_query(
            self, query: str, skip_403: bool = False) -> dict:
        """Get objects matching a query. Results will be returned in a dictionary where the key
        matches their project ID.

        :param query: API query string that should get sent to the server
        :type query: str
        :rtype: dict
        """
        issues = {}
        result = self._fetch_paged(query, skip_403=skip_403)
        for issue in result:
            issues[issue['id']] = (issue['project_id'], issue)
        return issues

    def get_todos(self, query: str) -> list:
        """Get all todo objects matching a query returned as list of (project_id, todo) tuples

        :param query: API query string that should get sent to the server
        :type query: str
        :rtype: list
        """
        todos = []
        fetched_todos = self._fetch_paged(query)
        for todo in fetched_todos:
            todos.append((todo.get('project'), todo))
        return todos


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

    # Override the method from parent class
    def get_priority(self):
        default_priority_map = {
            'todo': self.config.default_todo_priority,
            'merge_request': self.config.default_mr_priority,
            'issue': self.config.default_issue_priority}

        type_str = self.extra['type']
        default_priority = self.config.default_priority

        return default_priority_map.get(type_str, default_priority)

    def to_taskwarrior(self):
        author = self.record['author']
        milestone = self.record.get('milestone')
        created = self.record['created_at']
        updated = self.record.get('updated_at')
        state = self.record['state']
        upvotes = self.record.get('upvotes', 0)
        downvotes = self.record.get('downvotes', 0)
        work_in_progress = int(self.record.get('work_in_progress', 0))
        # FIXME: 'assignee' api column is deprecated in favor of 'assignees'
        assignee = self.record.get('assignee')
        duedate = self.record.get('due_date')
        weight = self.record.get('weight')
        number = (
            self.record['id'] if self.extra['type'] == 'todo'
            else self.record['iid'])
        priority = self.get_priority()
        title = (
            'Todo from %s for %s' % (author['name'], self.extra['project'])
            if self.extra['type'] == 'todo' else self.record['title'])
        description = (
            self.record['body'] if self.extra['type'] == 'todo'
            else self.extra['description'])

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
        return self.get_tags_from_labels(self.record.get('labels', []))

    def get_default_description(self):
        return self.build_default_description(
            title=self.title,
            url=self.extra['issue_url'],
            number=self.record.get('iid', ''),
            cls=self.extra['type'],
        )


class GitlabService(IssueService):
    ISSUE_CLASS = GitlabIssue
    CONFIG_SCHEMA = GitlabConfig

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        token = self.get_password('token', self.config.login)
        self.gitlab_client = GitlabClient(
            host=self.config.host,
            token=token,
            only_if_assigned=self.config.only_if_assigned,
            also_unassigned=self.config.also_unassigned,
            use_https=self.config.use_https,
            verify_ssl=self.config.verify_ssl
        )
        self.repo_map = dict()

    @staticmethod
    def get_keyring_service(config):
        return f"gitlab://{config.login}@{config.host}"

    def get_owner(self, issue):
        return [assignee['username'] for assignee in issue[1]['assignees']]

    def get_author(self, issue):
        if issue[1]['author'] is not None and issue[1]['author']['username']:
            return issue[1]['author']['username']

    def filter_repos(self, repo):
        if (repo['path_with_namespace'] in self.config.exclude_repos
                or "id:%d" % repo['id'] in self.config.exclude_repos):
            return False

        if self.config.exclude_regex:
            if self.config.exclude_regex.match(repo['path_with_namespace']):
                return False

        # fallback if no filter is set
        is_included = True

        if self.config.include_repos:
            if (repo['path_with_namespace'] in self.config.include_repos
                    or "id:%d" % repo['id'] in self.config.include_repos):
                return True
            else:
                is_included = False

        if self.config.include_regex:
            if self.config.include_regex.match(repo['path_with_namespace']):
                return True
            else:
                is_included = False

        return is_included

    def annotations(self, repo, url, issue_type, issue):
        annotations = []

        if self.main_config.annotation_comments:
            notes = self.gitlab_client.get_notes(repo['id'], issue_type, issue['iid'])
            annotations = ((
                n['author']['username'],
                n['body']
            ) for n in notes)

        return self.build_annotations(annotations, url)

    def include_todo(self, repos):
        ids = list(r['id'] for r in repos)

        def include_todo(todo):
            project, todo = todo
            return project is None or project['id'] in ids
        return include_todo

    def _get_issue_objs(self, issues, issue_type):
        type_plural = issue_type + 's'

        for rid, issue in issues:
            repo = self.gitlab_client.get_repo_cached(rid)
            issue['repo'] = repo['path']
            projectName = repo['path']
            if self.config.project_owner_prefix:
                projectName = repo['namespace']['path'] + "." + projectName
            issue_obj = self.get_issue_for_record(issue)
            issue_url = '%s/%s/%d' % (repo['web_url'], type_plural, issue['iid'])
            extra = {
                'issue_url': issue_url,
                'project': repo['path'],
                'namespace': repo['namespace']['full_path'],
                'type': issue_type,
                'annotations': self.annotations(repo, issue_url, type_plural, issue),
                'description': self.description(issue),
            }
            issue_obj.update_extra(extra)
            yield issue_obj

    def _get_todo_objs(self, todos):
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
            project_name = repo['path']
            if self.config.project_owner_prefix:
                project_name = repo['namespace']['path'] + "." + project_name
            extra = {
                'issue_url': todo_url,
                'project': project_name,
                'namespace': "todo",
                'type': 'todo',
                'annotations': [],
            }
            todo_obj.update_extra(extra)
            yield todo_obj

    def include(self, issue):
        """ Return true if the issue in question should be included """
        if not self.filter_repos(self.gitlab_client.get_repo_cached(issue[0])):
            return False

        if self.config.only_if_assigned:
            assignees = self.get_owner(issue)

            if self.config.also_unassigned and not assignees:
                return True

            return self.config.only_if_assigned in assignees

        if self.config.only_if_author:
            return self.get_author(issue) == self.config.only_if_author

        return True

    def get_issues_from_projects(self, repos):
        issues = {}
        for repo in repos:
            rid = repo['id']
            self.repo_map[rid] = repo
            issues.update(
                self.gitlab_client.get_repo_issues(rid)
            )
        return issues

    def get_all_repos(self):
        include_repos = list()
        if not self.config.include_regex:
            include_repos = self.config.include_repos
        all_repos = self.gitlab_client.get_repos(
            include_repos=include_repos,
            only_membership=self.config.membership,
            only_owned=self.config.owned
        )
        repos = list(filter(self.filter_repos, all_repos))
        return repos

    def description(self, issue):
        description = issue['description']

        if description:
            max_length = self.config.body_length
            description = description[:max_length]

        return description

    def issues(self):

        # List of repos will only be queried if needed
        repos = []

        # Issues
        if self.config.include_issues:
            if self.config.issue_query:
                issues = self.gitlab_client.get_issues_from_query(self.config.issue_query)
            else:
                if not repos:
                    repos = self.get_all_repos()
                issues = self.get_issues_from_projects(repos)

            log.debug("Found %i issues.", len(issues))
            issues_filtered = list(filter(self.include, issues.values()))
            log.debug("Pruned down to %i issues.", len(issues_filtered))
            yield from self._get_issue_objs(issues_filtered, 'issue')

        # Merge requests
        if self.config.include_merge_requests:
            if self.config.merge_request_query:
                merge_requests = self.gitlab_client.get_issues_from_query(
                    self.config.merge_request_query, skip_403=True)
            else:
                if not repos:
                    repos = self.get_all_repos()
                merge_requests = {}
                for repo in repos:
                    rid = repo['id']
                    merge_requests.update(
                        self.gitlab_client.get_repo_merge_requests(rid)
                    )
            log.debug("Found %i merge requests.", len(merge_requests))
            merge_requests_filtered = list(filter(self.include, merge_requests.values()))
            log.debug("Pruned down to %i merge requests.", len(merge_requests_filtered))

            yield from self._get_issue_objs(merge_requests_filtered, 'merge_request')

        # ToDos
        if self.config.include_todos:
            query = 'todos?state=pending'
            if self.config.todo_query:
                query = self.config.todo_query

            todos = self.gitlab_client.get_todos(query)
            log.debug(" Found %i todo items.", len(todos))
            if not self.config.include_all_todos:
                if not repos:
                    repos = self.get_all_repos()
                todos_filtered = list(filter(self.include_todo(repos), todos))
            else:
                todos_filtered = todos
            log.debug(" Pruned down to %i todos.", len(todos_filtered))
            yield from self._get_todo_objs(todos_filtered)
