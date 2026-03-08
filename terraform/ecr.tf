#######################################################################
# File: ecr.tf
#
# Description:
#   ECR repository that stores the agent Docker image and the lifecycle
#   policy that caps storage by expiring images beyond a retention count.
#######################################################################

# Stores the OpenSearch agent container image
resource "aws_ecr_repository" "agent" {
  name                 = var.ecr_repo_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

# Expires images exceeding the retention count
resource "aws_ecr_lifecycle_policy" "agent" {
  repository = aws_ecr_repository.agent.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = local.ecr_lifecycle_description
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = var.ecr_keep_last
        }
        action = { type = "expire" }
      }
    ]
  })
}
