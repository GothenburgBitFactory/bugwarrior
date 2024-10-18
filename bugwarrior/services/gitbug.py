import logging
import os
import signal
import subprocess
import sys

import requests
import typing_extensions

from bugwarrior import config
from bugwarrior.services import Service, Issue, Client

log = logging.getLogger(__name__)


class GitBugConfig(config.ServiceConfig):
    service: typing_extensions.Literal['gitbug']

    path: config.ExpandedPath

    import_labels_as_tags: bool = False
    label_template: str = '{{label}}'
    port: int = 43915


class Webui:
    def __init__(self, path, port):
        self.path = path
        self.port = port

    def __enter__(self):
        self.windows = True
        try:  # Windows
            kwargs = {'creationflags': (subprocess.CREATE_NEW_PROCESS_GROUP,)}
        except AttributeError:  # Posix
            self.windows = False
            kwargs = {'start_new_session': True}

        self.webui = subprocess.Popen(
            ['git', 'bug', 'webui', '--no-open', f'--port={self.port}'],
            stderr=subprocess.PIPE,
            cwd=self.path,
            text=True,
            **kwargs,
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

    def __exit__(self, *exc):
        if self.webui.returncode is None:
            if self.windows:
                os.kill(self.webui.pid, signal.SIGTERM)
            else:
                os.killpg(os.getpgid(self.webui.pid), signal.SIGTERM)

        return False


class GitBugClient(Client):
    def __init__(self, path, port, annotation_comments):
        self.path = path
        self.port = port
        self.annotation_comments = annotation_comments

    def _query_graphql(self, query):
        with Webui(self.path, self.port):
            response = requests.post(
                f'http://127.0.0.1:{self.port}/graphql',
                json={'query': query})
        return self.json_response(response)['data']

    def get_issues(self):
        return self._query_graphql(
            '{ repository { allBugs { nodes { %s } } } }' % ' '.join([
                'author { name }',
                (
                    'comments' +
                    ('(first: 1) ' if not self.annotation_comments else '')
                    + ' { nodes { author { name } message } }'
                ),
                'createdAt',
                'id',
                'labels { name }'
                'status',
                'title',
            ]))['repository']['allBugs']['nodes']


class GitBugIssue(Issue):
    AUTHOR = 'gitbugauthor'
    ID = 'gitbugid'
    STATE = 'gitbugstate'
    TITLE = 'gitbugtitle'

    UDAS = {
        AUTHOR: {
            'type': 'string',
            'label': 'Gitbug Issue Author',
        },
        ID: {
            'type': 'string',
            'label': 'Gitbug UUID',
        },
        STATE: {
            'type': 'string',
            'label': 'Gitbug state',
        },
        TITLE: {
            'type': 'string',
            'label': 'Gitbug Title',
        },
    }

    UNIQUE_KEY = (ID,)

    def to_taskwarrior(self):
        return {
            'project': self.config.target,
            'priority': self.config.default_priority,
            'annotations': self.record.get('annotations', []),
            'tags': self.get_tags(),
            'entry': self.parse_date(self.record.get('createdAt')),

            self.AUTHOR: self.record['author']['name'],
            self.ID: self.record['id'],
            self.STATE: self.record['status'],
            self.TITLE: self.record['title'],
        }

    def get_tags(self):
        return self.get_tags_from_labels(
            [label['name'] for label in self.record['labels']])

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['title'], cls='bug')


class GitBugService(Service):
    ISSUE_CLASS = GitBugIssue
    CONFIG_SCHEMA = GitBugConfig

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.client = GitBugClient(
            path=self.config.path,
            port=self.config.port,
            annotation_comments=self.main_config.annotation_comments)

    def issues(self):
        for issue in self.client.get_issues():
            comments = issue.pop('comments')
            issue['description'] = comments['nodes'].pop(0)['message']

            if self.main_config.annotation_comments:
                annotations = ((
                    comment['author']['name'],
                    comment['message']
                ) for comment in comments['nodes'])
                issue['annotations'] = self.build_annotations(annotations)

            yield self.get_issue_for_record(issue)
