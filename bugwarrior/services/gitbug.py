from collections.abc import Iterator
import logging
import os
import signal
import subprocess
import sys
from typing import Any, Literal

from pydantic import Field
import requests

from bugwarrior import config
from bugwarrior.services import Client, Issue, Service
from bugwarrior.task import Task, Udas

log = logging.getLogger(__name__)


class GitBugConfig(config.ServiceConfig):
    service: Literal['gitbug']
    KEYRING_SERVICE = 'gitbug://{path}'

    path: config.ExpandedPath

    import_labels_as_tags: bool = False
    label_template: str = '{{label}}'
    port: int = 43915

    only_if_assigned: config.UnsupportedOption[str] = ''
    also_unassigned: config.UnsupportedOption[bool] = False


class Webui:
    def __init__(self, path: str, port: int) -> None:
        self.path = path
        self.port = port

    def __enter__(self) -> "Webui":
        popen_kwargs: dict[str, Any] = {}
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True
        self.webui = subprocess.Popen(
            ['git', 'bug', 'webui', '--no-open', f'--port={self.port}'],
            stderr=subprocess.PIPE,
            cwd=self.path,
            text=True,
            **popen_kwargs,
        )

        # Give server a chance to spin up and make sure it's still running.
        try:
            _, errs = self.webui.communicate(timeout=0.5)
        except subprocess.TimeoutExpired:
            pass
        else:
            log.critical(errs.strip())
            sys.exit(1)

        return self

    def __exit__(self, *exc: Any) -> Literal[False]:
        if self.webui.returncode is None:
            if sys.platform == "win32":
                os.kill(self.webui.pid, signal.SIGTERM)
            else:
                os.killpg(os.getpgid(self.webui.pid), signal.SIGTERM)

        return False


class GitBugClient(Client):
    def __init__(self, path: str, port: int, annotation_comments: bool) -> None:
        self.path = path
        self.port = port
        self.annotation_comments = annotation_comments

    def _query_graphql(self, query: str) -> dict[str, Any]:
        with Webui(self.path, self.port):
            response = requests.post(
                f'http://127.0.0.1:{self.port}/graphql', json={'query': query}
            )
        return self.json_response(response)['data']

    def get_issues(self) -> list[dict[str, Any]]:
        return self._query_graphql(
            '{ repository { allBugs { nodes { %s } } } }'
            % ' '.join(
                [
                    'author { name }',
                    (
                        'comments'
                        + ('(first: 1) ' if not self.annotation_comments else '')
                        + ' { nodes { author { name } message } }'
                    ),
                    'createdAt',
                    'id',
                    'labels { name }status',
                    'title',
                ]
            )
        )['repository']['allBugs']['nodes']


class GitBugUdas(Udas):
    """Service-specific UDAs contributed by git-bug."""

    UNIQUE_KEY = ('gitbugid',)

    gitbugauthor: str = Field(title='Gitbug Issue Author')
    gitbugid: str = Field(title='Gitbug UUID')
    gitbugstate: str = Field(title='Gitbug state')
    gitbugtitle: str = Field(title='Gitbug Title')


class GitBugTask(Task):
    udas: GitBugUdas


class GitBugIssue(Issue):
    def to_taskwarrior(self) -> GitBugTask:
        return GitBugTask(
            project=self.config.target,
            priority=self.config.default_priority,
            annotations=self.record.get('annotations', []),
            tags=self.get_tags(),
            entry=self.record.get('createdAt'),
            udas=GitBugUdas(
                gitbugauthor=self.record['author']['name'],
                gitbugid=self.record['id'],
                gitbugstate=self.record['status'],
                gitbugtitle=self.record['title'],
            ),
        )

    def get_tags(self) -> list[str]:
        return self.get_tags_from_labels(
            [label['name'] for label in self.record['labels']]
        )

    def get_default_description(self) -> str:
        return self.build_default_description(title=self.record['title'], cls='bug')


class GitBugService(Service):
    API_VERSION = 2.0
    ISSUE_CLASS = GitBugIssue
    TASK_SCHEMA = GitBugTask
    CONFIG_SCHEMA = GitBugConfig

    def __init__(
        self, config: GitBugConfig, main_config: config.MainSectionConfig
    ) -> None:
        super().__init__(config, main_config)

        self.client = GitBugClient(
            path=self.config.path,
            port=self.config.port,
            annotation_comments=self.main_config.annotation_comments,
        )

    def issues(self) -> Iterator[Task]:
        for issue in self.client.get_issues():
            comments = issue.pop('comments')
            issue['description'] = comments['nodes'].pop(0)['message']

            if self.main_config.annotation_comments:
                annotations = (
                    (comment['author']['name'], comment['message'])
                    for comment in comments['nodes']
                )
                issue['annotations'] = self.build_annotations(annotations)

            yield self.process_record(issue)
