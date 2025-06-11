output "db_secret_arn" {
  description = "ARN of the database credentials secret"
  value       = aws_secretsmanager_secret.db_credentials.arn
}

output "db_secret_name" {
  description = "Name of the database credentials secret"
  value       = aws_secretsmanager_secret.db_credentials.name
}

output "redis_secret_arn" {
  description = "ARN of the Redis auth token secret"
  value       = var.create_redis_auth_token ? aws_secretsmanager_secret.redis_auth[0].arn : null
}

output "redis_secret_name" {
  description = "Name of the Redis auth token secret"
  value       = var.create_redis_auth_token ? aws_secretsmanager_secret.redis_auth[0].name : null
}

output "jwt_secret_arn" {
  description = "ARN of the JWT secret"
  value       = aws_secretsmanager_secret.jwt_secret.arn
}

output "jwt_secret_name" {
  description = "Name of the JWT secret"
  value       = aws_secretsmanager_secret.jwt_secret.name
}

output "api_keys_secret_arn" {
  description = "ARN of the API keys secret"
  value       = aws_secretsmanager_secret.api_keys.arn
}

output "api_keys_secret_name" {
  description = "Name of the API keys secret"
  value       = aws_secretsmanager_secret.api_keys.name
}

output "ecs_secrets_role_arn" {
  description = "ARN of the ECS secrets access role"
  value       = aws_iam_role.ecs_secrets_role.arn
}

output "db_password" {
  description = "Generated database password"
  value       = random_password.db_password.result
  sensitive   = true
}

output "redis_auth_token" {
  description = "Generated Redis auth token"
  value       = var.create_redis_auth_token ? random_password.redis_auth_token[0].result : null
  sensitive   = true
}

output "jwt_secret_key" {
  description = "Generated JWT secret key"
  value       = random_password.jwt_secret.result
  sensitive   = true
}
