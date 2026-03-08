# agentcore-opensearch-agent

OpenSearch data exploration agent built on **Amazon Bedrock AgentCore**.
The agent uses a conversational interface to query, explore, and analyse data stored in OpenSearch clusters -- powered by the **Strands Agents SDK** and the **official OpenSearch MCP server**.


## Overview

| Layer               | Technology                                                         |
|---------------------|--------------------------------------------------------------------|
| LLM                 | Amazon Nova Premier / Nova Pro via Strands Agents SDK              |
| Agentic framework   | Strands Agents SDK (`strands-agents`, `strands-agents-tools`)      |
| Runtime             | Amazon Bedrock AgentCore (arm64 container)                         |
| Persistent memory   | AgentCore Memory with session-scoped summarization                 |
| Data tools          | `opensearch-mcp-server-py` (official OpenSearch MCP server, stdio) |
| Infrastructure      | Terraform (AWS provider >= 6.17)                                   |
| Application         | Python 3.12+ packaged with `uv`                                   |


## Architecture

```
+---------------------------------------------------------------------+
|  Developer / CI                                                      |
|  terraform apply  -->  ECR (arm64 image)  -->  AgentCore Runtime     |
+---------------------------------------------------------------------+
                                                        |
                          +-----------------------------v--------------+
                          |           AgentCore Runtime                 |
                          |  +--------------------------------------+  |
                          |  |  Python container (os_search_agent)  |  |
                          |  |  +----------+  +------------------+  |  |
                          |  |  |  CLI /   |  |  Strands Agent   |  |  |
                          |  |  |  REPL    |  |  (agentic loop)  |  |  |
                          |  |  +----+-----+  +--------+---------+  |  |
                          |  |       |                 |            |  |
                          |  |  +----v-----------------v---------+  |  |
                          |  |  |     MCPClient (Strands SDK)    |  |  |
                          |  |  |     OpenSearch MCP Server      |  |  |
                          |  |  +--------------------------------+  |  |
                          |  +--------------------------------------+  |
                          |                   |                        |
                          |  AgentCore Memory (cross-session recall)   |
                          +--------------------------------------------+
                                              |
                          +-------------------v-----------------------+
                          |  OpenSearch Cluster                        |
                          |  (Amazon OpenSearch Service or self-hosted)|
                          |  Indices . Mappings . Aggregations         |
                          +-------------------------------------------+
```


## Repository Layout

```
agentcore-opensearch-agent/
+-- app/                      # Python agent application
|   +-- src/os_search_agent/  # Agent source code
|   +-- scripts/              # build_and_push.sh, run_local.sh
|   +-- Dockerfile            # arm64 container image
|   +-- invoke_agent.py       # Remote runtime invocation helper
|   +-- pyproject.toml        # Package metadata & dependencies
|   +-- README.md             # Application guide
+-- terraform/                # Infrastructure as code
    +-- agentcore.tf          # AgentCore runtime resource
    +-- memory.tf             # AgentCore Memory + summarization strategy
    +-- iam.tf                # Execution role & inline policy
    +-- ecr.tf                # ECR repository + lifecycle policy
    +-- docker.tf             # null_resource: build & push on change
    +-- cloudwatch.tf         # CloudWatch log group
    +-- locals.tf             # Derived identifiers
    +-- variables.tf          # All input variables with defaults
    +-- outputs.tf            # Key resource identifiers
    +-- providers.tf          # Terraform & AWS provider config
```


## Prerequisites

| Tool      | Minimum version   | Notes                                        |
|-----------|-------------------|----------------------------------------------|
| AWS CLI   | v2                | Must have ECR push & Bedrock permissions     |
| Docker    | 24+ with `buildx` | Required for arm64 cross-compilation         |
| Terraform | 1.5.0             | AWS provider >= 6.17 is fetched automatically |
| Python    | 3.12              | Only needed for local CLI usage              |
| `uv`      | latest            | Python package manager used in the app       |


## Getting Started

### 1. Provision infrastructure

```bash
cd terraform/
terraform init
terraform apply -var="opensearch_url=https://your-cluster.us-east-1.es.amazonaws.com"
```

`terraform apply` will:
- Create an ECR repository
- Build & push the arm64 Docker image
- Provision an AgentCore runtime wired to Bedrock and OpenSearch
- Create an AgentCore Memory resource with summarization
- Set up CloudWatch log group and IAM execution role

### 2. Run the agent

**Remote** (via the deployed AgentCore runtime):

```bash
cd app/
# ARN is discovered automatically from terraform output
python invoke_agent.py --interactive
```

**Local** (for development):

```bash
cd app/
cp .env.example .env   # fill in all values
./scripts/run_local.sh
```

See [app/README.md](app/README.md) for interactive commands and configuration details.


## OpenSearch MCP Tools

The agent has access to these tools via the official OpenSearch MCP server:

| Tool                      | Description                                    |
|---------------------------|------------------------------------------------|
| `ListIndexTool`           | List all indices with metadata                 |
| `IndexMappingTool`        | Get mappings and settings for specific indices |
| `SearchIndexTool`         | Execute queries using OpenSearch Query DSL     |
| `GetShardsTool`           | Retrieve shard information                     |
| `ClusterHealthTool`       | Check cluster health status                    |
| `CountTool`               | Count documents with optional filters          |
| `ExplainTool`             | Query relevance scoring explanation            |
| `MsearchTool`             | Batch/multi-search execution                   |
| `GenericOpenSearchApiTool` | Call any OpenSearch REST API endpoint          |
| `DataDistributionTool`    | Analyse field value distributions              |
| `LogPatternAnalysisTool`  | Anomaly detection with baseline comparison     |


## Key Design Decisions

- **Strands Agents SDK** -- the entire agentic loop (tool discovery, execution, retry, conversation history) is delegated to Strands.
- **Official OpenSearch MCP server** -- uses `opensearch-mcp-server-py` from the OpenSearch project, ensuring compatibility and correctness.
- **No fabricated data** -- the system prompt strictly enforces that every piece of data presented must come from an actual tool call.
- **Query DSL generation** -- the agent writes OpenSearch Query DSL itself; users describe what they want in natural language.
- **Cross-account via STS** -- assumed-role credentials are injected as environment variables into the MCP subprocess.
- **arm64 only** -- AgentCore runtimes run exclusively on arm64; the Docker build uses `buildx --platform linux/arm64`.
- **Content-addressable Docker builds** -- `docker.tf` hashes source files as Terraform triggers so the image is only rebuilt when code actually changes.


## License

See [LICENSE](LICENSE).
