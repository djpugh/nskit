"""Unit tests for EnvVarResolver."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from nskit.client.env_resolver import EnvVarResolver


class TestEnvVarResolver(unittest.TestCase):
    """Tests for EnvVarResolver prefix allowlist and resolution."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.resolver = EnvVarResolver()

    def test_default_prefixes(self) -> None:
        """Default prefixes include NSKIT_ and RECIPE_."""
        self.assertEqual(self.resolver.allowed_prefixes, ["NSKIT_", "RECIPE_"])

    def test_custom_prefixes(self) -> None:
        """Custom prefixes override defaults."""
        r = EnvVarResolver(allowed_prefixes=["MY_"])
        self.assertEqual(r.allowed_prefixes, ["MY_"])

    @patch.dict(os.environ, {"NSKIT_PROJECT": "myproject"})
    def test_resolve_allowed_prefix(self) -> None:
        """Resolves env var matching an allowed prefix."""
        self.assertEqual(self.resolver.resolve("NSKIT_PROJECT"), "myproject")

    @patch.dict(os.environ, {"SECRET_KEY": "hunter2"})
    def test_resolve_disallowed_prefix(self) -> None:
        """Returns None for env var not matching any allowed prefix."""
        self.assertIsNone(self.resolver.resolve("SECRET_KEY"))

    def test_resolve_missing_var(self) -> None:
        """Returns None when the env var is not set."""
        self.assertIsNone(self.resolver.resolve("NSKIT_NONEXISTENT_VAR_XYZ"))

    def test_is_allowed_true(self) -> None:
        """_is_allowed returns True for matching prefix."""
        self.assertTrue(self.resolver._is_allowed("RECIPE_NAME"))

    def test_is_allowed_false(self) -> None:
        """_is_allowed returns False for non-matching prefix."""
        self.assertFalse(self.resolver._is_allowed("HOME"))


if __name__ == "__main__":
    unittest.main()
