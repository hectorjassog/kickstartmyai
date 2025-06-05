variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "log_retention_days" {
  description = "Number of days to retain log events"
  type        = number
  default     = 14
}

variable "alert_email_addresses" {
  description = "List of email addresses for alerts"
  type        = list(string)
  default     = []
}

variable "alb_arn_suffix" {
  description = "ALB ARN suffix for CloudWatch metrics"
  type        = string
}

variable "ecs_service_name" {
  description = "Name of the ECS service"
  type        = string
}

variable "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  type        = string
}

variable "rds_instance_id" {
  description = "RDS instance identifier"
  type        = string
  default     = ""
}
