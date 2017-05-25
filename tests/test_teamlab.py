from builtins import next
import mock
import responses

from bugwarrior.services.teamlab import TeamLabService

from .base import ServiceTest, AbstractServiceTest


class TestTeamlabIssue(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        'teamlab.hostname': 'something',
        'teamlab.login': 'alkjdsf',
        'teamlab.password': 'lkjklj',
        'teamlab.project_name': 'abcdef',
    }
    arbitrary_issue = {
        'title': 'Hello',
        'id': 10,
        'projectOwner': {
            'id': 140,
        },
        'status': 1,
    }

    def setUp(self):
        super(TestTeamlabIssue, self).setUp()
        with mock.patch(
            'bugwarrior.services.teamlab.TeamLabClient.authenticate'
        ):
            self.service = self.get_mock_service(TeamLabService)

    def test_to_taskwarrior(self):
        arbitrary_url = 'http://galkjsdflkj.com/'

        issue = self.service.get_issue_for_record(self.arbitrary_issue)

        expected_output = {
            'project': self.SERVICE_CONFIG['teamlab.project_name'],
            'priority': self.service.default_priority,
            issue.TITLE: self.arbitrary_issue['title'],
            issue.FOREIGN_ID: self.arbitrary_issue['id'],
            issue.URL: arbitrary_url,
            issue.PROJECTOWNER_ID: self.arbitrary_issue['projectOwner']['id']
        }

        def get_url(*args):
            return arbitrary_url

        with mock.patch.object(issue, 'get_issue_url', side_effect=get_url):
            actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

    @responses.activate
    def test_issues(self):
        self.add_response(
            'http://something/api/1.0/project/task/@self.json',
            json=[self.arbitrary_issue])

        issue = next(self.service.issues())

        expected = {
            'description':
                u'(bw)Is#10 - Hello .. http://something/products/projects/tasks.aspx?prjID=140&id=10',
            'priority': 'M',
            'project': 'abcdef',
            'tags': [],
            'teamlabid': 10,
            'teamlabprojectownerid': 140,
            'teamlabtitle': u'Hello',
            'teamlaburl':
                'http://something/products/projects/tasks.aspx?prjID=140&id=10'}

        self.assertEqual(issue.get_taskwarrior_record(), expected)
