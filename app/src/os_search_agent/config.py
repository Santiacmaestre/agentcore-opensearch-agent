"""config.py -- Environment-variable based configuration with validation.

All env-var reading is centralised here so that the rest of the
codebase never calls ``os.environ`` directly.

Contract with Terraform (env vars injected at container launch):
    AWS_REGION          - AgentCore runtime region
    MODEL_ID            - Bedrock model ID to use for the LLM
    MAX_RESULT_CHARS    - Soft cap for tool output (default 20000)
    MEMORY_ID           - AgentCore Memory resource ID
    MEMORY_ACTOR_ID     - Actor namespace for Memory
    AGENT_LOG_GROUP     - Optional: existing CloudWatch Log Group for agent audit logs
    DEBUG_MODE          - "true" / "1" enables verbose debug output

OpenSearch-specific:
    OPENSEARCH_URL      - Cluster endpoint (e.g. https://search-xxx.us-east-1.es.amazonaws.com)
    OPENSEARCH_USERNAME - Basic auth username (empty for IAM auth)
    OPENSEARCH_PASSWORD - Basic auth password (empty for IAM auth)
    OPENSEARCH_USE_IAM  - "true" to use IAM/SigV4 auth instead of basic auth
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Optional


# -- Model defaults ----------------------------------------------------------

DEFAULT_MODEL_ID = "amazon.nova-premier-v1:0"
FALLBACK_MODEL_ID = "amazon.nova-pro-v1:0"

NOVA_PREMIER_REGIONS = {
    "us-east-1",
    "us-west-2",
    "eu-west-1",
    "ap-northeast-1",
}


def _resolve_default_model(region: str) -> str:
    """Return the best available model for the given runtime region."""
    if region in NOVA_PREMIER_REGIONS:
        return DEFAULT_MODEL_ID
    return FALLBACK_MODEL_ID


# -- Config dataclass ---------------------------------------------------------

@dataclass
class Config:
    """Validated application configuration loaded from environment variables."""

    # -- Required --
    aws_region: str
    model_id: str
    memory_id: str
    memory_actor_id: str
    agent_log_group: str

    # -- OpenSearch --
    opensearch_url: str = ""
    opensearch_username: str = ""
    opensearch_password: str = ""
    opensearch_use_iam: bool = False

    # -- Optional with defaults --
    max_result_chars: int = 20_000
    debug_mode: bool = False

    # -- Runtime-derived (not from env) --
    model_id_override: Optional[str] = field(default=None, repr=False)

    @property
    def effective_model_id(self) -> str:
        """Return CLI override if provided, otherwise env / region-default."""
        return self.model_id_override or self.model_id


def load_config(model_id_override: Optional[str] = None) -> Config:
    """Read and validate all required environment variables.

    Raises ``SystemExit`` with a human-readable message if any required
    variable is missing or invalid.
    """
    errors: list[str] = []

    def _require(name: str) -> str:
        val = os.environ.get(name, "").strip()
        if not val:
            errors.append(f"  * {name} is not set (required)")
        return val

    def _optional(name: str, default: str) -> str:
        return os.environ.get(name, default).strip() or default

    aws_region      = _require("AWS_REGION")
    model_id_raw    = _optional("MODEL_ID", "")
    memory_id       = _require("MEMORY_ID")
    memory_actor_id = _require("MEMORY_ACTOR_ID")
    agent_log_group = _require("AGENT_LOG_GROUP")

    # OpenSearch connection
    opensearch_url      = _require("OPENSEARCH_URL")
    opensearch_username = _optional("OPENSEARCH_USERNAME", "")
    opensearch_password = _optional("OPENSEARCH_PASSWORD", "")
    opensearch_use_iam  = _optional("OPENSEARCH_USE_IAM", "false").lower() in ("1", "true", "yes")

    # MAX_RESULT_CHARS
    max_result_chars_str = _optional("MAX_RESULT_CHARS", "20000")
    try:
        max_result_chars = int(max_result_chars_str)
        if max_result_chars <= 0:
            raise ValueError("must be positive")
    except ValueError:
        errors.append(f"  * MAX_RESULT_CHARS='{max_result_chars_str}' is not a positive integer")
        max_result_chars = 20_000

    debug_mode = _optional("DEBUG_MODE", "false").lower() in ("1", "true", "yes")

    if errors:
        print("Configuration errors -- fix the following env vars and restart:\n", file=sys.stderr)
        print("\n".join(errors), file=sys.stderr)
        sys.exit(1)

    # Resolve model: env var -> region default
    if not model_id_raw:
        model_id_raw = _resolve_default_model(aws_region)

    return Config(
        aws_region=aws_region,
        model_id=model_id_raw,
        memory_id=memory_id,
        memory_actor_id=memory_actor_id,
        agent_log_group=agent_log_group,
        opensearch_url=opensearch_url,
        opensearch_username=opensearch_username,
        opensearch_password=opensearch_password,
        opensearch_use_iam=opensearch_use_iam,
        max_result_chars=max_result_chars,
        debug_mode=debug_mode,
        model_id_override=model_id_override,
    )
