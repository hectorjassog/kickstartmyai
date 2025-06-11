output "endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.main.endpoint
}

output "port" {
  description = "RDS instance port"
  value       = aws_db_instance.main.port
}

output "db_name" {
  description = "Database name"
  value       = aws_db_instance.main.db_name
}

output "username" {
  description = "Database username"
  value       = aws_db_instance.main.username
  sensitive   = true
}

output "security_group_id" {
  description = "Security group ID for RDS"
  value       = aws_security_group.rds.id
}
