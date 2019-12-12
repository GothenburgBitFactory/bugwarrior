from builtins import filter, map
import six
import re
import operator

import requests
from jinja2 import Template

from bugwarrior.config import asbool, aslist, asint, die
from bugwarrior.services import IssueService, Issue, ServiceClient

import logging
log = logging.getLogger(__name__)


class PivotalTrackerIssue(Issue):
    URL = 'pivotalurl'
    DESCRIPTION = 'pivotaldescription'
    TYPE = 'pivotalstorytype'
    PROJECT_ID = 'pivotalprojectid'
    PROJECT_NAME = 'pivotalprojectname'
    OWNED_BY = 'pivotalowners'
    REQUEST_BY = 'pivotalrequesters'
    FOREIGN_ID = 'pivotalid'
    ESTIMATE = 'pivotalestimate'
    BLOCKERS = 'pivotalblockers'
    CREATED_AT = 'pivotalcreated'
    UPDATED_AT = 'pivotalupdated'
    CLOSED_AT = 'pivotalclosed'

    UDAS = {
        URL: {'type': 'string', 'label': 'Story URL'},
        DESCRIPTION: {'type': 'string', 'label': 'Story Description'},
        TYPE: {'type': 'string', 'label': 'Story Type'},
        PROJECT_ID: {'type': 'numeric', 'label': 'Project ID'},
        PROJECT_NAME: {'type': 'string', 'label': 'Project Name'},
        FOREIGN_ID: {'type': 'numeric', 'label': 'Story ID'},
        OWNED_BY: {'type': 'string', 'label': 'Story Owned By'},
        REQUEST_BY: {'type': 'string', 'label': 'Story Requested By'},
        ESTIMATE: {'type': 'numeric', 'label': 'Story Estimate'},
        BLOCKERS: {'type': 'string', 'label': 'Story Blockers'},
        CREATED_AT: {'type': 'date', 'label': 'Story Created'},
        UPDATED_AT: {'type': 'date', 'label': 'Story Updated'},
        CLOSED_AT: {'type': 'date', 'label': 'Story Closed'}
    }

    UNIQUE_KEY = (URL,)

    def _normalize_label_to_tag(self, label):
        return re.sub(r'[^a-zA-Z0-9]', '_', label)

    def get_owner(self, issue):
        _, issue = issue
        return issue.get('pivotalowners')

    def get_author(self, issue):
        _, issue = issue
        return issue.get('pivotalrequesters')

    def to_taskwarrior(self):
        description = self.record.get('description')
        created = self.parse_date(self.record.get('created_at'))
        modified = self.parse_date(self.record.get('updated_at'))
        closed = self.parse_date(self.record.get('accepted_at'))

        return {
            'project': self._normalize_label_to_tag(self.extra['project_name']).lower(),
            'priority': self.origin['default_priority'],
            'annotations': self.extra.get('annotations', []),
            'tags': self.get_tags(),

            self.URL: self.record['url'],
            self.DESCRIPTION: description,
            self.TYPE: self.record['story_type'],
            self.PROJECT_ID: int(self.record['project_id']),
            self.PROJECT_NAME: self.extra['project_name'],
            self.FOREIGN_ID: int(self.record['id']),
            self.OWNED_BY: self.extra['owned_user'],
            self.REQUEST_BY: self.extra['request_user'],
            self.ESTIMATE: int(self.record.get('estimate', 0)),
            self.BLOCKERS: self.extra['blockers'],
            self.CREATED_AT: created,
            self.UPDATED_AT: modified,
            self.CLOSED_AT: closed,
        }

    def get_tags(self):
        tags = []

        if not self.origin['import_labels_as_tags']:
            return tags

        context = self.record.copy()
        label_template = Template(self.origin['label_template'])

        for label in map(operator.itemgetter('name'), self.record.get('labels', [])):
            context.update({
                'label': self._normalize_label_to_tag(label)
            })
            tags.append(
                label_template.render(context)
            )

        return tags

    def get_default_description(self):
        return self.build_default_description(
            title=self.record.get('name'),
            url=self.get_processed_url(self.record.get('url')),
            number=int(self.record.get('id')),
            cls=self.record.get('story_type')
        )


