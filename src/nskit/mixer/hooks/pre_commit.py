"""Precommit hooks.

Contains post creation precommit install hooks.
"""
from pathlib import Path
import subprocess  # nosec B404
import sys
from typing import Any, Dict

from nskit._logging import logger_factory
from nskit.common.contextmanagers import ChDir
from nskit.mixer.components import Hook


logger = logger_factory.get(__name__)


class PrecommitInstall(Hook):

    def call(self, recipe_name: str, recipe_path: Path, context: Dict[str, Any]):
        """Run the pre-commit install and install hooks command."""
        with ChDir(recipe_path):
            if Path('.pre-commit-config.yaml').exists():
                logger.info('Installing precommit')
                # Install if pre-commit installed
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pre-commit'])  # nosec B603
                logger.info('Installing hooks')
                # Run
                subprocess.check_call([sys.executable, '-m', 'pre_commit', 'install', '--install-hooks'])  # nosec B603
                logger.info('Done')
            else:
                logger.info('Precommit config file not detected, skipping.')
