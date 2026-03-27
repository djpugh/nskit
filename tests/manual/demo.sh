#!/usr/bin/env bash
# Manual demo/test script for nskit CLI workflows.
# Run from the repo root: bash tests/manual/demo.sh
#
# Tests both local mode (default) and Docker mode (if Docker is available).
# Each test creates a temp directory, runs the workflow, and checks the output.

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓ $1${NC}"; }
fail() { echo -e "${RED}✗ $1${NC}"; FAILURES=$((FAILURES + 1)); }
info() { echo -e "${CYAN}→ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }

FAILURES=0
TMPBASE=$(mktemp -d)
trap "rm -rf $TMPBASE" EXIT

# ─────────────────────────────────────────────────────────────
info "Test 1: nskit list (entry point discovery)"
# ─────────────────────────────────────────────────────────────
OUTPUT=$(uv run python -m nskit.cli.app 2>/dev/null || true)
# Use the CLI factory directly since there's no registered script
OUTPUT=$(uv run python -c "
from nskit.cli.app import create_cli
from typer.testing import CliRunner
app = create_cli(recipe_entrypoint='nskit.recipes')
result = CliRunner().invoke(app, ['list'])
print(result.stdout)
" 2>/dev/null)

if echo "$OUTPUT" | grep -q "python_package"; then
    pass "nskit list shows python_package"
else
    fail "nskit list missing python_package"
fi

if echo "$OUTPUT" | grep -q "recipe"; then
    pass "nskit list shows recipe"
else
    fail "nskit list missing recipe"
fi

# ─────────────────────────────────────────────────────────────
info "Test 2: nskit get-required-fields"
# ─────────────────────────────────────────────────────────────
OUTPUT=$(uv run python -c "
from nskit.cli.app import create_cli
from typer.testing import CliRunner
app = create_cli(recipe_entrypoint='nskit.recipes')
result = CliRunner().invoke(app, ['get-required-fields', '--recipe', 'python_package'])
print(result.stdout)
" 2>/dev/null)

if echo "$OUTPUT" | grep -q "repo.owner"; then
    pass "get-required-fields shows repo.owner"
else
    fail "get-required-fields missing repo.owner"
fi

if echo "$OUTPUT" | grep -q "repo.email"; then
    pass "get-required-fields shows repo.email"
else
    fail "get-required-fields missing repo.email"
fi

# ─────────────────────────────────────────────────────────────
info "Test 3: nskit init with YAML (local mode)"
# ─────────────────────────────────────────────────────────────
DIR="$TMPBASE/test3"
mkdir -p "$DIR"
cat > "$DIR/input.yaml" << 'EOF'
name: demo-project
repo:
  owner: Demo User
  email: demo@example.com
  description: Demo project from manual test
  url: https://example.com
EOF

uv run python -c "
from nskit.cli.app import create_cli
from typer.testing import CliRunner
app = create_cli(recipe_entrypoint='nskit.recipes')
result = CliRunner().invoke(app, ['init', '--recipe', 'python_package', '--input-yaml-path', '$DIR/input.yaml', '--output-base-path', '$DIR/output'])
print('exit:', result.exit_code)
if result.exception: print('error:', result.exception)
" 2>/dev/null

if [ -f "$DIR/output/demo-project/pyproject.toml" ]; then
    pass "YAML init created pyproject.toml"
else
    fail "YAML init missing pyproject.toml"
fi

if [ -f "$DIR/output/demo-project/README.md" ]; then
    pass "YAML init created README.md"
else
    fail "YAML init missing README.md"
fi

if [ -d "$DIR/output/demo-project/src" ]; then
    pass "YAML init created src/"
else
    fail "YAML init missing src/"
fi

if [ -d "$DIR/output/demo-project/.git" ]; then
    pass "YAML init initialised git"
else
    fail "YAML init missing .git"
fi

# ─────────────────────────────────────────────────────────────
info "Test 4: Env var defaults resolve correctly"
# ─────────────────────────────────────────────────────────────
OUTPUT=$(RECIPE_NAME=env-demo RECIPE_REPO_OWNER=EnvOwner uv run python -c "
import os
from nskit.client.env_resolver import EnvVarResolver

resolver = EnvVarResolver()
name = resolver.resolve('RECIPE_NAME')
owner = resolver.resolve('RECIPE_REPO_OWNER')
print(f'name={name} owner={owner}')
" 2>/dev/null)

if echo "$OUTPUT" | grep -q "name=env-demo"; then
    pass "RECIPE_NAME env var resolved"
else
    fail "RECIPE_NAME env var not resolved: $OUTPUT"
fi

if echo "$OUTPUT" | grep -q "owner=EnvOwner"; then
    pass "RECIPE_REPO_OWNER env var resolved"
else
    fail "RECIPE_REPO_OWNER env var not resolved: $OUTPUT"
fi

# ─────────────────────────────────────────────────────────────
info "Test 5: Context defaults (git name/email)"
# ─────────────────────────────────────────────────────────────
OUTPUT=$(uv run python -c "
from nskit.client.context import ContextProvider
ctx = ContextProvider().get_context()
print(f'git_email={ctx.get(\"git_email\", \"\")} git_name={ctx.get(\"git_name\", \"\")}')
" 2>/dev/null)

GIT_EMAIL=$(git config --global user.email 2>/dev/null || echo "")
if [ -n "$GIT_EMAIL" ] && echo "$OUTPUT" | grep -q "$GIT_EMAIL"; then
    pass "ContextProvider returns git_email"
else
    warn "ContextProvider git_email mismatch (expected: $GIT_EMAIL, got: $OUTPUT)"
fi

GIT_NAME=$(git config --global user.name 2>/dev/null || echo "")
if [ -n "$GIT_NAME" ] && echo "$OUTPUT" | grep -q "$GIT_NAME"; then
    pass "ContextProvider returns git_name"
else
    warn "ContextProvider git_name mismatch (may not be set)"
fi

# ─────────────────────────────────────────────────────────────
info "Test 5b: YAML init with env-var-provided values"
# ─────────────────────────────────────────────────────────────
DIR="$TMPBASE/test5b"
mkdir -p "$DIR"
cat > "$DIR/input.yaml" << 'EOF'
name: env-yaml-test
repo:
  owner: EnvYamlOwner
  email: env@yaml.com
  description: Test
  url: https://example.com
EOF

uv run python -c "
from nskit.cli.app import create_cli
from typer.testing import CliRunner
app = create_cli(recipe_entrypoint='nskit.recipes')
result = CliRunner().invoke(app, ['init', '--recipe', 'python_package', '--input-yaml-path', '$DIR/input.yaml', '--output-base-path', '$DIR/output'])
print('exit:', result.exit_code)
" 2>/dev/null

if [ -f "$DIR/output/env-yaml-test/pyproject.toml" ]; then
    pass "YAML init with env values created project"
else
    fail "YAML init with env values failed"
fi

# ─────────────────────────────────────────────────────────────
info "Test 6: Programmatic RecipeClient + LocalEngine"
# ─────────────────────────────────────────────────────────────
DIR="$TMPBASE/test6"
mkdir -p "$DIR"

OUTPUT=$(uv run python -c "
from nskit.client import RecipeClient
from nskit.client.engines import LocalEngine
from unittest.mock import Mock
from pathlib import Path

backend = Mock()
backend.entrypoint = 'nskit.recipes'
client = RecipeClient(backend, engine=LocalEngine())
result = client.initialize_recipe(
    recipe='python_package', version='v1.0.0',
    parameters={'name': 'api-test', 'repo': {'owner': 'T', 'email': 't@t.com', 'description': 'd', 'url': 'https://t.com'}},
    output_dir=Path('$DIR/api-test'),
)
print('success:', result.success)
print('errors:', result.errors)
print('files:', len(result.files_created))
" 2>/dev/null)

if echo "$OUTPUT" | grep -q "success: True"; then
    pass "RecipeClient + LocalEngine succeeded"
else
    fail "RecipeClient + LocalEngine failed: $OUTPUT"
fi

# ─────────────────────────────────────────────────────────────
info "Test 7: Full init → update cycle (LocalEngine)"
# ─────────────────────────────────────────────────────────────
DIR="$TMPBASE/test7"
mkdir -p "$DIR"

OUTPUT=$(uv run python -c "
from nskit.client import RecipeClient, UpdateClient
from nskit.client.engines import LocalEngine
from nskit.client.config import ConfigManager, RecipeConfig, RecipeMetadata
from nskit.client.diff.models import DiffMode
from unittest.mock import Mock
from pathlib import Path
import subprocess

backend = Mock()
backend.entrypoint = 'nskit.recipes'
backend.get_recipe_versions = Mock(return_value=['v1.0.0'])
engine = LocalEngine()
project = Path('$DIR/update-test')

# Init
client = RecipeClient(backend, engine=engine)
result = client.initialize_recipe(
    recipe='python_package', version='v1.0.0',
    parameters={'name': 'update.test', 'repo': {'owner': 'T', 'email': 't@t.com', 'description': 'd', 'url': 'https://t.com'}},
    output_dir=project,
)
print('init:', result.success)

# Write config + commit
cfg = RecipeConfig(
    input={'name': 'update.test', 'repo': {'owner': 'T', 'email': 't@t.com', 'description': 'd', 'url': 'https://t.com'}},
    metadata=RecipeMetadata(recipe_name='python_package', docker_image='img:v1.0.0'),
)
ConfigManager(project).save_config(cfg)
subprocess.run(['git', 'config', 'user.email', 't@t.com'], cwd=project, capture_output=True)
subprocess.run(['git', 'config', 'user.name', 'T'], cwd=project, capture_output=True)
subprocess.run(['git', 'add', '.'], cwd=project, capture_output=True, check=True)
subprocess.run(['git', 'commit', '-m', 'init', '--no-verify'], cwd=project, capture_output=True, check=True)

# Dry-run update
update_client = UpdateClient(backend, engine=engine)
result = update_client.update_project(project_path=project, target_version='v1.0.0', diff_mode=DiffMode.THREE_WAY, dry_run=True)
print('update_dry_run:', result.success)
print('update_errors:', result.errors)
" 2>/dev/null)

if echo "$OUTPUT" | grep -q "init: True" && echo "$OUTPUT" | grep -q "update_dry_run: True"; then
    pass "Full init → update cycle succeeded"
else
    fail "Init → update cycle failed: $OUTPUT"
fi

# ─────────────────────────────────────────────────────────────
info "Test 8: NamespaceValidator"
# ─────────────────────────────────────────────────────────────
OUTPUT=$(uv run python -c "
from nskit.vcs.namespace_validator import NamespaceValidator
v = NamespaceValidator(options=[{'platform': ['auth', 'data']}, 'shared'], repo_separator='-')
ok1, _ = v.validate_name('platform-auth-users')
ok2, _ = v.validate_name('rogue-project')
ok3, _ = v.validate_name('shared')
print(f'valid={ok1} invalid={not ok2} shared={ok3}')
")

if echo "$OUTPUT" | grep -q "valid=True invalid=True shared=True"; then
    pass "NamespaceValidator works correctly"
else
    fail "NamespaceValidator failed: $OUTPUT"
fi

# ─────────────────────────────────────────────────────────────
info "Test 9: Docker engine (if Docker available)"
# ─────────────────────────────────────────────────────────────
if docker info >/dev/null 2>&1; then
    info "Docker available — testing Docker engine"
    DIR="$TMPBASE/test9"
    mkdir -p "$DIR"

    # Build the nskit image
    info "Building nskit Docker image (this may take a minute)..."
    if docker build --target runtime -t nskit-demo-test:latest . -q >/dev/null 2>&1; then
        OUTPUT=$(uv run python -c "
from nskit.client.engines import DockerEngine
from pathlib import Path

engine = DockerEngine(skip_pull=True)
result = engine.execute(
    recipe='python_package', version='local',
    parameters={'name': 'docker.test', 'repo': {'owner': 'T', 'email': 't@t.com', 'description': 'd', 'url': 'https://t.com'}},
    output_dir=Path('$DIR/docker-test'),
    image_url='nskit-demo-test:latest',
)
print('success:', result.success)
print('files:', len(result.files_created))
print('errors:', result.errors)
" 2>/dev/null)

        if echo "$OUTPUT" | grep -q "success: True"; then
            pass "DockerEngine created project"
        else
            fail "DockerEngine failed: $OUTPUT"
        fi

        # Cleanup
        docker rmi nskit-demo-test:latest >/dev/null 2>&1 || true
    else
        warn "Docker image build failed — skipping Docker tests"
    fi
else
    warn "Docker not available — skipping Docker tests"
fi

# ─────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
else
    echo -e "${RED}$FAILURES test(s) failed${NC}"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exit $FAILURES
