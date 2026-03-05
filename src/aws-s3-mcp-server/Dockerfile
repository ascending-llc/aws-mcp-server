# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM public.ecr.aws/docker/library/python:3.13.5-alpine3.21@sha256:c9a09c45a4bcc618c7f7128585b8dd0d41d0c31a8a107db4c8255ffe0b69375d AS uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_PREFERENCE=only-system \
    UV_FROZEN=true \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apk update && \
    apk add --no-cache --virtual .build-deps \
    build-base \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    cargo

# Copy lockfiles first for layer caching
COPY pyproject.toml uv.lock uv-requirements.txt ./

# Bootstrap uv with pinned hashes, then install project dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    pip install --require-hashes --requirement uv-requirements.txt --no-cache-dir && \
    uv sync --python 3.13 --frozen --no-install-project --no-dev --no-editable

# Copy source and install the package itself
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --python 3.13 --frozen --no-dev --no-editable

RUN mkdir -p /root/.local

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM public.ecr.aws/docker/library/python:3.13.5-alpine3.21@sha256:c9a09c45a4bcc618c7f7128585b8dd0d41d0c31a8a107db4c8255ffe0b69375d

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    MCP_PORT=3334 \
    VIRTUAL_ENV="/app/.venv"

EXPOSE 3334

RUN apk update && \
    apk add --no-cache ca-certificates curl && \
    update-ca-certificates && \
    addgroup -S app && \
    adduser -S app -G app -h /app

COPY --from=uv --chown=app:app /app /app
COPY --chown=app:app docker-healthcheck.sh /usr/local/bin/docker-healthcheck.sh
RUN chmod +x /usr/local/bin/docker-healthcheck.sh

USER app

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD ["/usr/local/bin/docker-healthcheck.sh"]

CMD ["awslabs.aws-s3-mcp-server"]
