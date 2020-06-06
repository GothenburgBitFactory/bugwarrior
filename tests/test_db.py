import copy
import subprocess
import unittest

import taskw.task

from bugwarrior import db
from bugwarrior.config.load import BugwarriorConfigParser

from .base import ConfigTest


class TestMergeLeft(unittest.TestCase):
    def setUp(self):
        self.issue_dict = {'annotations': ['testing']}

    def assertMerged(self, local, remote, **kwargs):
        db.merge_left('annotations', local, remote, **kwargs)
        self.assertEqual(local, remote)

    def test_with_dict(self):
        self.assertMerged({}, self.issue_dict)

    def test_with_taskw(self):
        self.assertMerged(taskw.task.Task({}), self.issue_dict)

    def test_already_in_sync(self):
        self.assertMerged(self.issue_dict, self.issue_dict)

    def test_rough_equality_hamming_false(self):
        """ When hamming=False, rough equivalents are duplicated. """
        remote = {'annotations': ['\n  testing  \n']}

        db.merge_left('annotations', self.issue_dict, remote, hamming=False)
        self.assertEqual(len(self.issue_dict['annotations']), 2)

    def test_rough_equality_hamming_true(self):
        """ When hamming=True, rough equivalents are not duplicated. """
        remote = {'annotations': ['\n  testing  \n']}

        db.merge_left('annotations', self.issue_dict, remote, hamming=True)
        self.assertEqual(len(self.issue_dict['annotations']), 1)


class TestReplaceLeft(unittest.TestCase):
    def setUp(self):
        self.issue_dict = {'tags': ['test', 'test2']}
        self.remote = {'tags': ['remote_tag1', 'remote_tag2']}

    def assertReplaced(self, local, remote, **kwargs):
        db.replace_left('tags', local, remote, **kwargs)
        self.assertEqual(local, remote)

    def test_with_dict(self):
        self.assertReplaced({}, self.issue_dict)

    def test_with_taskw(self):
        self.assertReplaced(taskw.task.Task({}), self.issue_dict)

    def test_already_in_sync(self):
        self.assertReplaced(self.issue_dict, self.issue_dict)

    def test_replace(self):
        self.assertReplaced(self.issue_dict, self.remote)

    def test_replace_with_keeped_item(self):
        """ When keeped_item is set, all item in this list are keeped """
        result = {'tags': ['test', 'remote_tag1', 'remote_tag2']}
        print(self.issue_dict)
        keeped_items = ['test']
        db.replace_left('tags', self.issue_dict, self.remote, keeped_items)
        self.assertEqual(self.issue_dict, result)


