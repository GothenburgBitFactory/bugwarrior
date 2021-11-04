import unittest

from bugwarrior.config import secrets


class TestOracleEval(unittest.TestCase):

    def test_echo(self):
        self.assertEqual(secrets.oracle_eval("echo fööbår"), "fööbår")
