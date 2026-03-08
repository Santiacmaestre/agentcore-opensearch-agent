#######################################################################
# File: cloudwatch.tf
#
# Description:
#   CloudWatch Log Group used by the agent container to write
#   structured JSON execution logs.
#######################################################################

# Destination log group where the agent writes structured audit/execution logs
resource "aws_cloudwatch_log_group" "agent_execution" {
  name              = local.resolved_agent_log_group_name
  retention_in_days = var.agent_log_retention_days
}
