import unittest
from unittest.mock import MagicMock, patch

import keyring.errors
import pytest

from bugwarrior.config import secrets


class TestOracleEval(unittest.TestCase):
    def test_echo(self):
        assert secrets.oracle_eval("echo fööbår") == "fööbår"


class TestGetServicePassword(unittest.TestCase):
    """Tests for get_service_password, covering every oracle code path."""

    SERVICE = "myservice"
    USERNAME = "username"

    def _call(self, oracle):
        return secrets.get_service_password(self.SERVICE, self.USERNAME, oracle=oracle)

    def _mock_keyring(self, password=None, locked=False):
        """Return a mock keyring module.

        If "locked" is True, get_password raises KeyringLocked.
        Otherwise it returns the given password.
        """
        mock = MagicMock()
        if locked:
            mock.get_password.side_effect = keyring.errors.KeyringLocked()
        else:
            mock.get_password.return_value = password
        mock.errors = keyring.errors
        return mock

    def test_eval_oracle_returns_command_output(self):
        with patch.object(secrets, "oracle_eval", return_value="s3cr3t") as mock_eval:
            result = self._call(oracle="@oracle:eval:echo s3cr3t")
        mock_eval.assert_called_once_with("echo s3cr3t")
        assert result == "s3cr3t"

    def test_ask_password_interactive_prompts_user(self):
        with (
            patch("sys.stdin") as mock_stdin,
            patch("getpass.getpass", return_value="typed") as mock_getpass,
        ):
            mock_stdin.isatty.return_value = True
            result = self._call(oracle="@oracle:ask_password")
        mock_getpass.assert_called_once()
        assert result == "typed"

    def test_ask_password_non_interactive_exits(self):
        with patch("sys.stdin") as mock_stdin, patch("getpass.getpass") as mock_getpass:
            mock_stdin.isatty.return_value = False
            with pytest.raises(SystemExit):
                self._call(oracle="@oracle:ask_password")
        mock_getpass.assert_not_called()

    def test_keyring_has_password_returns_it(self):
        mock = self._mock_keyring(password="stored")
        with patch.object(secrets, "get_keyring", return_value=mock):
            result = self._call(oracle="@oracle:use_keyring")
        mock.get_password.assert_called_once_with(self.SERVICE, self.USERNAME)
        assert result == "stored"

    def test_default_oracle_also_uses_keyring(self):
        """Passing oracle=None should behave identically to @oracle:use_keyring."""
        mock = self._mock_keyring(password="stored")
        with patch.object(secrets, "get_keyring", return_value=mock):
            result = self._call(oracle=None)
        assert result == "stored"

    def test_keyring_locked_exits(self):
        """When the keyring is locked and the unlock dialog is dismissed,
        keyring raises KeyringLocked. bugwarrior should exit fatally."""
        mock = self._mock_keyring(locked=True)
        with patch.object(secrets, "get_keyring", return_value=mock):
            with pytest.raises(SystemExit):
                self._call(oracle="@oracle:use_keyring")

    def test_keyring_empty_interactive_prompts_and_stores(self):
        """When keyring has no password and stdin is a tty, the user is prompted
        and the password is saved back to the keyring."""
        mock = self._mock_keyring(password=None)
        with (
            patch.object(secrets, "get_keyring", return_value=mock),
            patch("sys.stdin") as mock_stdin,
            patch("getpass.getpass", return_value="newpass"),
        ):
            mock_stdin.isatty.return_value = True
            result = self._call(oracle="@oracle:use_keyring")
        assert result == "newpass"
        mock.set_password.assert_called_once_with(
            self.SERVICE, self.USERNAME, "newpass"
        )

    def test_keyring_empty_non_interactive_exits(self):
        """When keyring has no password and stdin is not a tty, exit fatally."""
        mock = self._mock_keyring(password=None)
        with (
            patch.object(secrets, "get_keyring", return_value=mock),
            patch("sys.stdin") as mock_stdin,
            patch("getpass.getpass") as mock_getpass,
        ):
            mock_stdin.isatty.return_value = False
            with pytest.raises(SystemExit):
                self._call(oracle="@oracle:use_keyring")
        mock_getpass.assert_not_called()

    def test_unknown_oracle_exits(self):
        with pytest.raises(SystemExit):
            self._call(oracle="@oracle:unknown_strategy")