class TestSynchronize(ConfigTest):

    def setUp(self):
        super().setUp()

        self.config = BugwarriorConfigParser()
        self.config.add_section('general')
        self.config.set('general', 'targets', 'my_service')
        self.config.set('general', 'taskrc', self.taskrc)
        self.config.set('general', 'static_fields', 'project, priority')
        self.config.add_section('my_service')
        self.config.set('my_service', 'service', 'github')
        self.config.set('my_service', 'github.login', 'ralphbean')
        self.config.set('my_service', 'github.username', 'ralphbean')
        self.config.set('my_service', 'github.password', 'abc123')

        self.bwconfig = self.validate()

        self.tw = taskw.TaskWarrior(self.taskrc)

        self.synchronizer = db.Synchronizer(self.bwconfig, 'general')

        self.issue = {
            'description': 'Blah blah blah. ☃',
            'project': 'sample_project',
            'githubtype': 'issue',
            'githuburl': 'https://example.com',
            'priority': 'M',
            'tags': ['foo'],
        }

    @staticmethod
    def remove_non_deterministic_keys(tasks: dict) -> dict:
        for status in ['pending', 'completed']:
            for task in tasks[status]:
                del task['modified']
                del task['entry']
                del task['uuid']
                task['tags'] = sorted(task['tags'])
        return tasks

    def get_tasks(self) -> dict:
        return self.remove_non_deterministic_keys(self.tw.load_tasks())

    def assertUpdatesEqual(self, updates: dict):
        # Make tag order deterministic.
        for key in ['new', 'existing', 'changed', 'closed']:
            for task in self.synchronizer.updates[key]:
                task['tags'] = sorted(task['tags'])
            for task in updates[key]:
                task['tags'] = sorted(task['tags'])

        self.assertEqual(self.synchronizer.updates, updates)

    def test_synchronize_integration(self):

        self.assertEqual(self.tw.load_tasks(), {'completed': [], 'pending': []})

        # TEST NEW ISSUE AND EXISTING ISSUE.
        for _ in range(2):
            db.synchronize(iter((self.issue,)), self.bwconfig, 'general')

            self.assertEqual(self.get_tasks(), {
                'completed': [],
                'pending': [{
                    'project': 'sample_project',
                    'priority': 'M',
                    'status': 'pending',
                    'description': 'Blah blah blah. ☃',
                    'githuburl': 'https://example.com',
                    'githubtype': 'issue',
                    'id': 1,
                    'tags': ['foo'],
                    'urgency': 5.7,
                }]})

        # TEST CHANGED ISSUE.
        self.issue['description'] = 'Yada yada yada.'

        # Change static field
        self.issue['project'] = 'other_project'

        db.synchronize(iter((self.issue,)), self.bwconfig, 'general')

        self.assertEqual(self.get_tasks(), {
            'completed': [],
            'pending': [{
                'priority': 'M',
                'project': 'sample_project',
                'status': 'pending',
                'description': 'Yada yada yada.',
                'githuburl': 'https://example.com',
                'githubtype': 'issue',
                'id': 1,
                'tags': ['foo'],
                'urgency': 5.7,
            }]})

        # TEST CLOSED ISSUE.
        db.synchronize(iter(()), self.bwconfig, 'general')

        completed_tasks = self.tw.load_tasks()

        tasks = self.remove_non_deterministic_keys(copy.deepcopy(completed_tasks))
        del tasks['completed'][0]['end']
        self.assertEqual(tasks, {
            'completed': [{
                'project': 'sample_project',
                'description': 'Yada yada yada.',
                'githubtype': 'issue',
                'githuburl': 'https://example.com',
                'id': 0,
                'priority': 'M',
                'status': 'completed',
                'tags': ['foo'],
                'urgency': 5.7,
            }],
            'pending': []})

        # TEST REOPENED ISSUE
        db.synchronize(iter((self.issue,)), self.bwconfig, 'general')

        tasks = self.tw.load_tasks()
        self.assertEqual(
            completed_tasks['completed'][0]['uuid'],
            tasks['pending'][0]['uuid'])

        tasks = self.remove_non_deterministic_keys(tasks)
        self.assertEqual(tasks, {
            'completed': [],
            'pending': [{
                'priority': 'M',
                'project': 'sample_project',
                'status': 'pending',
                'description': 'Yada yada yada.',
                'githuburl': 'https://example.com',
                'githubtype': 'issue',
                'id': 1,
                'tags': ['foo'],
                'urgency': 5.7,
            }]})

    def test_duplicate_issues(self):
        """
        Issues should be deduplicated with their tags merged.

        See https://github.com/ralphbean/bugwarrior/issues/601.
        """
        duplicate_issue = copy.deepcopy(self.issue)
        duplicate_issue['tags'] = ['bar']

        issue_generator = iter((self.issue, duplicate_issue,))

        self.synchronizer.aggregate_updates(issue_generator)

        self.assertUpdatesEqual({
            'new': [{
                'project': 'sample_project',
                'priority': 'M',
                'description': 'Blah blah blah. ☃',
                'githuburl': 'https://example.com',
                'githubtype': 'issue',
                'tags': ['bar', 'foo'],
            }],
            'existing': [],
            'changed': [],
            'closed': []
        })

    @unittest.skipIf(
        subprocess.run(['task', '--version'], capture_output=True).stdout.strip() <= b'2.5.1',
        'https://github.com/ralphbean/bugwarrior/issues/733')
    def test_synchronize_depends_description(self):
        """
        Certain versions of taskwarrior/taskw don't properly handle
        descriptions that start with taskwarrior keywords.

        See https://github.com/ralphbean/bugwarrior/issues/733.
        """
        self.issue['description'] = 'depends filter does not work with IDs'

        # Note: In order to test the desired taskwarrior behavior we need to
        # actually commit the changes to the database.
        db.synchronize(iter((self.issue,)), self.bwconfig, 'general')

        self.assertEqual(self.get_tasks(), {
            'completed': [],
            'pending': [{
                'priority': 'M',
                'project': 'sample_project',
                'status': 'pending',
                'description': 'depends filter does not work with IDs',
                'githuburl': 'https://example.com',
                'githubtype': 'issue',
                'id': 1,
                'tags': ['foo'],
                'urgency': 5.7,
            }]
        })


class TestUDAs(ConfigTest):
    def test_udas(self):
        self.config = BugwarriorConfigParser()
        self.config.add_section('general')
        self.config.set('general', 'targets', 'my_service')
        self.config.add_section('my_service')
        self.config.set('my_service', 'service', 'github')
        self.config.set('my_service', 'github.login', 'ralphbean')
        self.config.set('my_service', 'github.username', 'ralphbean')
        self.config.set('my_service', 'github.password', 'abc123')
        self.config.set('my_service', 'service', 'github')

        conf = self.validate()
        udas = sorted(list(db.get_defined_udas_as_strings(conf, 'general')))
        self.assertEqual(udas, [
            'uda.githubbody.label=Github Body',
            'uda.githubbody.type=string',
            'uda.githubclosedon.label=GitHub Closed',
            'uda.githubclosedon.type=date',
            'uda.githubcreatedon.label=Github Created',
            'uda.githubcreatedon.type=date',
            'uda.githubmilestone.label=Github Milestone',
            'uda.githubmilestone.type=string',
            'uda.githubnamespace.label=Github Namespace',
            'uda.githubnamespace.type=string',
            'uda.githubnumber.label=Github Issue/PR #',
            'uda.githubnumber.type=numeric',
            'uda.githubrepo.label=Github Repo Slug',
            'uda.githubrepo.type=string',
            'uda.githubstate.label=GitHub State',
            'uda.githubstate.type=string',
            'uda.githubtitle.label=Github Title',
            'uda.githubtitle.type=string',
            'uda.githubtype.label=Github Type',
            'uda.githubtype.type=string',
            'uda.githubupdatedat.label=Github Updated',
            'uda.githubupdatedat.type=date',
            'uda.githuburl.label=Github URL',
            'uda.githuburl.type=string',
            'uda.githubuser.label=Github User',
            'uda.githubuser.type=string',
        ])
