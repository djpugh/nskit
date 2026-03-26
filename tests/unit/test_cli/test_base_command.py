"""Tests for BaseCommand error handling."""

import unittest

import typer

from nskit.cli.base_command import BaseCommand
from nskit.client.exceptions import GitStatusError, InitError, InvalidConfigError, UpdateError


class _SuccessCommand(BaseCommand):
    def execute(self, *args, **kwargs):
        return "ok"


class _InitErrorCommand(BaseCommand):
    def execute(self, *args, **kwargs):
        raise InitError("init failed")


class _UpdateErrorCommand(BaseCommand):
    def execute(self, *args, **kwargs):
        raise UpdateError("update failed")


class _GitErrorCommand(BaseCommand):
    def execute(self, *args, **kwargs):
        raise GitStatusError("dirty tree")


class _ConfigErrorCommand(BaseCommand):
    def execute(self, *args, **kwargs):
        raise InvalidConfigError(["bad config"])


class _UnexpectedErrorCommand(BaseCommand):
    def execute(self, *args, **kwargs):
        raise RuntimeError("boom")


class TestBaseCommand(unittest.TestCase):
    """Tests for BaseCommand."""

    def test_successful_execution(self) -> None:
        """run() returns the result of execute()."""
        cmd = _SuccessCommand()
        self.assertEqual(cmd.run(), "ok")

    def test_execute_not_implemented(self) -> None:
        """Base execute() raises NotImplementedError."""
        cmd = BaseCommand()
        with self.assertRaises(NotImplementedError):
            cmd.execute()

    def test_init_error_exits(self) -> None:
        """InitError is caught and converted to typer.Exit."""
        cmd = _InitErrorCommand()
        with self.assertRaises(typer.Exit) as ctx:
            cmd.run()
        self.assertEqual(ctx.exception.exit_code, 1)

    def test_update_error_exits(self) -> None:
        """UpdateError is caught and converted to typer.Exit."""
        cmd = _UpdateErrorCommand()
        with self.assertRaises(typer.Exit) as ctx:
            cmd.run()
        self.assertEqual(ctx.exception.exit_code, 1)

    def test_git_error_exits(self) -> None:
        """GitStatusError is caught and converted to typer.Exit."""
        cmd = _GitErrorCommand()
        with self.assertRaises(typer.Exit) as ctx:
            cmd.run()
        self.assertEqual(ctx.exception.exit_code, 1)

    def test_config_error_exits(self) -> None:
        """InvalidConfigError is caught and converted to typer.Exit."""
        cmd = _ConfigErrorCommand()
        with self.assertRaises(typer.Exit) as ctx:
            cmd.run()
        self.assertEqual(ctx.exception.exit_code, 1)

    def test_unexpected_error_exits(self) -> None:
        """Unexpected exceptions are caught and converted to typer.Exit."""
        cmd = _UnexpectedErrorCommand()
        with self.assertRaises(typer.Exit) as ctx:
            cmd.run()
        self.assertEqual(ctx.exception.exit_code, 1)
