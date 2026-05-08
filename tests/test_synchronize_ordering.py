import copy

import taskw

from bugwarrior import db
from bugwarrior.types import CollectedIssue

from .base import ConfigTest


class TestSynchronizeOrdering(ConfigTest):
    def setUp(self):
        super().setUp()
        self.config = {
            'general': {'targets': ['my_service'], 'taskrc': self.taskrc},
            'my_service': {
                'service': 'github',
                'login': 'ralphbean',
                'username': 'ralphbean',
                'token': 'abc123',
            },
        }
        self.bwconfig = self.validate()
        self.tw = taskw.TaskWarrior(self.taskrc)

    @staticmethod
    def make_github_issue(tags=None, annotations=None):
        return {
            'description': 'Synchronized issue',
            'githubtype': 'issue',
            'githuburl': 'https://example.com/issue/1',
            'priority': 'M',
            'tags': tags or [],
            'annotations': annotations or [],
        }

    @staticmethod
    def annotation_descriptions(task):
        return [annotation['description'] for annotation in task.get('annotations', [])]

    def synchronize(self, issue):
        issue_generator = [
            CollectedIssue(
                taskwarrior_data=copy.deepcopy(issue),
                target="my_service",
                identifier="abcd",
            )
        ]
        db.synchronize(issue_generator, self.bwconfig)

    def get_task(self):
        return self.tw.load_tasks()['pending'][0]

    def test_create_preserves_annotation_order_and_duplicates(self):
        """Creating a task preserves remote annotation order and duplicates."""
        issue = self.make_github_issue(annotations=['first', 'second', 'first'])

        self.synchronize(issue)

        task = self.get_task()
        assert self.annotation_descriptions(task) == ['first', 'second', 'first']

    def test_update_preserves_existing_annotation_order(self):
        """Updating a task keeps existing annotations in their stored order."""
        issue = self.make_github_issue(annotations=['first', 'second', 'first'])
        self.synchronize(issue)

        issue['annotations'] = ['first', 'third', 'third', 'fourth']
        self.synchronize(issue)

        task = self.get_task()
        descriptions = self.annotation_descriptions(task)
        assert descriptions[:3] == ['first', 'second', 'first']
        # taskw.task_update uses a set for annotations it creates, so do not
        # rely on ordering among newly-added annotations.
        assert sorted(descriptions[3:]) == ['fourth', 'third']

    def test_update_deduplicates_new_annotations_when_none_exist(self):
        """Updating a task deduplicates new annotations via taskw.task_update."""
        issue = self.make_github_issue(annotations=[])
        self.synchronize(issue)

        issue['annotations'] = ['same', 'same', 'other']
        self.synchronize(issue)

        task = self.get_task()
        assert sorted(self.annotation_descriptions(task)) == ['other', 'same']

    def test_create_sorts_and_deduplicates_tags(self):
        """Creating a task stores tags as a sorted unique collection."""
        issue = self.make_github_issue(tags=['beta', 'alpha', 'beta'])

        self.synchronize(issue)

        task = self.get_task()
        assert task['tags'] == ['alpha', 'beta']

    def test_update_sorts_and_deduplicates_tags(self):
        """Updating a task keeps tags sorted and deduplicated."""
        issue = self.make_github_issue(tags=['beta', 'alpha', 'beta'])
        self.synchronize(issue)

        issue['tags'] = ['delta', 'alpha', 'delta', 'gamma']
        self.synchronize(issue)

        task = self.get_task()
        assert task['tags'] == ['alpha', 'beta', 'delta', 'gamma']
