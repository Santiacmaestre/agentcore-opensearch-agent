#######################################################################
# File: agentcore.tf
#
# Description:
#   Defines the Bedrock AgentCore runtime that runs the OpenSearch
#   agent container. Wires the ECR image, IAM execution role, and
#   environment configuration into a single deployable runtime unit.
#
# Notes:
#   - network_mode CUSTOMER_VPC is used so the container can reach
#     VPC-internal OpenSearch endpoints via the provided subnets and
#     security groups.
#   - Bedrock and other AWS API calls go through VPC endpoints or
#     NAT gateways configured in the target VPC.
#######################################################################

# Runs the OpenSearch agent container on AgentCore inside the customer VPC
resource "aws_bedrockagentcore_agent_runtime" "this" {
  agent_runtime_name = var.agent_name
  role_arn           = local.runtime_role_arn

  agent_runtime_artifact {
    container_configuration {
      container_uri = local.image_uri
    }
  }

  network_configuration {
    network_mode = "VPC"

    customer_vpc_configuration {
      subnet_ids         = var.vpc_subnet_ids
      security_group_ids = var.vpc_security_group_ids
    }
  }

  environment_variables = {
    AWS_REGION           = var.region
    MODEL_ID             = var.model_id
    MAX_RESULT_CHARS     = tostring(var.max_result_chars)
    MEMORY_ID            = aws_bedrockagentcore_memory.this.id
    MEMORY_ACTOR_ID      = var.memory_actor_id
    AGENT_LOG_GROUP      = aws_cloudwatch_log_group.agent_execution.name
    OPENSEARCH_URL       = var.opensearch_url
    OPENSEARCH_USERNAME  = var.opensearch_username
    OPENSEARCH_PASSWORD  = var.opensearch_password
    OPENSEARCH_USE_IAM   = tostring(var.opensearch_use_iam)
  }

  depends_on = [
    aws_iam_role_policy.runtime_inline,
    null_resource.docker_build_push,
    aws_bedrockagentcore_memory.this,
    aws_cloudwatch_log_group.agent_execution,
  ]
}
