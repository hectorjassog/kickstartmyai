output "redis_endpoint" {
  description = "Redis endpoint"
  value       = aws_elasticache_replication_group.redis.configuration_endpoint_address
}

output "redis_port" {
  description = "Redis port"
  value       = aws_elasticache_replication_group.redis.port
}

output "redis_auth_token" {
  description = "Redis auth token"
  value       = aws_elasticache_replication_group.redis.auth_token
  sensitive   = true
}

output "redis_security_group_id" {
  description = "Security group ID for Redis"
  value       = aws_security_group.redis.id
}

output "redis_subnet_group_name" {
  description = "Name of the ElastiCache subnet group"
  value       = aws_elasticache_subnet_group.redis.name
}

output "redis_parameter_group_name" {
  description = "Name of the ElastiCache parameter group"
  value       = aws_elasticache_parameter_group.redis.name
}

output "redis_replication_group_id" {
  description = "ID of the ElastiCache replication group"
  value       = aws_elasticache_replication_group.redis.id
}
