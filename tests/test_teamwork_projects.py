from .base import ServiceTest, AbstractServiceTest
from bugwarrior.services.teamwork_projects import TeamworkService, TeamworkClient

import responses
import datetime
from dateutil.tz import tzutc

class TestTeamworkIssue(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        'teamwork_projects.host': 'https://test.teamwork_projects.com',
        'teamwork_projects.token': 'arbitrary_token',
    }

    @responses.activate
    def setUp(self):
        super(TestTeamworkIssue, self).setUp()
        self.add_response(
            'https://test.teamwork_projects.com/authenticate.json',
            json={
                'account': {
                    'userId': 5,
                    'firstname': 'Greg',
                    'lastname': 'McCoy'
                }
            }
        )
        self.service = self.get_mock_service(TeamworkService)
        self.arbitrary_issue = { 
            "todo-items": [{
                "id": 5,
                "comments-count": 2,
                "description": "This issue is meant for testing",
                "content": "This is a test issue",
                "project-id": 1,
                "project-name": "Test Project",
                "status": "new",
                "company-name": "Test Company",
                "company-id": 1,
                "creator-id": 1,
                "creator-firstname": "Greg",
                "creator-lastname": "McCoy",
                "updater-id": 0,
                "updater-firstname": "",
                "updater-lastname": "",
                "completed": False,
                "start-date": "",
                "due-date": "2019-12-12T10:06:31Z",
                "created-on": "2018-12-12T10:06:31Z",
                "last-changed-on": "2019-01-16T11:00:44Z",
                "priority": "high",
                "parentTaskId": "",
                "userFollowingComments": True,
                "userFollowingChanges": True,
                "DLM": 0,
                "responsible-party-ids": ["5"]
            }]
        }
        self.arbitrary_extra = {
            "host": "https://test.teamwork_projects.com",
            "annotations": [("Greg McCoy", "Test comment"), ("Bob Test", "testing")]
        }
        self.arbitrary_comments = {
            "comments": [
                {
                  "project-id": "999",
                  "author-lastname": "User",
                  "datetime": "2014-03-31T13:03:29Z",
                  "author_id": "999",
                  "id": "999",
                  "company-name": "Test Company",
                  "last-changed-on": "",
                  "company-id": "999",
                  "project-name": "demo",
                  "body": "A test comment",
                  "commentNo": "1",
                  "author-firstname": "Demo",
                  "comment-link": "tasks/436523?c=93",
                  "author-id": "999"
                }
            ]
        }



    @responses.activate
    def test_to_taskwarrior(self):
        issue = self.service.get_issue_for_record(self.arbitrary_issue["todo-items"][0], self.arbitrary_extra)
        data = self.arbitrary_issue["todo-items"][0]
        expected_data = {
            'project': data["project-name"],
            'priority': "H",
            'due': datetime.datetime(2019, 12, 12, 10, 6, 31, tzinfo=tzutc()),
            'entry': datetime.datetime(2018, 12, 12, 10, 6, 31, tzinfo=tzutc()),
            'end': "",
            'modified': datetime.datetime(2019, 1, 16, 11, 0, 44, tzinfo=tzutc()),
            'annotations': self.arbitrary_extra.get("annotations", ""),
            issue.URL: "https://test.teamwork_projects.com/#/tasks/5",
            issue.TITLE: data["content"],
            issue.DESCRIPTION_LONG: data["description"],
            issue.PROJECT_ID: int(data["project-id"]),
            issue.STATUS: "Open",
            issue.ID: int(data["id"]),
            "annotations": [('Greg McCoy', 'Test comment'), ('Bob Test', 'testing')],
        }
        actual_output = issue.to_taskwarrior()
        self.assertEqual(actual_output, expected_data)

    @responses.activate
    def test_issues(self):
        self.add_response(
            'https://test.teamwork_projects.com/tasks/5/comments.json',
            json=self.arbitrary_comments
        )
        self.add_response(
            'https://test.teamwork_projects.com/tasks.json',
            json=self.arbitrary_issue
        )
        issue = next(self.service.issues())
        data = self.arbitrary_issue["todo-items"][0]
        expected_data = {
            'project': data["project-name"],
            'priority': "H",
            'due': datetime.datetime(2019, 12, 12, 10, 6, 31, tzinfo=tzutc()),
            'entry': datetime.datetime(2018, 12, 12, 10, 6, 31, tzinfo=tzutc()),
            'end': "",
            'modified': datetime.datetime(2019, 1, 16, 11, 0, 44, tzinfo=tzutc()),
            'annotations': self.arbitrary_extra.get("annotations", ""),
            'description': '(bw)Is#5 - This is a test issue .. https://test.teamwork_projects.com/#/tasks/5', 
            issue.URL: "https://test.teamwork_projects.com/#/tasks/5",
            issue.TITLE: data["content"],
            issue.DESCRIPTION_LONG: data["description"],
            issue.PROJECT_ID: int(data["project-id"]),
            issue.STATUS: "Open",
            issue.ID: int(data["id"]),
            "annotations": ['@Demo User - A test comment'],
            "tags": [],
        }
        issue.user_id = "5"
        issue.name = "Greg McCoy"
        self.assertEqual(issue.get_taskwarrior_record(), expected_data)
        self.assertEqual(issue.get_owner(issue), "Greg McCoy")
        self.assertEqual(issue.get_author(issue), "Greg McCoy")
