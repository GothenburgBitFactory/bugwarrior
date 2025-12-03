import typing
import unittest

import pydantic

from bugwarrior.config import schema


class NoSchemeUrlModel(pydantic.BaseModel):
    host: schema.NoSchemeUrl
    host_with_default: schema.NoSchemeUrl = "default.example.com"
    host_optional: typing.Optional[schema.NoSchemeUrl] = None


class StrippedUrlModel(pydantic.BaseModel):
    url: schema.StrippedTrailingSlashUrl
    url_optional: typing.Optional[schema.StrippedTrailingSlashUrl] = None


class TestNoSchemeUrl(unittest.TestCase):
    def test_valid_host(self):
        model = NoSchemeUrlModel(host="github.com")
        self.assertEqual(model.host, "github.com")

    def test_valid_host_with_path(self):
        model = NoSchemeUrlModel(host="github.com/org/repo")
        self.assertEqual(model.host, "github.com/org/repo")

    def test_rejects_scheme(self):
        with self.assertRaises(pydantic.ValidationError) as ctx:
            NoSchemeUrlModel(host="https://github.com")

        error = ctx.exception.errors()[0]
        self.assertEqual(error["type"], "url_scheme_not_allowed")
        self.assertIn("https", error["msg"])

    def test_rejects_empty_string(self):
        with self.assertRaises(pydantic.ValidationError):
            NoSchemeUrlModel(host="")

    def test_default_value(self):
        model = NoSchemeUrlModel(host="github.com")
        self.assertEqual(model.host_with_default, "default.example.com")

    def test_optional_none(self):
        model = NoSchemeUrlModel(host="github.com")
        self.assertIsNone(model.host_optional)


class TestStrippedTrailingSlashUrl(unittest.TestCase):
    def test_strips_trailing_slash(self):
        model = StrippedUrlModel(url="https://example.com/path/")
        self.assertEqual(str(model.url), "https://example.com/path")

    def test_no_trailing_slash_unchanged(self):
        model = StrippedUrlModel(url="https://example.com/path")
        self.assertEqual(str(model.url), "https://example.com/path")

    def test_optional_none(self):
        model = StrippedUrlModel(url="https://example.com")
        self.assertIsNone(model.url_optional)
