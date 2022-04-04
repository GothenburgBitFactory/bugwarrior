import os.path
import pathlib
import subprocess
import tempfile
import unittest

from bugwarrior import config

from .base import ConfigTest

DOCS_PATH = str(pathlib.Path(__file__).parent / '../bugwarrior/docs')


class DocsTest(unittest.TestCase):
    def test_docs_build_without_warning(self):
        with tempfile.TemporaryDirectory() as buildDir:
            subprocess.run(
                ['sphinx-build', '-n', '-W', '-v', DOCS_PATH, buildDir],
                check=True)

    def test_manpage_build_without_warning(self):
        with tempfile.TemporaryDirectory() as buildDir:
            subprocess.run(
                ['sphinx-build', '-b', 'man', '-n', '-W', '-v', DOCS_PATH, buildDir],
                check=True)


class ExampleBugwarriorrcTest(ConfigTest):
    def test_example_bugwarriorrc(self):
        os.environ['BUGWARRIORRC'] = os.path.join(
            DOCS_PATH, 'example-bugwarriorrc')
        config.load_config('general', False, False)
