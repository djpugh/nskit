# syntax=docker/dockerfile:1
# Generic Dockerfile for nskit-based recipe CLIs
# 
# Build args:
#   - RECIPE_ENTRYPOINT: Python entrypoint for recipe discovery (e.g., "nskit.recipes")
#   - CLI_COMMAND: Command name for the CLI (e.g., "nskit")
#   - PYPI_INDEX_URL: Optional custom PyPI index URL
#   - PYPI_INDEX_USERNAME_SECRET: Secret ID for PyPI username
#   - PYPI_INDEX_PASSWORD_SECRET: Secret ID for PyPI password

FROM python:3.12-slim-bookworm AS base

LABEL org.opencontainers.image.source="https://github.com/djpugh/nskit"

ARG PROJECT_DIR=/app
ARG SOURCE_FILES_DIRNAME=src
ARG CLI_COMMAND=nskit

# Set up uv and other deps first
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates git
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:$PATH"

# Copy dependency files
WORKDIR ${PROJECT_DIR}
COPY pyproject.toml uv.lock* README.md ${PROJECT_DIR}/

# Use secret from env vars for dependency installation (if provided)
RUN --mount=type=secret,id=pypi_username,env=UV_INDEX_USERNAME,required=false \
    --mount=type=secret,id=pypi_password,env=UV_INDEX_PASSWORD,required=false \
    uv sync --frozen --no-install-project --no-dev || uv sync --no-install-project --no-dev

###### Test image stage ######
FROM base AS test

# Install the test dependencies
RUN --mount=type=secret,id=pypi_username,env=UV_INDEX_USERNAME,required=false \
    --mount=type=secret,id=pypi_password,env=UV_INDEX_PASSWORD,required=false \
    uv sync --frozen --no-install-project || uv sync --no-install-project

COPY tests ${PROJECT_DIR}/tests

# Install the project itself
COPY ${SOURCE_FILES_DIRNAME}/ ${PROJECT_DIR}/${SOURCE_FILES_DIRNAME}
RUN --mount=type=secret,id=pypi_username,env=UV_INDEX_USERNAME,required=false \
    --mount=type=secret,id=pypi_password,env=UV_INDEX_PASSWORD,required=false \
    --mount=type=bind,src=.git,dst=${PROJECT_DIR}/.git,required=false \
    uv build && uv sync --frozen || uv sync

###### Runtime image stage ######
FROM base AS runtime

# Create input and output directories
RUN mkdir -p ${PROJECT_DIR}/input ${PROJECT_DIR}/output

# Install the project itself
COPY ${SOURCE_FILES_DIRNAME}/ ${PROJECT_DIR}/${SOURCE_FILES_DIRNAME}
RUN --mount=type=secret,id=pypi_username,env=UV_INDEX_USERNAME,required=false \
    --mount=type=secret,id=pypi_password,env=UV_INDEX_PASSWORD,required=false \
    --mount=type=bind,src=.git,dst=${PROJECT_DIR}/.git,required=false \
    uv sync --frozen --no-dev || uv sync --no-dev

ENTRYPOINT [ "uv", "run", "--no-sync", "${CLI_COMMAND}" ]
