variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "replica_region" {
  description = "AWS region for secret replication"
  type        = string
  default     = "us-west-2"
}

variable "create_redis_auth_token" {
  description = "Whether to create Redis auth token secret"
  type        = bool
  default     = true
}

# Database variables
variable "db_username" {
  description = "Database username"
  type        = string
  default     = "app_user"
}

variable "db_host" {
  description = "Database host"
  type        = string
}

variable "db_port" {
  description = "Database port"
  type        = number
  default     = 5432
}

variable "db_name" {
  description = "Database name"
  type        = string
}

# API Keys (optional, can be set later)
variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  default     = "your-openai-api-key-here"
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "Anthropic API key"
  type        = string
  default     = "your-anthropic-api-key-here"
  sensitive   = true
}
