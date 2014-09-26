from v1pysdk import V1Meta
from six.moves.urllib import parse

from bugwarrior.services import IssueService, Issue
from bugwarrior.config import die, get_service_password


class VersionOneIssue(Issue):
    TASK_NAME = 'versiononetaskname'
    TASK_DESCRIPTION = 'versiononetaskdescrption'
    TASK_ESTIMATE = 'versiononetaskestimate'
    TASK_DETAIL_ESTIMATE = 'versiononetaskdetailestimate'
    TASK_TO_DO = 'versiononetasktodo'
    TASK_REFERENCE = 'versiononetaskreference'
    TASK_URL = 'versiononetaskurl'
    TASK_OID = 'versiononetaskoid'

    STORY_NAME = 'versiononestoryname'
    STORY_DESCRIPTION = 'versiononestorydescription'
    STORY_ESTIMATE = 'versiononestoryestimate'
    STORY_DETAIL_ESTIMATE = 'versiononestorydetailestimate'
    STORY_URL = 'versiononestoryurl'
    STORY_OID = 'versiononestoryoid'

    UDAS = {
        TASK_NAME: {
            'type': 'string',
            'label': 'VersionOne Task Name'
        },
        TASK_DESCRIPTION: {
            'type': 'string',
            'label': 'VersionOne Task Description'
        },
        TASK_ESTIMATE: {
            'type': 'numeric',
            'label': 'VersionOne Task Estimate'
        },
        TASK_DETAIL_ESTIMATE: {
            'type': 'numeric',
            'label': 'VersionOne Task Detail Estimate',
        },
        TASK_TO_DO: {
            'type': 'numeric',
            'label': 'VersionOne Task To Do'
        },
        TASK_REFERENCE: {
            'type': 'string',
            'label': 'VersionOne Task Reference'
        },
        TASK_URL: {
            'type': 'string',
            'label': 'VersionOne Task URL'
        },
        TASK_OID: {
            'type': 'string',
            'label': 'VersionOne Task Object ID'
        },
        STORY_NAME: {
            'type': 'string',
            'label': 'VersionOne Story Name'
        },
        STORY_DESCRIPTION: {
            'type': 'string',
            'label': 'VersionOne Story Description'
        },
        STORY_ESTIMATE: {
            'type': 'numeric',
            'label': 'VersionOne Story Estimate'
        },
        STORY_DETAIL_ESTIMATE: {
            'type': 'numeric',
            'label': 'VersionOne Story Detail Estimate'
        },
        STORY_URL: {
            'type': 'string',
            'label': 'VersionOne Story URL'
        },
        STORY_OID: {
            'type': 'string',
            'label': 'VersionOne Story Object ID'
        },
    }

    UNIQUE_KEY = (TASK_URL, )

    def to_taskwarrior(self):
        return {
            'project': self.extra['project'],

            self.TASK_NAME: self.record['task']['Name'],
            self.TASK_DESCRIPTION: self.record['task']['Description'],
            self.TASK_ESTIMATE: self.record['task']['Estimate'],
            self.TASK_DETAIL_ESTIMATE: self.record['task']['DetailEstimate'],
            self.TASK_TO_DO: self.record['task']['ToDo'],
            self.TASK_REFERENCE: self.record['task']['Reference'],
            self.TASK_URL: self.record['task']['url'],
            self.TASK_OID: self.record['task']['idref'],

            self.STORY_NAME: self.record['story']['Name'],
            self.STORY_DESCRIPTION: self.record['story']['Description'],
            self.STORY_ESTIMATE: self.record['story']['Estimate'],
            self.STORY_DETAIL_ESTIMATE: self.record['story']['DetailEstimate'],
            self.STORY_URL: self.record['story']['url'],
            self.STORY_OID: self.record['story']['idref'],
        }

    def get_default_description(self):
        return self.build_default_description(
            title=': '.join([
                self.record['story']['Name'],
                self.record['task']['Name'],
            ]),
            url=self.record['task']['url'],
            number=self.record['story']['Number'],
            cls='task',
        )


class VersionOneService(IssueService):
    ISSUE_CLASS = VersionOneIssue
    CONFIG_PREFIX = 'versionone'

    TASK_COLLECT_DATA = {
        'Name',
        'Description',
        'Estimate',
        'DetailEstimate',
        'ToDo',
        'Reference',
        'url',
        'idref',
    }
    STORY_COLLECT_DATA = {
        'Name',
        'Description',
        'Estimate',
        'DetailEstimate',
        'Number',
        'url',
        'idref',
    }

    def __init__(self, *args, **kw):
        super(VersionOneService, self).__init__(*args, **kw)

        parsed_address = parse.urlparse(
            self.config_get('base_uri')
        )
        self.address = parsed_address.netloc
        self.instance = parsed_address.path.strip('/')
        self.username = self.config_get('username')
        self.password = self.config_get('password')
        self.project = self.config_get_default('project', default='')
        self.timebox_name = self.config_get_default('timebox_name')

        if not self.password or self.password.startswith('@oracle:'):
            username = self.config_get('username')
            service = "versionone://%s@v1host.com/%s" % (username, username)
            self.password = get_service_password(
                service, username, oracle=self.password,
                interactive=self.config.interactive
            )

    @classmethod
    def validate_config(cls, config, target):
        options = (
            'versionone.base_uri',
            'versionone.username',
            'versionone.password'
        )
        for option in options:
            if not config.has_option(target, option):
                die("[%s] has no '%s'" % (target, option))

        IssueService.validate_config(config, target)

    def get_meta(self):
        if not hasattr(self, '_meta'):
            self._meta = V1Meta(
                address=self.address,
                instance=self.instance,
                username=self.username,
                password=self.password
            )
        return self._meta

    def get_assignments(self, username):
        meta = self.get_meta()
        where = {
            'IsCompleted': False
        }
        if self.timebox_name:
            where['Parent.Timebox.Name'] = self.timebox_name

        tasks = meta.Task.select(
            'Name',
            'Parent',
            'Description',
            'Estimate',
            'DetailEstimate',
            'ToDo',
            'Reference',
        ).filter(
            "Owners.Username='{username}'".format(username=self.username)
        ).where(**where)
        return tasks

    def issues(self):
        for issue in self.get_assignments(self.username):
            issue_data = {
                'task': {},
                'story': {}
            }
            for column in self.TASK_COLLECT_DATA:
                issue_data['task'][column] = getattr(
                    issue, column, None
                )
            for column in self.STORY_COLLECT_DATA:
                issue_data['story'][column] = getattr(
                    issue.Parent, column, None
                )

            extras = {
                'project': self.project
            }

            yield self.get_issue_for_record(
                issue_data,
                extras
            )
