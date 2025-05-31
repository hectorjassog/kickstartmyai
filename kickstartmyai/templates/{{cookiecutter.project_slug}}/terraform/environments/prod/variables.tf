# Production Environment Variables

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

# Database variables
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
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

# Redis variables
variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro"
}

# ECS variables
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
  description = "Desired number of ECS tasks"
  type        = number
  default     = 2
}

variable "cpu" {
  description = "CPU units for ECS task"
  type        = number
  default     = 256
}

variable "memory" {
  description = "Memory for ECS task"
  type        = number
  default     = 512
}

# SSL Certificate
variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS"
  type        = string
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
