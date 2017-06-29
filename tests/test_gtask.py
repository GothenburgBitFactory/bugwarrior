import mock
import os.path
from .base import ServiceTest, AbstractServiceTest
import bugwarrior.services.gtask as gtask

TEST_LISTS = [{'title': 'list1', 'id': '1'}, {'title': 'list2', 'id': '2'}]
TEST_TASK = {
    'id': 'test_task_1',
    'selfLink': 'http://www.example.com/task/test_task_1',
    'title': 'Test Task 1',
    'links': [{
        'link': 'http://www.example.com/link/1',
        'description': '1'}]
    }

class TestGtaskIssue(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
            'gtask.add_tags': 'foo',
            'gtask.lists': 'list1, list2',
            'gtask.login_name': 'test@example.com',
    }
    def setUp(self):
        super(TestGtaskIssue, self).setUp()

        mock_api = mock.Mock()
        mock_api().tasklists().list().execute.return_value = {'items': TEST_LISTS}
        mock_api().tasks().list().execute.return_value = {'items': [TEST_TASK]}
        gtask.GtaskService.build_api = mock_api
        self.service = self.get_mock_service(gtask.GtaskService, section='test_section')

    def test_to_taskwarrior(self):
        task = TEST_TASK
        issue = self.service.get_issue_for_record(
                task,
                {'tasklist': 'test_list'})
        expected = {
            'gtaskid': 'test_task_1',
            'gtasklist': 'test_list',
            'gtasktitle': 'Test Task 1',
            'gtaskurl': 'http://www.example.com/task/test_task_1',
            'priority': 'M',
            'gtasklinktitle': '1',
            'gtasklinkurl': 'http://www.example.com/link/1',
        }
        taskwarrior = issue.to_taskwarrior()

        self.assertEqual(taskwarrior, expected)

    def test_issues(self):
        issue = next(self.service.issues())
        expected = {
            'description': u'(bw)Is#t_task_1 - Test Task 1',
            'gtaskid': 'test_task_1',
            'gtasklist': 'list1',
            'gtasktitle': 'Test Task 1',
            'gtaskurl': 'http://www.example.com/task/test_task_1',
            'priority': 'M',
            'gtasklinktitle': '1',
            'gtasklinkurl': 'http://www.example.com/link/1',
            'tags': ['foo']}
        taskwarrior = issue.get_taskwarrior_record()
        self.assertEqual(taskwarrior, expected)
