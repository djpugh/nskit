# Contributing to NSKit

We love contributions to NSKit.

## Issues

Please raise issues, queries or discussions [here](https://github.com/djpugh/nskit/issues).

## Contributing to the Codebase

### Prerequisites

* Python 3.8+
* [uv](https://docs.astral.sh/uv/) (package manager)
* [Task](https://taskfile.dev/) (task runner)
* git

### Setup

```bash
git clone https://github.com/djpugh/nskit.git
cd nskit
task setup
```

This installs dependencies with `uv` and sets up pre-commit hooks.

### Make Changes

```bash
git checkout -b my-branch
# Make your changes...
```

### Run Tests

```bash
task test                    # Run all tests (unit by default)
task test -- unit            # Unit tests only
task test -- functional      # Functional tests only
task test:unit               # Unit tests
task test:integration        # Integration/functional tests
```

### Lint and Format

```bash
task lint                    # Run linter
task format                  # Auto-format code (ruff + isort)
task check                   # Run all checks (pre-commit, security, licences)
```

### Build Docs

```bash
task docs:serve              # Serve docs locally
task docs:build              # Build docs
```

### Build Package

```bash
task build                   # Build distribution package
```

### Commit and Push

Commit your changes, push your branch to GitHub, and create a pull request to the main [nskit repo](https://github.com/djpugh/nskit). Please include clear information in the pull request for review.
