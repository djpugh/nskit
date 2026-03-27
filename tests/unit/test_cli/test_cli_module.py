"""Tests for CLI module — resolve functions and logging configuration."""

import logging
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from nskit.cli import _configure_cli_logging, _resolve_backend, _resolve_engine


class TestResolveBackend(unittest.TestCase):
    """Tests for _resolve_backend."""

    def test_none_returns_none(self):
        """None input returns None."""
        self.assertIsNone(_resolve_backend(None))

    def test_docker_local(self):
        """docker-local returns DockerLocalBackend."""
        from nskit.client.backends import DockerLocalBackend

        result = _resolve_backend("docker-local")
        self.assertIsInstance(result, DockerLocalBackend)

    def test_local(self):
        """local returns LocalBackend."""
        from nskit.client.backends import LocalBackend

        result = _resolve_backend("local")
        self.assertIsInstance(result, LocalBackend)

    def test_config_file(self, tmp_path=None):
        """Config file path returns configured backend."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("type: local\npath: /tmp\n")
            f.flush()
            try:
                result = _resolve_backend(f.name)
                from nskit.client.backends import LocalBackend

                self.assertIsInstance(result, LocalBackend)
            finally:
                os.unlink(f.name)

    def test_unknown_raises(self):
        """Unknown backend raises SystemExit."""
        with self.assertRaises(SystemExit):
            _resolve_backend("nonexistent")


class TestResolveEngine(unittest.TestCase):
    """Tests for _resolve_engine."""

    def test_none_returns_none(self):
        """None input returns None."""
        self.assertIsNone(_resolve_engine(None))

    def test_docker(self):
        """docker returns DockerEngine."""
        from nskit.client.engines import DockerEngine

        result = _resolve_engine("docker")
        self.assertIsInstance(result, DockerEngine)

    def test_local(self):
        """local returns LocalEngine."""
        from nskit.client.engines import LocalEngine

        result = _resolve_engine("local")
        self.assertIsInstance(result, LocalEngine)

    def test_unknown_raises(self):
        """Unknown engine raises SystemExit."""
        with self.assertRaises(SystemExit):
            _resolve_engine("nonexistent")


class TestConfigureCliLogging(unittest.TestCase):
    """Tests for _configure_cli_logging."""

    def test_sets_env_defaults(self):
        """Sets LOG_JSON and LOGLEVEL env vars."""
        env = os.environ.copy()
        env.pop("LOG_JSON", None)
        env.pop("LOGLEVEL", None)
        with patch.dict(os.environ, env, clear=True):
            _configure_cli_logging()
            self.assertEqual(os.environ["LOG_JSON"], "false")
            self.assertEqual(os.environ["LOGLEVEL"], "WARNING")

    def test_respects_existing_env(self):
        """Does not override existing env vars."""
        with patch.dict(os.environ, {"LOG_JSON": "true", "LOGLEVEL": "DEBUG"}):
            _configure_cli_logging()
            self.assertEqual(os.environ["LOG_JSON"], "true")
            self.assertEqual(os.environ["LOGLEVEL"], "DEBUG")

    def test_reconfigures_nskit_loggers(self):
        """Reconfigures existing nskit loggers to WARNING."""
        logger = logging.getLogger("nskit.test.cli_logging")
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LOGLEVEL", None)
            _configure_cli_logging()

        self.assertEqual(logger.level, logging.WARNING)
        self.assertEqual(handler.level, logging.WARNING)
        logger.removeHandler(handler)


if __name__ == "__main__":
    unittest.main()
