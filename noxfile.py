"""Nox configuration — test sessions only."""

import os
from pathlib import Path
from platform import platform, python_version

import nox

nox.options.default_venv_backend = "uv"

_PYTHON_VERSIONS = False if os.environ.get("ON_CI") else ["3.9", "3.10", "3.11", "3.12", "3.13"]


@nox.session(reuse_venv=True, tags=["test"], python=_PYTHON_VERSIONS)
def test(session):
    """Run tests."""
    Path("reports").mkdir(exist_ok=True)
    if session.posargs:
        test_folder = [f"tests/{u}" for u in session.posargs]
    else:
        test_folder = ["tests/unit"]
    session.run("uv", "sync", external=True)
    env_name = f"py-{python_version()}-os-{platform()}"
    # Clear any previous coverage data
    session.run("coverage", "erase")
    for folder in test_folder:
        session.run(
            "pytest",
            "--log-level=WARNING",
            "--cov=nskit",
            "--cov-append",
            "--junitxml",
            f"reports/{env_name}-test.xml",
            "-rs",
            folder,
        )
    # Generate combined coverage reports after all test folders
    session.run("coverage", "xml", "-o", "reports/coverage.xml")
    session.run("coverage", "html", "-d", "reports/htmlcov")
