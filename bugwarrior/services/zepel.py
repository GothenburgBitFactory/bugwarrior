from __future__ import absolute_import

from bugwarrior.config import die
from bugwarrior.services import IssueService, Issue

from zepel.client import ProjectRepository, ItemRepository, ListRepository, ZepelClient

import logging
log = logging.getLogger(__name__)

class ZepelIssue(Issue):
    URL = 'zepelurl'
    FOREIGN_ID = 'zepelid'
    TITLE = 'zepeltitle'

    UDAS = {
        TITLE: {
            'type': 'string',
            'label': 'Zepel Title',
        },
        URL: {
            'type': 'string',
            'label': 'Zepel URL',
        },
        FOREIGN_ID: {
            'type': 'string',
            'label': 'Zepel Issue ID'
        }
    }

    UNIQUE_KEY = (URL, )

    def to_taskwarrior(self):
        return {
            'project': self.get_foreign_project().key,
            'due': self.get_foreign_item().due_date,
            'tags': self.get_foreign_item().tags,
            'entry': self.get_foreign_item().created_at,
            'priority': self.origin['default_priority'],

            self.FOREIGN_ID: self.get_foreign_item().id,
            self.URL: self.get_issue_url(),
            self.TITLE: self.get_foreign_item().title,
        }

    def get_foreign_item(self):
        item, zlist, project = self.record
        return item

    def get_foreign_project(self):
        item, zlist, project = self.record
        return project

    def get_foreign_list(self):
        item, zlist, project = self.record
        return zlist

    def get_issue_url(self):
        item, zlist, project = self.record

        return "https://{subdomain}.zepel.io/projects/{project_id}/lists/{list_id}/items/{item_id}".format(
            subdomain = self.origin['subdomain'],
            project_id = project.id,
            list_id = zlist.id,
            item_id = item.id
        )

    def get_default_description(self):
        return self.build_default_description(
            title=self.get_foreign_item().title,
            url=self.get_issue_url(),
            number=self.get_foreign_item().key,
            cls=self.get_cls()
        )

    def get_cls(self):
        item = self.get_foreign_item()

        return ({
            'Story': 'story',
            'Task': 'issue',
            'Subtask': 'subtask',
            'Enhancement': 'feature',
            'Bug': 'bug'
        }).get(item.type, 'issue')

class ZepelService(IssueService):
    ISSUE_CLASS = ZepelIssue
    CONFIG_PREFIX = 'zepel'

    def __init__(self, *args, **kw):
        super(ZepelService, self).__init__(*args, **kw)

        self.client = ZepelClient(self.config.get('subdomain'), self.config.get('token'))

    def get_service_metadata(self):
        return {
            'subdomain': self.client.subdomain
        }

    @classmethod
    def validate_config(cls, service_config, target):
        for k in ('subdomain', 'token'):
            if k not in service_config:
                die("[%s] has no 'mplan.%s'" % (target, k))

        IssueService.validate_config(service_config, target)

    def issues(self):
        for project in ProjectRepository(self.client).index():
            for zlist in ListRepository(self.client).index(project=project):
                items = ItemRepository(self.client).index(list=zlist)
                log.debug("Found %i items in list '%s' of project %s" % ( len(items), zlist.title, project.key ) )

                for item in items:
                    yield self.get_issue_for_record((item, zlist, project))
