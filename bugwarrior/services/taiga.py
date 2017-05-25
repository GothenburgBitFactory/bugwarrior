from __future__ import absolute_import

import requests
import six

from bugwarrior.db import CACHE_REGION as cache
from bugwarrior.config import die
from bugwarrior.services import IssueService, Issue, ServiceClient


class TaigaIssue(Issue):
    SUMMARY = 'taigasummary'
    URL = 'taigaurl'
    FOREIGN_ID = 'taigaid'

    UDAS = {
        SUMMARY: {
            'type': 'string',
            'label': 'Taiga Summary'
        },
        URL: {
            'type': 'string',
            'label': 'Taiga URL',
        },
        FOREIGN_ID: {
            'type': 'numeric',
            'label': 'Taiga Issue ID'
        },
    }
    UNIQUE_KEY = (URL, )

    def to_taskwarrior(self):
        return {
            'project': self.extra['project'],
            'annotations': self.extra['annotations'],
            self.URL: self.extra['url'],

            'priority': self.origin['default_priority'],
            'tags': self.record['tags'],
            self.FOREIGN_ID: self.record['ref'],
            self.SUMMARY: self.record['subject'],
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['subject'],
            url=self.get_processed_url(self.extra['url']),
            number=self.record['ref'],
            cls='issue',
        )


class TaigaService(IssueService, ServiceClient):
    ISSUE_CLASS = TaigaIssue
    CONFIG_PREFIX = 'taiga'

    def __init__(self, *args, **kw):
        super(TaigaService, self).__init__(*args, **kw)
        self.url = self.config.get('base_uri')
        self.auth_token = self.get_password('auth_token')
        self.label_template = self.config.get(
            'label_template', default='{{label}}', to_type=six.text_type
        )
        self.session = requests.session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Authorization': 'Bearer %s' % self.auth_token,
        })

    @staticmethod
    def get_keyring_service(service_config):
        base_uri = service_config.get('base_uri')
        return "taiga://%s" % base_uri

    def get_service_metadata(self):
        return {
            'url': self.url,
            'label_template': self.label_template,
        }

    @classmethod
    def validate_config(cls, service_config, target):
        for option in ('auth_token', 'base_uri'):
            if option not in service_config:
                die("[%s] has no 'taiga.%s'" % (target, option))

        IssueService.validate_config(service_config, target)

    def issues(self):
        url = self.url + '/api/v1/users/me'
        me = self.session.get(url)
        data = me.json()

        # Check for errors and bail if we failed.
        if '_error_message' in data:
            raise RuntimeError("{_error_type} {_error_message}".format(**data))

        # Otherwise, proceed.
        userid = data['id']

        url = self.url + '/api/v1/userstories'
        params = dict(assigned_to=userid, status__is_closed="false")
        response = self.session.get(url, params=params)
        stories = response.json()

        for story in stories:
            project = self.get_project(story['project'])
            extra = {
                'project': project['slug'],
                'annotations': self.annotations(story, project),
                'url': self.build_url(story, project),
            }
            yield self.get_issue_for_record(story, extra)

    @cache.cache_on_arguments()
    def get_project(self, project_id):
        url = '%s/api/v1/projects/%i' % (self.url, project_id)
        return self.json_response(self.session.get(url))

    def build_url(self, story, project):
        return '%s/project/%s/us/%i' % (self.url, project['slug'], story['ref'])

    def annotations(self, story, project):
        url = '%s/api/v1/history/userstory/%i' % (self.url, story['id'])
        response = self.session.get(url)
        history = response.json()
        return self.build_annotations(
            ((
                item['user']['username'],
                item['comment'],
            ) for item in history if item['comment']),
            self.build_url(story, project)
        )
