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
    """Precommit install hook."""

    def call(self, recipe_path: Path, context: Dict[str, Any]):  # noqa: U100
        """Run the pre-commit install and install hooks command."""
        with ChDir(recipe_path):
            if Path('.pre-commit-config.yaml').exists():
                logger.info('Installing precommit')
                # Install if pre-commit installed
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pre-commit'])  # nosec B603
                logger.info('Installing hooks')
                with open('.pre-commit-config.yaml') as f:
                    logger.info(f'Precommit Config: {f.read()}')
                # Run
                try:
                    subprocess.check_output([sys.executable, '-m', 'pre_commit', 'install', '--install-hooks'])  # nosec B603
                except subprocess.CalledProcessError as e:
                    logger.error('Error running pre-commit', output=e.output, return_code=e.returncode)
                    raise e from None
                logger.info('Done')
            else:
                logger.info('Precommit config file not detected, skipping.')