class PivotalTrackerService(IssueService, ServiceClient):
    ISSUE_CLASS = PivotalTrackerIssue
    CONFIG_PREFIX = 'pivotaltracker'

    def __init__(self, *args, **kwargs):
        super(PivotalTrackerService, self).__init__(*args, **kwargs)

        self.host=self.config.get('host', 'https://www.pivotaltracker.com/services')
        self.version = self.config.get('version', 'v5')
        self.token = self.config.get('token')
        self.path = "{0}/{1}".format(self.host, self.version)

        self.session = requests.Session()
        self.session.headers.update(
            {
                'X-TrackerToken': self.token,
                'Content-Type': 'application/json'
            }
        )

        self.account_ids = self.config.get(
	    'account_ids', default=[], to_type=aslist)
        self.user_id = self.config.get('user_id', to_type=asint)
        self.only_if_assigned = self.config.get(
            'only_if_assigned', default=True, to_type=asbool)
        self.also_unassigned = self.config.get(
            'also_unassigned', default=False, to_type=asbool)
        self.only_if_author = self.config.get(
            'only_if_author', default=False, to_type=asbool)
        self.exclude_stories = self.config.get(
            'exclude_stories', default=[], to_type=aslist)
        self.exclude_projects = self.config.get(
            'exclude_projects', default=[], to_type=aslist)
        self.exclude_tags = self.config.get(
            'exclude_tag', default=[], to_type=aslist)
        self.import_labels_as_tags = self.config.get(
            'import_labels_as_tags', default=False, to_type=asbool)
        self.label_template = self.config.get(
            'label_template', default='{{label}}', to_type=six.text_type)
        self.import_blockers = self.config.get(
            'import_blockers', default=True, to_type=asbool)
        self.blocker_template = self.config.get(
            'blocker_template', default='Description: {{description}} Resovled: {{resolved}}\n', to_type=six.text_type)
        self.annotation_template = self.config.get(
            'annotation_template', default='Completed: {{complete}} - {{description}}', to_type=six.text_type)
        self.query = self.config.get('query', default="", to_type=six.text_type)

        if not self.query:
            if self.only_if_assigned and not self.also_unassigned:
                self.query += "mywork:{user_id}".format(user_id=self.user_id)
            if self.exclude_stories:
                self.query += " -id:{stories}".format(stories=",".join(self.exclude_stories))
            if self.exclude_tags:
                self.query += " -label:{labels}".format(labels=",".join(self.exclude_tags))
            if self.only_if_author:
                self.query += " requester:{user_id}".format(user_id=self.user_id)

    @classmethod
    def validate_config(cls, service_config, target):
        required = ['user_id', 'token', 'account_ids']

        for item in required:
            if item not in service_config:
                die("[{0}] has no 'pivotaltracker.{1}'".format(target, item))

        if service_config.get('version', default='v5') not in ['v5', 'edge']:
            die("[%s] has an invalid 'pivotaltracker.version'" % target)

        super(PivotalTrackerService, cls).validate_config(service_config, target)

    def get_service_metadata(self):
        return {
            'import_labels_as_tags': self.import_labels_as_tags,
            'label_template': self.label_template,
            'annotation_template': self.annotation_template,
            'import_blockers': self.import_blockers,
            'blocker_template': self.blocker_template
        }

    def annotations(self, annotations, story):
        final_annotations = []
        if self.annotation_comments:
            annotation_template = Template(self.annotation_template)
            for annotation in annotations:
                final_annotations.append(
                    ('task', annotation_template.render(annotation))
                )
        return self.build_annotations(
            final_annotations,
            story.get('url')
        )

    def blockers(self, blocker_list):
        blockers = []

        if not self.import_blockers:
            return blockers

        blocker_template = Template(self.blocker_template)
        for blocker in blocker_list:
            blockers.append(
                blocker_template.render(blocker)
            )

        return ', '.join(blockers) or None

    def issues(self):
        for project in self.get_projects(self.account_ids):
            project_id = project.get('id')
            if project_id not in self.exclude_projects:
                for story in self.get_query(project_id, query=self.query):
                    story_id = story.get('id')
                    tasks = self.get_tasks(
                        project_id,
                        story_id
                    )
                    blockers = self.get_blockers(
                        project_id,
                        story_id
                    )
                    extra = {
                        'project_name': project.get('name'),
                        'annotations': self.annotations(
                            tasks,
                            story
                        ),
                        'owned_user': self.get_user_by_id(
                            project_id,
                            story['owner_ids']
                        ),
                        'request_user': self.get_user_by_id(
                            project_id,
                            [story['requested_by_id']]
                        ),
                        'blockers': self.blockers(blockers)
                    }
                    yield self.get_issue_for_record(story, extra)

    def api_request(self, endpoint, params={}):
        """
        Make a PivotalTracker API request. This takes an absolute urland a list
        of argumnets and return a GET request with the key and token from the
        configuration.
        """
        subkey = params.pop('subkey', None)

        url = "{path}/{endpoint}".format(
            path=self.path,
            endpoint=endpoint
        )
        response = self.session.get(url, params=params)
        json_res = self.json_response(response)

        if subkey is not None:
            json_res = json_res[subkey]

        return json_res

    def get_projects(self, account_ids):
        params = {
            'account_ids': ','.join(account_ids)
        }
        projects = self.api_request(
            'projects',
            params=params)
        return projects

    def get_query(self, project_id, **params):
        params['subkey'] = 'stories'
        query = self.api_request(
            "projects/{project_id}/search".format(project_id=project_id),
            params=params)

        return query['stories']

    def get_tasks(self, project_id, story_id):
        tasks = self.api_request(
            "projects/{project_id}/stories/{story_id}/tasks".format(
                project_id=project_id,
                story_id=story_id))
        return tasks

    def get_blockers(self, project_id, story_id):
        blockers = self.api_request(
            "projects/{project_id}/stories/{story_id}/blockers".format(
                project_id=project_id, story_id=story_id)
        )
        blocker_results = []
        for blocker in blockers:
            blocker['users'] = self.get_user_by_id(
                project_id,
                [blocker['person_id']]
            )
            blocker_results.append(blocker)
        return blocker_results

    def get_user_by_id(self, project_id, user_ids):
        persons = self.api_request(
            "projects/{project_id}/memberships".format(
                project_id=project_id))
        user_list = filter(
            lambda x: x.get('id') in user_ids,
            map(operator.itemgetter('person'), persons)
        )
        return ', '.join(list(map(operator.itemgetter('username'), user_list))) or None
