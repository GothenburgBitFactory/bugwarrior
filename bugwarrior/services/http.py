import requests
import logging
from dateutil.parser import isoparse

from bugwarrior.services import IssueService, Issue

log = logging.getLogger(__name__)


class HttpIssue(Issue):
    UUID = 'http_uuid'
    URL = 'http_url'

    UNIQUE_KEY = (UUID,)
    UDAS = {
        URL: {
            'type': 'string',
            'label': "API URL"
        },
        UUID: {
            'type': 'string',
            'label': 'Virtual API UUID for task'
        }
    }

    def get_default_description(self):
        return self.record.get(
            'description',
            self.record.get(
                'uuid',
                self.extra.get('url')
            )
        )

    def to_taskwarrior(self):
        return {
            'entry': isoparse(self.record.get('entry')) if self.record.get('entry') else None,
            'tags': self.record.get('tags', []),
            'project': self.get_project(),
            'description': self.record.get('description'),
            'priority': self.get_priority(),

            self.UUID: self.record.get('uuid'),
            self.URL: self.extra.get('url')
        }


class HttpService(IssueService):
    APPLICATION_NAME = 'Bugwarrior HTTP Service'

    ISSUE_CLASS = HttpIssue
    CONFIG_PREFIX = 'http'

    def __init__(self, *args, **kw):
        super(HttpService, self).__init__(*args, **kw)

        self.url = self.config.get('url')
        self.method = self.config.get('method', 'GET')
        self.authorization_header = self.config.get('authorization_header')

    def issues(self):
        return ( self.convert_to_issue(task) for task in self.request() )

    def request(self):
        return requests.request(
            self.method, self.url,
            headers={ 'Authorization': self.authorization_header }
        ).json()

    def convert_to_issue(self, task):
        issue = self.get_issue_for_record(task)

        issue.update_extra({ 'url': self.url })

        return issue
