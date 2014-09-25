import json
import requests
from twiggy import log

from bugwarrior.services import IssueService, Issue
from bugwarrior.config import die, get_service_password


class VersionOneIssue(Issue):
    OID = 'versiononeoid'
    DESCRIPTION = 'versiononedescription'
    ESTIMATE = 'versiononeestimate'
    DETAIL_ESTIMATE = 'versiononedetailestimate'
    TYPE = 'versiononetype'
    NAME = 'versiononename'

    UDAS = {
        OID: {
            'type': 'string',
            'label': 'VersionOne ID',
        },
        DESCRIPTION: {
            'type': 'string',
            'label': 'VersionOne Description',
        },
        ESTIMATE: {
            'type': 'numeric',
            'label': 'VersionOne Estimate',
        },
        DETAIL_ESTIMATE: {
            'type': 'numeric',
            'label': 'VersionOne DetailEstimate',
        },
        TYPE: {
            'type': 'string',
            'label': 'VersionOne Type',
        },
        NAME: {
            'type': 'string',
            'label': 'VersionOne Name',
        }
    }
    UNIQUE_KEY = (OID, )

    def to_taskwarrior(self):
        return {
            self.OID: self.record['_oid'],
            self.DESCRIPTION: self.record['Description'],
            self.ESTIMATE: self.record['Estimate'],
            self.DETAIL_ESTIMATE: self.record['DetailEstimate'],
            self.NAME: self.record['Name'],
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['Name'],
            number=self.record['OID'],
        )


class VersionOneService(IssueService):
    ISSUE_CLASS = VersionOneIssue
    CONFIG_PREFIX = 'versionone'

    ITEMTYPES = {
        'Task': {
            'columns': [
                'Name',
                'Estimate',
                'DetailEstimate',
                'Description',
            ],
        },
    }

    def __init__(self, *args, **kw):
        super(VersionOneService, self).__init__(*args, **kw)

        self.url = self.config_get('base_uri')
        username = self.config_get('username')
        password = self.config_get('password')

        raw_item_types = self.config_get_default(
            'item_types',
            default='Task',
            to_type=six.text_type
        ).split(',')
        self.item_types = []
        for item_type in raw_item_types:
            if item_type in self.ITEMTYPES:
                self.item_types.append(item_type)
            else:
                log.name(self.target).warning(
                    "%s is not a known VersionOne item type", item_type
                )

        if not password or password.startswith('@oracle:'):
            username = self.config_get('username')
            service = "versionone://%s@v1host.com/%s" % (username, username)
            password = get_service_password(
                service, username, oracle=password,
                interactive=self.config.interactive
            )
        self.auth = (username, password)

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

        return super(VersionOneService, self).validate_config(config, target)

    def get_data(self, query):
        response = requests.get(
            self.url + '/query.v1',
            auth=self.auth,
            data=json.dumps(query)
        )

        if response.status_code != 200:
            raise IOError(
                "Non-200 status code %s; %s; %s" % (
                    response.status_code,
                    json.dumps(query),
                    response.text
                )
            )
        if callable(response.json):
            # Newer python-requests
            return response.json()
        else:
            # Older python-requests
            return response.json

    def get_item_data(self, oid):
        item_type, _ = oid.split(':', 1)
        data = self.get-data({
            'from': item_type,
            'select': self.ITEMTYPES[item_type]['columns'],
            'where': {
                'ID': oid
            }
        })[0][0]

        return item_type, data

    def get_assignments(self, username):
        items = {}

        result = self.get_data({
            'from': 'Member'
            'select': [
                'OwnedWorkitems',
            ],
            'where': {
                'Username': username
            }
        })
        for item in result[0][0]['OwnedWorkItems']:
            item_type, _ = item['_oid'].split(':', 1)

            if item_type not in items:
                items[item_type] = []

            items[item_type].append(item['_oid'])

        for item_type, items in item_type.items():
            if item_type not in self.item_types:
                continue
            for item in items:
                yield self.get_item_data(item)

    def issues(self):
        for item_type, issue in self.get_assignments(self.username):
            yield self.get_issue_for_record(issue)
