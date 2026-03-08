#######################################################################
# File: iam.tf
#
# Description:
#   IAM role and inline policy that the AgentCore runtime assumes at
#   execution time. Grants least-privilege access to the specific
#   OpenSearch domain, Bedrock model invocation, ECR image pulling,
#   and VPC ENI management for CUSTOMER_VPC network mode.
#######################################################################

# Allows the AgentCore service principal to assume the runtime execution role
data "aws_iam_policy_document" "agentcore_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }
  }
}

# Execution role assumed by the AgentCore runtime during agent invocations
resource "aws_iam_role" "runtime" {
  name               = local.runtime_role_name
  assume_role_policy = data.aws_iam_policy_document.agentcore_assume_role.json
}

# Defines the permission boundaries for OpenSearch, Bedrock, ECR, VPC, and STS
data "aws_iam_policy_document" "runtime_policy" {
  # OpenSearch HTTP access scoped to the specific domain
  statement {
    sid = "OpenSearchDomainAccess"
    actions = [
      "es:ESHttpGet",
      "es:ESHttpPost",
      "es:ESHttpPut",
      "es:ESHttpHead",
      "es:ESHttpDelete",
    ]
    resources = [
      var.opensearch_domain_arn,
      "${var.opensearch_domain_arn}/*",
    ]
  }

  # OpenSearch describe/list (account-scoped, read-only)
  statement {
    sid = "OpenSearchDescribe"
    actions = [
      "es:DescribeElasticsearchDomains",
      "es:DescribeDomains",
      "es:ListDomainNames",
      "es:ListTags",
    ]
    resources = ["*"]
  }

  # VPC ENI management required for CUSTOMER_VPC network mode
  statement {
    sid = "VPCNetworking"
    actions = [
      "ec2:CreateNetworkInterface",
      "ec2:DescribeNetworkInterfaces",
      "ec2:DeleteNetworkInterface",
      "ec2:DescribeSubnets",
      "ec2:DescribeSecurityGroups",
      "ec2:DescribeVpcs",
    ]
    resources = ["*"]
  }

  # CloudWatch Logs write (for agent audit logs only)
  statement {
    sid = "CloudWatchLogsWrite"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogStreams"
    ]
    resources = [local.agentcore_log_arn]
  }

  # Bedrock model invocation
  statement {
    sid = "BedrockInvoke"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
      "bedrock:Converse",
      "bedrock:ConverseStream",
    ]
    resources = ["*"]
  }

  # ECR image pulling
  statement {
    sid = "ECRPull"
    actions = [
      "ecr:GetAuthorizationToken",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer"
    ]
    resources = ["*"]
  }

  # STS AssumeRole for cross-account access and OpenSearch admin role
  statement {
    sid     = "STSAssumeRole"
    actions = ["sts:AssumeRole"]
    resources = compact([
      var.opensearch_admin_role_arn,
      "*",
    ])
  }

  # AgentCore Memory access
  statement {
    sid = "AgentCoreMemory"
    actions = [
      "bedrock-agentcore:CreateEvent",
      "bedrock-agentcore:ListMemories",
      "bedrock-agentcore:GetMemory",
    ]
    resources = ["arn:aws:bedrock-agentcore:${var.region}:*:memory/${aws_bedrockagentcore_memory.this.id}"]
  }
}

# Attaches the permissions policy inline
resource "aws_iam_role_policy" "runtime_inline" {
  name   = local.runtime_inline_policy_name
  role   = aws_iam_role.runtime.id
  policy = data.aws_iam_policy_document.runtime_policy.json
}
