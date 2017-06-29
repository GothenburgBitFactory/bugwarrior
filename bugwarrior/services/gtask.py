import httplib2
import googleapiclient.discovery
from bugwarrior.services import Issue
from bugwarrior.config import aslist
from .google import GoogleService

import logging
log = logging.getLogger(__name__)

class GtaskIssue(Issue):
    TASK_ID = 'gtaskid'
    URL = 'gtaskurl'
    TITLE = 'gtasktitle'
    TASKLIST = 'gtasklist'
    TASKLINKTITLE = 'gtasklinktitle'
    TASKLINKURL = 'gtasklinkurl'
    UNIQUE_KEY = (TASK_ID,)
    UDAS = {
        TASK_ID: {
            'type': 'string',
            'label': 'GTask Id',
        },
        URL: {
            'type': 'string',
            'label': 'GTask URL',
        },
        TITLE: {
            'type': 'string',
            'label': 'GTask Title',
        },
        TASKLIST: {
            'type': 'string',
            'label': 'GTask List Name',
        },
        TASKLINKTITLE: {
            'type': 'string',
            'label': 'GTask Link Title',
        },
        TASKLINKURL: {
            'type': 'string',
            'label': 'GTask Link Url',
        },
    }

    def to_taskwarrior(self):
        tw = {
            'priority': self.origin['default_priority'],
            self.TASK_ID: self.record['id'],
            self.URL: self.record['selfLink'],
            self.TITLE: self.record['title'],
            self.TASKLIST: self.extra['tasklist'],
        }
        if 'links' in self.record:
            tw[self.TASKLINKURL] = self.record['links'][0]['link']
            tw[self.TASKLINKTITLE] = self.record['links'][0]['description']
        return tw

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['title'],
            number=self.record['id'][-8:],
            cls='issue',
        )


class GtaskService(GoogleService):
    APPLICATION_NAME = 'Bugwarrior GTasks Service'
    SCOPES = 'https://www.googleapis.com/auth/tasks.readonly'
    ISSUE_CLASS = GtaskIssue
    RESOURCE = 'tasks'
    CONFIG_PREFIX = 'gtask'

    def __init__(self, *args, **kw):
        super(GtaskService, self).__init__(*args, **kw)
        self.lists = self.config.get('lists', 'default', aslist)

    def get_tasklists(self):
        lists = self.api.tasklists().list().execute()
        return dict((item['title'], item['id']) for item in lists['items'])

    def get_tasks(self, list_id):
        return self.api.tasks().list(
                tasklist=list_id,
                showCompleted=False,
                showDeleted=False).execute()['items']

    def issues(self):
        tasklists = self.get_tasklists()
        for list_name in self.lists:
            try:
                list_id = tasklists[list_name]
            except KeyError:
                log.error("Invalid tasklist: %r. Available tasklists: %r",
                        self.lists, tasklists.keys())
                raise

            for task in self.get_tasks(list_id):
                yield self.get_issue_for_record(task, {'tasklist': list_name})
