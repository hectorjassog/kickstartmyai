# Production Environment Variables - Cost Optimized for $50-100/month

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "{{cookiecutter.aws_region}}"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# Cost optimization settings
variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "cost_budget_monthly" {
  description = "Monthly cost budget in USD"
  type        = number
  default     = 100
}

variable "enable_cost_optimization" {
  description = "Enable cost optimization features"
  type        = bool
  default     = true
}

# Database variables - Cost optimized
variable "db_name" {
  description = "Database name"
  type        = string
  default     = "{{cookiecutter.database_name}}"
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "{{cookiecutter.database_user}}"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "RDS instance class - t3.micro for cost optimization"
  type        = string
  default     = "db.t3.micro"  # ~$13/month
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20  # Minimum for gp3, ~$2.3/month
}

variable "db_storage_type" {
  description = "RDS storage type"
  type        = string
  default     = "gp3"  # More cost effective than gp2
}

variable "db_backup_retention_period" {
  description = "Database backup retention period in days"
  type        = number
  default     = 7  # Reduced from default 30 for cost savings
}

variable "db_enable_deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = true
}

# Redis variables - Cost optimized
variable "redis_node_type" {
  description = "ElastiCache node type - t3.micro for cost optimization"
  type        = string
  default     = "cache.t3.micro"  # ~$12/month
}

variable "redis_num_cache_nodes" {
  description = "Number of cache nodes"
  type        = number
  default     = 1  # Single node for cost optimization
}

# ECS variables - Cost optimized
variable "app_image" {
  description = "Docker image for the application"
  type        = string
}

variable "app_port" {
  description = "Application port"
  type        = number
  default     = 8000
}

variable "desired_count" {
  description = "Desired number of ECS tasks - reduced for cost"
  type        = number
  default     = 1  # Reduced from 2 for cost optimization
}

variable "cpu" {
  description = "CPU units for ECS task - 256 (0.25 vCPU)"
  type        = number
  default     = 256  # ~$6/month for 24/7 operation
}

variable "memory" {
  description = "Memory for ECS task in MB"
  type        = number
  default     = 512  # ~$3/month for 24/7 operation
}

variable "enable_ecs_auto_scaling" {
  description = "Enable ECS auto scaling"
  type        = bool
  default     = true
}

variable "ecs_min_capacity" {
  description = "Minimum ECS task count"
  type        = number
  default     = 1
}

variable "ecs_max_capacity" {
  description = "Maximum ECS task count"
  type        = number
  default     = 3  # Limited scaling for cost control
}

# SSL Certificate - Free with AWS Certificate Manager
variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS (optional - will create if not provided)"
  type        = string
  default     = ""
}

variable "domain_name" {
  description = "Domain name for SSL certificate"
  type        = string
  default     = ""
}

variable "create_certificate" {
  description = "Create ACM certificate automatically"
  type        = bool
  default     = false
}

variable "route53_zone_id" {
  description = "Route53 hosted zone ID for domain validation"
  type        = string
  default     = ""
}

# CloudWatch Log Retention - Cost optimized
variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 7  # Reduced for cost optimization
}

variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring (additional cost)"
  type        = bool
  default     = false  # Disabled for cost optimization
}

# Secrets
variable "secret_key" {
  description = "Application secret key"
  type        = string
  sensitive   = true
}

variable "secret_key_arn" {
  description = "ARN of secret key in Secrets Manager"
  type        = string
}

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "openai_api_key_arn" {
  description = "ARN of OpenAI API key in Secrets Manager"
  type        = string
  default     = ""
}

variable "anthropic_api_key" {
  description = "Anthropic API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "anthropic_api_key_arn" {
  description = "ARN of Anthropic API key in Secrets Manager"
  type        = string
  default     = ""
}

variable "gemini_api_key" {
  description = "Google Gemini API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "gemini_api_key_arn" {
  description = "ARN of Gemini API key in Secrets Manager"
  type        = string
  default     = ""
}
