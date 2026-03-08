# OpenSearch Agent -- Application

Python agent that uses the **Strands Agents SDK** and the **official OpenSearch MCP server** to query, explore, and analyse data in OpenSearch clusters.

## Local development

```bash
# Create venv and install
uv venv .venv && source .venv/bin/activate
uv pip install -e .

# Configure
cp .env.example .env   # fill in values

# Run
python -m os_search_agent
```

## Environment variables

| Variable              | Required | Description                                       |
|-----------------------|----------|---------------------------------------------------|
| `AWS_REGION`          | Yes      | AgentCore runtime region                          |
| `MODEL_ID`            | No       | Bedrock model ID (defaults by region)             |
| `MEMORY_ID`           | Yes      | AgentCore Memory resource ID                      |
| `MEMORY_ACTOR_ID`     | Yes      | Actor namespace for Memory                        |
| `AGENT_LOG_GROUP`     | Yes      | CloudWatch Log Group for agent logs               |
| `OPENSEARCH_URL`      | Yes      | OpenSearch cluster endpoint                       |
| `OPENSEARCH_USERNAME` | No       | Basic auth username (empty for IAM auth)          |
| `OPENSEARCH_PASSWORD` | No       | Basic auth password (empty for IAM auth)          |
| `OPENSEARCH_USE_IAM`  | No       | "true" for IAM/SigV4 auth                        |
| `MAX_RESULT_CHARS`    | No       | Soft cap for tool output (default 20000)          |
| `DEBUG_MODE`          | No       | "true" enables verbose logging                    |

## Interactive commands

| Command                | Description                        |
|------------------------|------------------------------------|
| `/help`                | Show available commands            |
| `/reset`               | Clear conversation history         |
| `/summarize`           | Session summary from memory        |
| `/recall <sessionId>`  | Load a previous session            |
| `/export`              | Export investigation bundle        |
| `/quit`                | Exit the agent                     |
