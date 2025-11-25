import subprocess
import unittest


class TestGeneral(unittest.TestCase):
    def test_ruff(self):
        subprocess.run(['ruff', 'check'], check=True)
