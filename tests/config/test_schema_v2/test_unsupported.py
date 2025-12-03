import unittest

import pydantic

from bugwarrior.config import schema


class TestUnsupportedOption(unittest.TestCase):
    def test_unsupportedoption_falsey(self):
        adapter = pydantic.TypeAdapter(schema.UnsupportedOption[str])
        self.assertEqual(adapter.validate_python(''), '')

    def test_unsupportedoption_truthy(self):
        adapter = pydantic.TypeAdapter(schema.UnsupportedOption[str])
        with self.assertRaises(pydantic.ValidationError):
            adapter.validate_python('foo')

    def test_unsupportedoption_in_model(self):
        class Config(pydantic.BaseModel):
            deprecated: schema.UnsupportedOption[bool] = False

        self.assertFalse(Config().deprecated)
        with self.assertRaises(pydantic.ValidationError):
            Config(deprecated=True)
