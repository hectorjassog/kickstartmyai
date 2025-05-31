variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "node_type" {
  description = "The compute and memory capacity of the nodes"
  type        = string
  default     = "cache.t4g.micro"
}

variable "engine_version" {
  description = "Version number of the cache engine"
  type        = string
  default     = "7.0"
}

variable "num_cache_nodes" {
  description = "Number of cache nodes"
  type        = number
  default     = 1
}

variable "multi_az_enabled" {
  description = "Specifies whether to enable Multi-AZ Support for the replication group"
  type        = bool
  default     = false
}

variable "auth_token" {
  description = "Password used to access a password protected server"
  type        = string
  sensitive   = true
  default     = null
}

variable "maintenance_window" {
  description = "Maintenance window for the cache cluster"
  type        = string
  default     = "sun:05:00-sun:06:00"
}

variable "snapshot_retention_limit" {
  description = "Number of days for which ElastiCache retains automatic cache cluster snapshots"
  type        = number
  default     = 7
}

variable "snapshot_window" {
  description = "Daily time range during which ElastiCache begins taking a daily snapshot"
  type        = string
  default     = "03:00-04:00"
}

variable "apply_immediately" {
  description = "Whether any database modifications are applied immediately"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "Number of days to retain log events"
  type        = number
  default     = 7
}

variable "alarm_actions" {
  description = "List of ARNs to notify when this alarm transitions into an ALARM state"
  type        = list(string)
  default     = []
}
