from collections.abc import Iterator
import logging
import re
import sys
import typing
from typing import Any
import urllib.parse

from pydantic import ValidationInfo, field_validator, model_validator
import requests

from bugwarrior import config
from bugwarrior.services import Client, Issue, Service

log = logging.getLogger(__name__)

# (repo_name, issue_data)
GithubIssueEntry = tuple[str, dict[str, Any]]
# {issue_url: (repo_name, issue_data)}
GithubIssueMap = dict[str, GithubIssueEntry]


class GithubConfig(config.ServiceConfig):
    password: str = "Deprecated"

    # strictly required
    service: typing.Literal["github"]
    KEYRING_SERVICE = "github://{login}@{host}/{username}"
    login: str
    token: str

    # conditionally required
    username: str = ""
    query: str = ""

    # optional
    include_user_repos: bool = True
    include_repos: config.ConfigList = []
    exclude_repos: config.ConfigList = []
    import_labels_as_tags: bool = False
    label_template: str = "{{label}}"
    filter_pull_requests: bool = False
    exclude_pull_requests: bool = False
    include_user_issues: bool = True
    involved_issues: bool = False
    host: config.NoSchemeUrl = "github.com"
    body_length: int = sys.maxsize
    project_owner_prefix: bool = False
    issue_urls: config.ConfigList = []
    ignore_user_comments: config.ConfigList = []

    @model_validator(mode="after")
    def deprecate_password(self) -> "GithubConfig":
        if self.password != "Deprecated":
            log.warning(
                "Basic auth is no longer supported. Please remove "
                '"password" in favor of "token".'
            )
        return self

    @model_validator(mode="after")
    def require_username_or_query(self) -> "GithubConfig":
        if not self.username and not self.query:
            raise ValueError("section requires one of:\n    username\n    query")
        return self

    @field_validator("issue_urls", mode="after")
    @classmethod
    def issue_urls_consistent_with_host(
        cls, value: list[str], info: ValidationInfo
    ) -> list[str]:
        issue_url_paths = []

        # host can be None if it raised a ValidationError (e.g. if it has a scheme)
        host = info.data.get("host")

        if host is None:
            return value
        for url in value:
            parsed_url = urllib.parse.urlparse(url)
            if parsed_url.netloc != host:
                raise ValueError(f"issue_urls: {url} inconsistent with host {host}")
            if not re.match(r"^/.*/.*/(issues|pull)/[0-9]*$", parsed_url.path):
                raise ValueError(
                    f"issue_urls: {parsed_url.path} is not a valid issue path"
                )
            issue_url_paths.append(parsed_url.path)
        return issue_url_paths

    @model_validator(mode="after")
    def require_username_if_include_user_repos(self) -> "GithubConfig":
        if self.include_user_repos and not self.username:
            raise ValueError(
                "username required when include_user_repos is True (default)"
            )
        return self


