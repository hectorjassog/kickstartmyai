output "app_log_group_name" {
  description = "Name of the application log group"
  value       = aws_cloudwatch_log_group.app_logs.name
}

output "app_log_group_arn" {
  description = "ARN of the application log group"
  value       = aws_cloudwatch_log_group.app_logs.arn
}

output "nginx_log_group_name" {
  description = "Name of the nginx log group"
  value       = aws_cloudwatch_log_group.nginx_logs.name
}

output "nginx_log_group_arn" {
  description = "ARN of the nginx log group"
  value       = aws_cloudwatch_log_group.nginx_logs.arn
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic for alerts"
  value       = aws_sns_topic.alerts.arn
}

output "dashboard_url" {
  description = "URL of the CloudWatch dashboard"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}
