#######################################################################
# File: variables.tf
#
# Description:
#   Input variables for the OpenSearch agent deployed on
#   AWS Bedrock AgentCore.
#######################################################################

# Controls which AWS region all resources are created in
variable "region" {
  type        = string
  description = "AWS region where AgentCore runtime and ECR repository are deployed."
  default     = "us-west-2"
}

# Drives resource naming and the AgentCore runtime identifier
variable "agent_name" {
  type        = string
  description = "Logical name for the AgentCore runtime, used to compose resource names."
  default     = "opensearch_explorer"
}

# Determines which Bedrock model the agent calls during the agentic loop
variable "model_id" {
  type        = string
  description = "Bedrock model or cross-region inference profile ID invoked by the container."
  default     = "us.amazon.nova-premier-v1:0"
}

# Identifies the ECR repository that stores the agent container image
variable "ecr_repo_name" {
  type        = string
  description = "Name of the ECR repository created to host the agent Docker image."
  default     = "opensearch-agentcore"
}

# Pinning the image tag triggers a rebuild and runtime update on apply
variable "image_tag" {
  type        = string
  description = "Docker image tag built, pushed to ECR, and registered with AgentCore."
  default     = "latest"
}

# Prevents unbounded ECR storage growth
variable "ecr_keep_last" {
  type        = number
  description = "Maximum number of images to retain in ECR before the lifecycle policy expires older ones."
  default     = 30
}

# Hard cap on serialised JSON bytes returned per tool result
variable "max_result_chars" {
  type        = number
  description = "Hard cap (bytes) on the JSON returned per tool result."
  default     = 20000
}

# Scopes memories to a logical user or team
variable "memory_actor_id" {
  type        = string
  description = "Actor ID that owns memories in the AgentCore Memory resource."
  default     = "opensearch-agent"
}

# Enables automatic summarisation of conversation turns
variable "enable_memory_summarization" {
  type        = bool
  description = "When true, a SUMMARIZATION strategy is attached to the Memory resource."
  default     = true
}

# Memory event expiry
variable "memory_event_expiry_days" {
  type        = number
  description = "Number of days before individual Memory events are automatically expired."
  default     = 7
}

# Agent execution log group override
variable "agent_log_group_name" {
  type        = string
  description = "Override for the CloudWatch Log Group name. Defaults to /aws/bedrock-agentcore/<agent_name> when empty."
  default     = ""
}

# Log retention
variable "agent_log_retention_days" {
  type        = number
  description = "Retention period in days for the agent execution log group."
  default     = 1
}

# -- OpenSearch connection variables ------------------------------------------

variable "opensearch_url" {
  type        = string
  description = "OpenSearch cluster endpoint URL (e.g. https://vpc-xxx.us-west-2.es.amazonaws.com)."
}

variable "opensearch_domain_arn" {
  type        = string
  description = "ARN of the OpenSearch domain. Used to scope IAM permissions to the specific domain."
}

variable "opensearch_admin_role_arn" {
  type        = string
  description = "IAM role ARN with admin access to the OpenSearch domain. The runtime role assumes this to authenticate."
  default     = ""
}

variable "opensearch_username" {
  type        = string
  description = "Basic auth username for OpenSearch. Leave empty for IAM auth."
  default     = ""
  sensitive   = true
}

variable "opensearch_password" {
  type        = string
  description = "Basic auth password for OpenSearch. Leave empty for IAM auth."
  default     = ""
  sensitive   = true
}

variable "opensearch_use_iam" {
  type        = bool
  description = "When true, use IAM/SigV4 authentication instead of basic auth."
  default     = false
}

# -- VPC networking -----------------------------------------------------------

variable "vpc_subnet_ids" {
  type        = list(string)
  description = "Subnet IDs where the AgentCore runtime container is placed. Must have connectivity to the OpenSearch VPC endpoint."
}

variable "vpc_security_group_ids" {
  type        = list(string)
  description = "Security group IDs attached to the AgentCore runtime ENIs. Must allow outbound to the OpenSearch domain (port 443)."
}
