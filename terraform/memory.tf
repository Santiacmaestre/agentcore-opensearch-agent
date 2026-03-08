#######################################################################
# File: memory.tf
#
# Description:
#   Provisions the AgentCore Memory resource that the agent uses to
#   persist and recall context across sessions.
#######################################################################

locals {
  memory_resource_name = "${replace(var.agent_name, "-", "_")}_memory"
  memory_strategy_name = "${replace(var.agent_name, "-", "_")}_summarization_strategy"
}

# Persistent cross-session memory store
resource "aws_bedrockagentcore_memory" "this" {
  name                  = local.memory_resource_name
  event_expiry_duration = var.memory_event_expiry_days
  memory_execution_role_arn = local.runtime_role_arn
}

# Condenses stored conversation turns into summaries
resource "aws_bedrockagentcore_memory_strategy" "summarization" {
  count       = var.enable_memory_summarization ? 1 : 0
  name        = local.memory_strategy_name
  memory_id   = aws_bedrockagentcore_memory.this.id
  type        = "SUMMARIZATION"
  description = "Condenses OpenSearch agent conversation turns into summaries for efficient recall across sessions."
  namespaces  = ["${var.memory_actor_id}/{sessionId}"]
}