class GithubClient(Client):
    def __init__(self, host: str, auth: dict[str, Any]) -> None:
        self.host = host
        self.auth = auth
        self.session = requests.Session()
        if "token" in self.auth:
            authorization = "token " + self.auth["token"]
            self.session.headers["Authorization"] = authorization

        self.kwargs = {}
        if "basic" in self.auth:
            self.kwargs["auth"] = self.auth["basic"]

    def _api_url(self, path: str, **context: Any) -> str:
        """Build the full url to the API endpoint"""
        if self.host == "github.com":
            baseurl = "https://api.github.com"
        else:
            baseurl = f"https://{self.host}/api/v3"
        return baseurl + path.format(**context)

    def get_repos(self, username: str) -> list[Any]:
        user_repos = self._getter(self._api_url("/user/repos?per_page=100"))
        public_repos = self._getter(
            self._api_url("/users/{username}/repos?per_page=100", username=username)
        )
        return user_repos + public_repos

    def get_query(self, query: str) -> list[Any]:
        """Run a generic issue/PR query"""
        url = self._api_url("/search/issues?q={query}&per_page=100", query=query)
        return self._getter(url, subkey="items")

    def get_issues(self, username: str, repo: str) -> list[Any]:
        url = self._api_url(
            "/repos/{username}/{repo}/issues?per_page=100", username=username, repo=repo
        )
        return self._getter(url)

    def get_directly_assigned_issues(self) -> list[Any]:
        """Returns all issues assigned to authenticated user.

        List issues assigned to the authenticated user across all visible
        repositories including owned repositories, member repositories, and
        organization repositories.
        """
        url = self._api_url("/issues?per_page=100")
        return self._getter(url)

    def get_issue_for_url_path(self, url_path: str) -> dict[str, Any]:
        # The pull request url is '/pull/' but the api path is '/pulls/'.
        api_path = re.sub(r"pull(?=/[0-9]*$)", "pulls", url_path)
        url = self._api_url(f"/repos{api_path}")
        return self.json_response(self._request(url))

    def get_comments(self, username: str, repo: str, number: int) -> list[Any]:
        url = self._api_url(
            "/repos/{username}/{repo}/issues/{number}/comments?per_page=100",
            username=username,
            repo=repo,
            number=number,
        )
        return self._getter(url)

    def get_pulls(self, username: str, repo: str) -> list[Any]:
        url = self._api_url(
            "/repos/{username}/{repo}/pulls?per_page=100", username=username, repo=repo
        )
        return self._getter(url)

    def _getter(self, url: str, subkey: str | None = None) -> list[Any]:
        """Pagination utility.  Obnoxious."""
        results = []
        link = {"next": url}

        while "next" in link:
            response = self._request(link["next"])
            json_res = self.json_response(response)

            if subkey is not None:
                json_res = json_res[subkey]

            results += json_res

            link = self._link_field_to_dict(response.headers.get("link", None))

        return results

    def _request(self, url: str) -> requests.Response:
        response = self.session.get(url, **self.kwargs)

        # Warn about the mis-leading 404 error code.  See:
        # https://github.com/ralphbean/bugwarrior/issues/374
        if response.status_code == 404 and "token" in self.auth:
            log.warning(
                "A '404' from github may indicate an auth "
                "failure. Make sure both that your token is correct "
                "and that it has 'public_repo' and not 'public "
                "access' rights."
            )

        return response

    @staticmethod
    def _link_field_to_dict(field: str | None) -> dict[str, str]:
        """Utility for ripping apart github's Link header field.
        It's kind of ugly.
        """

        if not field:
            return {}

        return {
            part.split("; ")[1][5:-1]: part.split("; ")[0][1:-1]
            for part in field.split(", ")
        }


