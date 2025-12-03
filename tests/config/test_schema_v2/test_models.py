import unittest

import pydantic

from bugwarrior.config import schema


class TestHooks(unittest.TestCase):
    def test_defaults(self):
        hooks = schema.Hooks()
        self.assertEqual(hooks.pre_import, [])

    def test_pre_import_from_string(self):
        hooks = schema.Hooks(pre_import='hook1, hook2')
        self.assertEqual(hooks.pre_import, ['hook1', 'hook2'])


class TestNotifications(unittest.TestCase):
    def test_defaults(self):
        notifications = schema.Notifications()
        self.assertFalse(notifications.notifications)
        self.assertIsNone(notifications.backend)

    def test_valid_backend(self):
        notifications = schema.Notifications(backend='gobject')
        self.assertEqual(notifications.backend, 'gobject')

    def test_invalid_backend(self):
        with self.assertRaises(pydantic.ValidationError):
            schema.Notifications(backend='invalid')


class TestSchemaBase(unittest.TestCase):
    def test_defaults(self):
        base = schema.SchemaBase()
        self.assertIsInstance(base.hooks, schema.Hooks)
        self.assertIsInstance(base.notifications, schema.Notifications)

    def test_extra_ignored(self):
        base = schema.SchemaBase(unknown_field='ignored')
        self.assertFalse(hasattr(base, 'unknown_field'))


class TestBaseConfig(unittest.TestCase):
    def test_frozen(self):
        hooks = schema.Hooks()
        with self.assertRaises(pydantic.ValidationError):
            hooks.pre_import = ['changed']

    def test_extra_forbid(self):
        with self.assertRaises(pydantic.ValidationError):
            schema.Hooks(unknown='value')
