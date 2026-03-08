#######################################################################
# File: outputs.tf
#
# Description:
#   Exposes key identifiers produced by this module.
#######################################################################

# ECR repository URL
output "ecr_repository_url" {
  value = aws_ecr_repository.agent.repository_url
}

# Exact image registered with AgentCore
output "image_uri" {
  value = local.image_uri
}

# Required by invoke_agent.py
output "agent_runtime_arn" {
  value = aws_bedrockagentcore_agent_runtime.this.agent_runtime_arn
}

# IAM role assumed by the runtime
output "runtime_role_arn" {
  value = aws_iam_role.runtime.arn
}

# Memory resource ID
output "memory_id" {
  value = aws_bedrockagentcore_memory.this.id
}

# Agent execution log group
output "agent_execution_log_group" {
  value = aws_cloudwatch_log_group.agent_execution.name
}
