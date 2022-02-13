import subprocess
import tempfile
import unittest


class DocsTest(unittest.TestCase):
    def test_docs_build_without_warning(self):
        with tempfile.TemporaryDirectory() as buildDir:
            subprocess.run(
                ['sphinx-build', '-n', '-W', 'bugwarrior/docs', buildDir],
                check=True)
