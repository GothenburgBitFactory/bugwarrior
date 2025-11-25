import subprocess
import unittest


class TestGeneral(unittest.TestCase):
    def test_ruff_check(self):
        subprocess.run(['ruff', 'check'], check=True)

    def test_ruff_format(self):
        subprocess.run(['ruff', 'format', '--check'], check=True)
