"""Nox configuration — test sessions only."""
from pathlib import Path
from platform import platform, python_version

import nox

nox.options.default_venv_backend = "uv"


@nox.session(reuse_venv=True, tags=["test"], python=["3.9", "3.10", "3.11", "3.12", "3.13"])
def test(session):
    """Run tests."""
    Path("reports").mkdir(exist_ok=True)
    if session.posargs:
        test_folder = [f"tests/{u}" for u in session.posargs]
    else:
        test_folder = ["tests/unit"]
    session.run("uv", "sync", external=True)
    for folder in test_folder:
        env_name = f"py-{python_version()}-os-{platform()}"
        session.run(
            "pytest",
            "--log-level=WARNING",
            "--cov=nskit",
            "--cov-report",
            "xml:reports/coverage.xml",
            "--cov-report",
            "html:reports/htmlcov",
            "--junitxml",
            f"reports/{env_name}-test.xml",
            "-rs",
            folder,
        )
