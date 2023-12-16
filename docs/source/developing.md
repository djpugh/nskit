# Contributing to NSKit

We love contributions to NSKit

## Issues

Please raise issues, queries or discussions [here](https://github.com/djpugh/nskit/issues).

## Contributing to the codebase

### Installation and setup

Fork the repository on [Github](https://github.com/djpugh/nskit), and clone your fork to your local machine.

Make sure you have the prerequisites installed (for adding code):
* Python (Versions from 3.8)
* virtualenv or another virtual environment tool
* git

Create and activate a virtual environment.

Install ``nskit``:

```
# Install nskit as an editable install with the dev dependencies
pip install -e ".[dev]"
```

The codebase uses ``pre-commit``, so please use ``pre-commit install`` and ``pre-commit install-hooks`` to make sure the pre-commit hooks are installed correctly.

#### Checkout a branch and make changes

Create a branch to make  your changes in:
```
# Checkout a new branch and make your changes
git checkout -b my-branch
# Make your changes...
```

#### Run tests and linting

``nskit`` uses [``nox``](https://nox.thea.codes/en/stable/) for running tests.
```
# You can either use session tags with the -s flag
nox -s test lint
# There are also sessions: security, types, pre-commit

# or the -t lint and test tags
nox -t lint
# This includes lint, pre-commit, security (bandit and pipenv check), types

nox -t test
```

#### Build docs

If you have edited the docs (or signatures/classes), please check the docs:
```
nox -t docs
```

They will be output to ``build/docs``


#### Commit and push your changes

Commit your changes, push your branch to GitHub, and create a pull request to the main [nskit repo](https://github.com/djpugh/nskit), and please include clear information in the pull request for review.
