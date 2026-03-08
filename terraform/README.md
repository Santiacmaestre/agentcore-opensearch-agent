# OpenSearch Agent -- Terraform

Infrastructure as code for the OpenSearch agent on AWS Bedrock AgentCore.

## Usage

```bash
terraform init
terraform apply -var="opensearch_url=https://your-cluster.us-east-1.es.amazonaws.com"
```

## Variables

| Variable                      | Default              | Description                                    |
|-------------------------------|----------------------|------------------------------------------------|
| `region`                      | `us-west-2`          | AWS region for all resources                   |
| `agent_name`                  | `opensearch_explorer`| AgentCore runtime name                         |
| `model_id`                    | `us.amazon.nova-premier-v1:0` | Bedrock model ID                      |
| `ecr_repo_name`               | `opensearch-agentcore` | ECR repository name                          |
| `image_tag`                   | `latest`             | Docker image tag                               |
| `ecr_keep_last`               | `30`                 | Max images in ECR                              |
| `max_result_chars`            | `20000`              | Tool output cap (bytes)                        |
| `memory_actor_id`             | `opensearch-agent`   | Memory actor namespace                         |
| `enable_memory_summarization` | `true`               | Attach SUMMARIZATION strategy                  |
| `memory_event_expiry_days`    | `7`                  | Memory event TTL                               |
| `agent_log_group_name`        | `""`                 | Log group override                             |
| `agent_log_retention_days`    | `1`                  | Log retention                                  |
| `opensearch_url`              | (required)           | OpenSearch cluster endpoint                    |
| `opensearch_username`         | `""`                 | Basic auth username                            |
| `opensearch_password`         | `""`                 | Basic auth password                            |
| `opensearch_use_iam`          | `false`              | Use IAM/SigV4 auth                             |

## Outputs

| Output                     | Description                          |
|----------------------------|--------------------------------------|
| `ecr_repository_url`       | ECR repository URL                   |
| `image_uri`                | Full image URI with tag              |
| `agent_runtime_arn`        | AgentCore runtime ARN                |
| `runtime_role_arn`         | IAM execution role ARN               |
| `memory_id`                | AgentCore Memory resource ID         |
| `agent_execution_log_group`| CloudWatch log group name            |
