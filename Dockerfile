# syntax=docker/dockerfile:1
# Generic Dockerfile for nskit-based recipe CLIs

FROM python:3.12-slim-bookworm AS base

LABEL org.opencontainers.image.source="https://github.com/djpugh/nskit"

ARG PROJECT_DIR=/app
ARG SOURCE_FILES_DIRNAME=src
ARG CLI_COMMAND=nskit
ARG RECIPE_NAME=nskit

# Set up uv and other deps first
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates git && rm -rf /var/lib/apt/lists/*
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:$PATH"

# Copy dependency files
WORKDIR ${PROJECT_DIR}
COPY pyproject.toml uv.lock* README.md ${PROJECT_DIR}/

# Install dependencies (not the project itself yet)
RUN --mount=type=secret,id=pypi_username,env=UV_INDEX_USERNAME,required=false \
    --mount=type=secret,id=pypi_password,env=UV_INDEX_PASSWORD,required=false \
    uv sync --frozen --no-install-project --no-dev || uv sync --no-install-project --no-dev

###### Test image stage ######
FROM base AS test

RUN --mount=type=secret,id=pypi_username,env=UV_INDEX_USERNAME,required=false \
    --mount=type=secret,id=pypi_password,env=UV_INDEX_PASSWORD,required=false \
    uv sync --frozen --no-install-project || uv sync --no-install-project

COPY tests ${PROJECT_DIR}/tests
COPY ${SOURCE_FILES_DIRNAME}/ ${PROJECT_DIR}/${SOURCE_FILES_DIRNAME}

RUN --mount=type=secret,id=pypi_username,env=UV_INDEX_USERNAME,required=false \
    --mount=type=secret,id=pypi_password,env=UV_INDEX_PASSWORD,required=false \
    --mount=type=bind,src=.git,dst=${PROJECT_DIR}/.git \
    uv sync --frozen || uv sync

###### Runtime image stage ######
FROM base AS runtime

RUN mkdir -p ${PROJECT_DIR}/input ${PROJECT_DIR}/output

COPY ${SOURCE_FILES_DIRNAME}/ ${PROJECT_DIR}/${SOURCE_FILES_DIRNAME}

RUN --mount=type=secret,id=pypi_username,env=UV_INDEX_USERNAME,required=false \
    --mount=type=secret,id=pypi_password,env=UV_INDEX_PASSWORD,required=false \
    --mount=type=bind,src=.git,dst=${PROJECT_DIR}/.git \
    uv sync --frozen --no-dev || uv sync --no-dev

ENV CLI_COMMAND=${CLI_COMMAND}
LABEL nskit.recipe="true"
LABEL nskit.recipe.name="${RECIPE_NAME}"
ENTRYPOINT ["sh", "-c", "uv run --no-sync $CLI_COMMAND \"$@\"", "--"]