class GithubIssue(Issue):
    TITLE = "githubtitle"
    BODY = "githubbody"
    CREATED_AT = "githubcreatedon"
    UPDATED_AT = "githubupdatedat"
    CLOSED_AT = "githubclosedon"
    MILESTONE = "githubmilestone"
    URL = "githuburl"
    REPO = "githubrepo"
    TYPE = "githubtype"
    NUMBER = "githubnumber"
    USER = "githubuser"
    NAMESPACE = "githubnamespace"
    STATE = "githubstate"
    DRAFT = "githubdraft"

    UDAS = {
        TITLE: {"type": "string", "label": "Github Title"},
        BODY: {"type": "string", "label": "Github Body"},
        CREATED_AT: {"type": "date", "label": "Github Created"},
        UPDATED_AT: {"type": "date", "label": "Github Updated"},
        CLOSED_AT: {"type": "date", "label": "GitHub Closed"},
        MILESTONE: {"type": "string", "label": "Github Milestone"},
        REPO: {"type": "string", "label": "Github Repo Slug"},
        URL: {"type": "string", "label": "Github URL"},
        TYPE: {"type": "string", "label": "Github Type"},
        NUMBER: {"type": "numeric", "label": "Github Issue/PR #"},
        USER: {"type": "string", "label": "Github User"},
        NAMESPACE: {"type": "string", "label": "Github Namespace"},
        STATE: {"type": "string", "label": "GitHub State"},
        DRAFT: {"type": "numeric", "label": "GitHub Draft"},
    }
    UNIQUE_KEY = (URL, TYPE)

    def to_taskwarrior(self) -> dict[str, Any]:
        milestone = self.record["milestone"]
        if milestone:
            milestone = milestone["title"]

        created = self.parse_date(self.record.get("created_at"))
        updated = self.parse_date(self.record.get("updated_at"))
        closed = self.parse_date(self.record.get("closed_at"))

        return {
            "project": self.extra["project"],
            "priority": self.config.default_priority,
            "annotations": self.extra.get("annotations", []),
            "tags": self.get_tags(),
            "entry": created,
            "end": closed,
            self.URL: self.record["html_url"],
            self.REPO: self.record["repo"],
            self.TYPE: self.extra["type"],
            self.USER: self.record["user"]["login"],
            self.TITLE: self.record["title"],
            self.BODY: self.extra["body"],
            self.MILESTONE: milestone,
            self.NUMBER: self.record["number"],
            self.CREATED_AT: created,
            self.UPDATED_AT: updated,
            self.CLOSED_AT: closed,
            self.NAMESPACE: self.extra["namespace"],
            self.STATE: self.record.get("state", ""),
            self.DRAFT: int(self.record.get("draft", 0)),
        }

    def get_tags(self) -> list[str]:
        labels = [label["name"] for label in self.record.get("labels", [])]
        return self.get_tags_from_labels(labels)

    def get_default_description(self) -> str:
        return self.build_default_description(
            title=self.record["title"],
            url=self.record["html_url"],
            number=self.record["number"],
            cls=self.extra["type"],
        )


