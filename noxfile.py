import os
from pathlib import Path
import tomllib

import nox

ON_CI = any([os.environ.get('ON_CI', '0') == '1'])
STRICT_TYPES = False


def install_dependencies(session, required=True, optional=[], pyproject_toml='pyproject.toml'):
    with open(pyproject_toml, 'rb') as f:
        config = tomllib.load(f)
    dependencies = []
    if required:
        dependencies += config['project']['dependencies']
    for option in optional:
        dependencies += config['project']['optional-dependencies'].get(option, [])
    session.install(*dependencies)


@nox.session(name='pre-commit', python=None if ON_CI else False, reuse_venv=True, tags=['lint'])
def pre_commit(session):
    if ON_CI:
        session.install('pre-commit')
    session.run('pre-commit', 'run', '--all-files', env={'SKIP': 'lint,types,security'})


@nox.session(reuse_venv=True, tags=['lint'])
def lint(session):
    install_dependencies(session, required=False, optional=['dev','dev-lint'])
    session.run('flake8', 'src/')


@nox.session(reuse_venv=True, tags=['lint'])
def security(session):
    install_dependencies(session, required=False, optional=['dev', 'dev-security'])
    Path('reports').mkdir(exist_ok=True)
    session.run('pipenv', 'lock')
    session.run('pipenv', 'check')
    session.run('bandit', '-r', 'src')
    session.run('bandit', '-r', 'src', '--format', 'xml', '--output', 'reports/security-results.xml')


@nox.session(python=None if ON_CI else False, tags=['lint'])
def types(session):
    Path('reports').mkdir(exist_ok=True)
    if ON_CI:
        session.install('.[dev,dev-types]')
    args = ('mypy', 'src/', '--linecoverage-report', 'reports', '--junit-xml', 'reports/mypy.xml', '--cobertura-xml-report', 'reports')
    if (STRICT_TYPES and (not session.posargs or 'warn-only' not in session.posargs)) or (not STRICT_TYPES and session.posargs and 'strict' in session.posargs):
        # set default behaviour using the STRICT_TYPES variable, and then use either strict or warn-only in the command line args to turn off
        session.run(*args)
    else:
        try:
            session.run(*args)
        except nox.command.CommandFailed:
            session.warn('mypy failed, but warn-only set')



@nox.session(reuse_venv=True, tags=['test'])
def test(session):
    Path('reports').mkdir(exist_ok=True)
    if session.posargs:
        test_folder = [f'tests/{u}' for u in session.posargs]
    else:
        test_folder = ['tests']
    session.install('.[dev,dev-test]')
    for folder in test_folder:
        args = []
        args.append('-rs')
        args.append(folder)
        session.run('pytest', '--log-level=WARNING', '--cov=nskit', '--cov-report', 'xml:reports/coverage.xml', *args)


@nox.session(reuse_venv=True, tags=['docs'])
def docs(session):
    session.install('.[dev,dev-docs]')
    session.run('pipenv', 'check')



@nox.session(reuse_venv=True, tags=['build'])
def build(session):
    install_dependencies(session, required=False, optional=['dev','dev-build'])
    session.run('python', '-m', 'build')
