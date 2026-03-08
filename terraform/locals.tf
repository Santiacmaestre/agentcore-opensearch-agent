#######################################################################
# File: locals.tf
#
# Description:
#   Derived values composed from variables and resource attributes.
#######################################################################

# Container image reference
locals {
  image_uri    = "${aws_ecr_repository.agent.repository_url}:${var.image_tag}"
  ecr_registry = aws_ecr_repository.agent.repository_url
}

# IAM identifiers composed from the agent name
locals {
  runtime_role_name          = "${var.agent_name}_runtime_role"
  runtime_inline_policy_name = "${var.agent_name}_runtime_inline"
  agentcore_log_arn          = "arn:aws:logs:${var.region}:*:log-group:/aws/bedrock-agentcore/*:*"
  runtime_role_arn           = aws_iam_role.runtime.arn
}

# Log group name
locals {
  resolved_agent_log_group_name = var.agent_log_group_name != "" ? var.agent_log_group_name : "/aws/bedrock-agentcore/${var.agent_name}"
}

# ECR lifecycle policy description
locals {
  ecr_lifecycle_description = "Keep last ${var.ecr_keep_last} images"
}