class GithubService(Service[GithubIssue]):
    API_VERSION = 2.0
    ISSUE_CLASS = GithubIssue
    CONFIG_SCHEMA = GithubConfig

    def __init__(
        self, config: GithubConfig, main_config: config.MainSectionConfig
    ) -> None:
        super().__init__(config, main_config)

        auth = {"token": self.get_secret("token", self.config.login)}
        self.client = GithubClient(self.config.host, auth)

    def get_owned_repo_issues(self, tag: str) -> GithubIssueMap:
        """Grab all the issues"""
        issues = {}
        for issue in self.client.get_issues(*tag.split("/")):
            issues[issue["url"]] = (tag, issue)
        return issues

    def get_query(self, query: str) -> GithubIssueMap:
        """Grab all issues matching a github query"""
        issues = {}
        for issue in self.client.get_query(query):
            url = issue["html_url"]
            try:
                repo = self.get_repository_from_issue(issue)
            except ValueError as e:
                log.critical(e)
            else:
                issues[url] = (repo, issue)
        return issues

    def get_directly_assigned_issues(self) -> GithubIssueMap:
        issues = {}
        for issue in self.client.get_directly_assigned_issues():
            repo = self.get_repository_from_issue(issue)
            issues[issue["url"]] = (repo, issue)
        return issues

    def get_issues_by_url(self) -> GithubIssueMap:
        issues = {}
        for url_path in self.config.issue_urls:
            issue = self.client.get_issue_for_url_path(url_path)
            match = re.search(r"(?<=^/)(.*/.*)(?=/(issues|pull)/[0-9]*$)", url_path)
            assert match is not None
            repo = match[0]
            issues[url_path] = (repo, issue)
        return issues

    @classmethod
    def get_repository_from_issue(cls, issue: dict[str, Any]) -> str:
        if "repo" in issue:
            return issue["repo"]
        if "repos_url" in issue:
            url = issue["repos_url"]
        elif "repository_url" in issue:
            url = issue["repository_url"]
        else:
            raise ValueError("Issue has no repository url" + str(issue))
        tag = re.match(".*/([^/]*/[^/]*)$", url)
        if tag is None:
            raise ValueError(f"Unrecognized URL: {url}.")
        return tag.group(1)

    def _comments(self, tag: str, number: int) -> list[Any]:
        user, repo = tag.split("/")
        return self.client.get_comments(user, repo, number)

    def annotations(self, tag: str, issue: dict[str, Any]) -> list[str]:
        url = issue["html_url"]
        annotations = []
        if self.main_config.annotation_comments:
            comments = self._comments(tag, issue["number"])
            log.debug(" got comments for %s", issue["html_url"])
            annotations = []
            for c in comments:
                login = c["user"]["login"]
                if login in self.config.ignore_user_comments:
                    log.debug(" ignoring comment from %s", login)
                    continue
                annotations.append((login, c["body"]))
        return self.build_annotations(annotations, url)

    def body(self, issue: dict[str, Any]) -> str | None:
        body = issue["body"]

        if body:
            body = body.replace("\r\n", "\n")
            max_length = self.config.body_length
            body = body[:max_length]

        return body

    def _reqs(self, tag: str) -> list[tuple[str, Any]]:
        """Grab all the pull requests"""
        return [(tag, i) for i in self.client.get_pulls(*tag.split("/"))]

    def get_owner(self, issue: GithubIssueEntry) -> str | None:
        if issue[1]["assignee"]:
            return issue[1]["assignee"]["login"]

    def filter_issues(self, issue: Any) -> bool:
        repo, _ = issue
        return self.filter_repo_name(repo.split("/")[-3])

    def filter_repos(self, repo: dict[str, Any]) -> bool:
        if repo["owner"]["login"] != self.config.username:
            return False

        return self.filter_repo_name(repo["name"])

    def filter_repo_name(self, name: str) -> bool:
        if name in self.config.exclude_repos:
            return False

        if self.config.include_repos:
            return name in self.config.include_repos

        return True

    def include(self, issue: GithubIssueEntry) -> bool:
        """Return true if the issue in question should be included"""
        if "pull_request" in issue[1]:
            if self.config.exclude_pull_requests:
                return False
            if not self.config.filter_pull_requests:
                return True

        if self.config.only_if_assigned:
            owner = self.get_owner(issue)
            include_owners: list[str | None] = [self.config.only_if_assigned]

            if self.config.also_unassigned:
                include_owners.append(None)

            return owner in include_owners

        return True

    def issues(self) -> Iterator[GithubIssue]:
        issues = {}
        if self.config.query:
            issues.update(self.get_query(self.config.query))
        elif self.config.involved_issues:
            issues.update(self.get_query(f"involves:{self.config.username} state:open"))

        if self.config.include_user_repos:
            # Only query for all repos if an explicit
            # include_repos list is not specified.
            if self.config.include_repos:
                repos = self.config.include_repos
            else:
                all_repos = self.client.get_repos(self.config.username)
                repos = filter(self.filter_repos, all_repos)
                repos = [repo["name"] for repo in repos]

            for repo in repos:
                issues.update(
                    self.get_owned_repo_issues(self.config.username + "/" + repo)
                )
        if self.config.include_user_issues:
            issues.update(
                filter(self.filter_issues, self.get_directly_assigned_issues().items())
            )
        if self.config.issue_urls:
            issues.update(filter(self.filter_issues, self.get_issues_by_url().items()))

        log.debug(" Found %i issues.", len(issues))
        issues = list(filter(self.include, issues.values()))
        log.debug(" Pruned down to %i issues.", len(issues))

        for tag, issue in issues:
            # Stuff this value into the upstream dict for:
            # https://github.com/ralphbean/bugwarrior/issues/159
            issue["repo"] = tag

            issue_obj = self.get_issue_for_record(issue)
            tagParts = tag.split("/")
            projectName = tagParts[1]
            if self.config.project_owner_prefix:
                projectName = tagParts[0] + "." + projectName
            extra = {
                "project": projectName,
                "type": "pull_request" if "pull_request" in issue else "issue",
                "annotations": self.annotations(tag, issue),
                "body": self.body(issue),
                "namespace": self.config.username,
            }
            issue_obj.extra.update(extra)
            yield issue_obj
