# syntax=docker/dockerfile:1

FROM python:3.11-slim-bookworm

ARG GRAPHITI_REF=v0.29.2
ARG GRAPHITI_CORE_VERSION=0.29.2
ARG MCP_SERVER_VERSION=1.0.2
ARG BUILD_DATE
ARG VCS_REF

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh

ENV PATH="/root/.local/bin:${PATH}" \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    MCP_SERVER_HOST="0.0.0.0" \
    PYTHONUNBUFFERED=1

WORKDIR /app/mcp

RUN git clone --depth 1 --branch "${GRAPHITI_REF}" https://github.com/getzep/graphiti.git /tmp/graphiti \
    && cp /tmp/graphiti/mcp_server/pyproject.toml /tmp/graphiti/mcp_server/uv.lock ./ \
    && sed -i '/\[tool\.uv\.sources\]/,/graphiti-core/d' pyproject.toml \
    && sed -i "s/graphiti-core\[falkordb\][>=]\+[0-9]\+\.[0-9]\+\.[0-9]\+/graphiti-core[falkordb]==${GRAPHITI_CORE_VERSION}/" pyproject.toml \
    && rm -f uv.lock \
    && uv lock \
    && uv sync --no-group dev \
    && echo "${GRAPHITI_CORE_VERSION}" > /app/mcp/.graphiti-core-version \
    && cp /tmp/graphiti/mcp_server/main.py ./ \
    && cp -r /tmp/graphiti/mcp_server/src ./src \
    && cp -r /tmp/graphiti/mcp_server/config ./config \
    && rm -rf /tmp/graphiti /root/.cache/uv

RUN mkdir -p /var/log/graphiti

LABEL org.opencontainers.image.title="Graphiti MCP Server" \
      org.opencontainers.image.description="Graphiti MCP server for external Neo4j or FalkorDB" \
      org.opencontainers.image.version="${MCP_SERVER_VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.vendor="repotea" \
      org.opencontainers.image.source="https://github.com/getzep/graphiti" \
      graphiti.core.version="${GRAPHITI_CORE_VERSION}"

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uv", "run", "--no-sync", "main.py"]
