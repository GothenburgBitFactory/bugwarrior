from __future__ import absolute_import
import re
import six

import requests

from bugwarrior.config import asbool, die
from bugwarrior.services import IssueService, Issue, ServiceClient
from jinja2 import Template

import logging

log = logging.getLogger(__name__)


class NotionIssue(Issue):
    ISSUE_PREFIX = 'notion'
    ISSUE = ISSUE_PREFIX + 'issue'
    SUMMARY = ISSUE_PREFIX + 'summary'
    URL = ISSUE_PREFIX + 'url'
    PROJECT = ISSUE_PREFIX + 'project'
    NUMBER = ISSUE_PREFIX + 'number'

    UDAS = {
        ISSUE: {
            'type': 'string',
            'label': 'Notion Issue'
        },
        SUMMARY: {
            'type': 'string',
            'label': 'Notion Summary',
        },
        URL: {
            'type': 'string',
            'label': 'Notion URL',
        },
        PROJECT: {
            'type': 'string',
            'label': 'Notion Project'
        },
        NUMBER: {
            'type': 'string',
            'label': 'Notion Project Issue Number'
        },
    }
    UNIQUE_KEY = (URL,)

    def _get_record_field(self, field_name):
        for field in self.record['field']:
            if field['name'] == field_name:
                return field

    def _get_record_field_value(self, field_name, field_value='value'):
        field = self._get_record_field(field_name)
        if field:
            return field[field_value]

    def to_taskwarrior(self):
        return {
            'project': self.get_project(),
            'priority': self.get_priority(),
            'tags': self.get_tags(),

            self.ISSUE: self.get_issue(),
            self.SUMMARY: self.get_issue_summary(),
            self.URL: self.get_issue_url(),
            self.PROJECT: self.get_project(),
            self.NUMBER: self.get_number_in_project(),
        }

    def get_issue(self):
        return self.record['id']

    def get_issue_summary(self):
        return self._get_record_field_value('summary')

    def get_issue_url(self):
        return "%s/issue/%s" % (
            self.origin['base_url'], self.get_issue()
        )

    def get_project(self):
        return self._get_record_field_value('projectShortName')

    def get_number_in_project(self):
        return int(self._get_record_field_value('numberInProject'))

    def get_default_description(self):
        return self.build_default_description(
            title=self.get_issue_summary(),
            url=self.get_processed_url(self.get_issue_url()),
            number=self.get_issue(),
            cls='issue',
        )

    def get_tags(self):
        tags = []
        return tags


class NotionService(IssueService, ServiceClient):
    ISSUE_CLASS = NotionIssue
    CONFIG_PREFIX = ISSUE_CLASS.ISSUE_PREFIX

    def __init__(self, *args, **kw):
        super(NotionService, self).__init__(*args, **kw)
        self.token_v2 = self.config.get('token_v2')
        self.task_page = self.config.get('task_page')
        self.email = self.config.get('email')
        self.base_url = 'https://notion.so'


    def get_service_metadata(self):
        return {
            'token_v2': self.token_v2,
            'task_page': self.task_page,
            'email': self.email,
            'base_url': self.base_url,
        }

    @classmethod
    def validate_config(cls, service_config, target):
        for k in ('token_v2', 'task_page', 'email'):
            if k not in service_config:
                die("[%s] has no 'notion.%s'" % (target, k))

        IssueService.validate_config(service_config, target)

    def issues(self):
        from notion.client import NotionClient
        client = NotionClient(token_v2=self.token_v2)
        response = client.get_block(self.task_page)
        rows = response.collection.get_rows()
        issues = []
        for row in rows:
            if any(x.email == self.email for x in row.engineers):
                field = [ { "name": "projectShortName", "value": "TEST" },
                        { "name": "numberInProject", "value": "1" },
                        { "name": "summary", "value": "Hello World" }, ]
                issues.append({'id':row.id,
                               'assignee':row.engineers,
                               'status':row.status,
                               'title':row.title,
                               'field':field})
        log.debug(" Found %i total.", len(issues))

        for issue in issues:
            yield self.get_issue_for_record(issue)
