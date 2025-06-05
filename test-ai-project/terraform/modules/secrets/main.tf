# Random password generation
resource "random_password" "db_password" {
  length  = 32
  special = true
}

resource "random_password" "redis_auth_token" {
  count   = var.create_redis_auth_token ? 1 : 0
  length  = 32
  special = false
}

resource "random_password" "jwt_secret" {
  length  = 64
  special = true
}

# Database credentials secret
resource "aws_secretsmanager_secret" "db_credentials" {
  name        = "${var.environment}/${var.project_name}/database"
  description = "Database credentials for ${var.project_name} ${var.environment}"
  
  replica {
    region = var.replica_region
  }

  tags = {
    Name        = "${var.environment}-${var.project_name}-db-secret"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db_password.result
    host     = var.db_host
    port     = var.db_port
    dbname   = var.db_name
  })
}

# Redis auth token secret
resource "aws_secretsmanager_secret" "redis_auth" {
  count       = var.create_redis_auth_token ? 1 : 0
  name        = "${var.environment}/${var.project_name}/redis-auth"
  description = "Redis authentication token for ${var.project_name} ${var.environment}"

  replica {
    region = var.replica_region
  }

  tags = {
    Name        = "${var.environment}-${var.project_name}-redis-secret"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_secretsmanager_secret_version" "redis_auth" {
  count     = var.create_redis_auth_token ? 1 : 0
  secret_id = aws_secretsmanager_secret.redis_auth[0].id
  secret_string = jsonencode({
    auth_token = random_password.redis_auth_token[0].result
  })
}

# JWT secret
resource "aws_secretsmanager_secret" "jwt_secret" {
  name        = "${var.environment}/${var.project_name}/jwt-secret"
  description = "JWT signing secret for ${var.project_name} ${var.environment}"

  replica {
    region = var.replica_region
  }

  tags = {
    Name        = "${var.environment}-${var.project_name}-jwt-secret"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_secretsmanager_secret_version" "jwt_secret" {
  secret_id = aws_secretsmanager_secret.jwt_secret.id
  secret_string = jsonencode({
    secret_key = random_password.jwt_secret.result
  })
}

# API keys secret (for AI providers)
resource "aws_secretsmanager_secret" "api_keys" {
  name        = "${var.environment}/${var.project_name}/api-keys"
  description = "API keys for external services for ${var.project_name} ${var.environment}"

  replica {
    region = var.replica_region
  }

  tags = {
    Name        = "${var.environment}-${var.project_name}-api-keys"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_secretsmanager_secret_version" "api_keys" {
  secret_id = aws_secretsmanager_secret.api_keys.id
  secret_string = jsonencode({
    openai_api_key    = var.openai_api_key
    anthropic_api_key = var.anthropic_api_key
    gemini_api_key    = var.gemini_api_key
  })
}

# IAM role for ECS to access secrets
resource "aws_iam_role" "ecs_secrets_role" {
  name = "${var.environment}-${var.project_name}-ecs-secrets-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.environment}-${var.project_name}-ecs-secrets-role"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_iam_policy" "ecs_secrets_policy" {
  name        = "${var.environment}-${var.project_name}-ecs-secrets-policy"
  description = "Policy for ECS to access secrets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.db_credentials.arn,
          aws_secretsmanager_secret.jwt_secret.arn,
          aws_secretsmanager_secret.api_keys.arn,
        ]
      }
    ]
  })
}

resource "aws_iam_policy" "ecs_secrets_redis_policy" {
  count       = var.create_redis_auth_token ? 1 : 0
  name        = "${var.environment}-${var.project_name}-ecs-secrets-redis-policy"
  description = "Policy for ECS to access Redis secrets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.redis_auth[0].arn,
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_secrets_policy_attachment" {
  role       = aws_iam_role.ecs_secrets_role.name
  policy_arn = aws_iam_policy.ecs_secrets_policy.arn
}

resource "aws_iam_role_policy_attachment" "ecs_secrets_redis_policy_attachment" {
  count      = var.create_redis_auth_token ? 1 : 0
  role       = aws_iam_role.ecs_secrets_role.name
  policy_arn = aws_iam_policy.ecs_secrets_redis_policy[0].arn
}
