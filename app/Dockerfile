# --------------------------------------------------------------
# Builder stage: install dependencies with uv
# --------------------------------------------------------------
FROM --platform=linux/arm64 python:3.12-slim AS builder

# Install uv
RUN pip install --no-cache-dir uv==0.4.18

WORKDIR /app

# Copy everything hatchling needs to build the package and resolve deps.
COPY pyproject.toml README.md ./
COPY src/ src/

# Create venv and install the package + all runtime dependencies in one shot.
RUN uv venv .venv && \
    uv pip install --python .venv/bin/python .

# --------------------------------------------------------------
# Runtime stage: lean image
# --------------------------------------------------------------
FROM --platform=linux/arm64 python:3.12-slim AS runtime

# Non-root user for security
RUN groupadd --gid 10001 agent && \
    useradd  --uid 10001 --gid agent --no-create-home agent

WORKDIR /app

# Copy the virtualenv from builder.
COPY --from=builder /app/.venv /app/.venv

# Make venv binaries the default Python
ENV PATH="/app/.venv/bin:$PATH"

# AgentCore sends HTTP POST requests to the container.
EXPOSE 8080
CMD ["uvicorn", "os_search_agent.server:app", "--host", "0.0.0.0", "--port", "8080"]
