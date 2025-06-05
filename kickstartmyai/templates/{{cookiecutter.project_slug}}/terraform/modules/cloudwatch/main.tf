# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "app_logs" {
  name              = "/aws/ecs/${var.environment}-${var.project_name}"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.environment}-${var.project_name}-app-logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_log_group" "nginx_logs" {
  name              = "/aws/ecs/${var.environment}-${var.project_name}/nginx"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.environment}-${var.project_name}-nginx-logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

# SNS Topic for Alarms
resource "aws_sns_topic" "alerts" {
  name = "${var.environment}-${var.project_name}-alerts"

  tags = {
    Name        = "${var.environment}-${var.project_name}-alerts"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_sns_topic_subscription" "email" {
  count     = length(var.alert_email_addresses)
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email_addresses[count.index]
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.environment}-${var.project_name}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", var.alb_arn_suffix],
            [".", "TargetResponseTime", ".", "."],
            [".", "HTTPCode_Target_2XX_Count", ".", "."],
            [".", "HTTPCode_Target_4XX_Count", ".", "."],
            [".", "HTTPCode_Target_5XX_Count", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Application Load Balancer Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ServiceName", var.ecs_service_name, "ClusterName", var.ecs_cluster_name],
            [".", "MemoryUtilization", ".", ".", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "ECS Service Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", var.rds_instance_id],
            [".", "DatabaseConnections", ".", "."],
            [".", "FreeableMemory", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "RDS Metrics"
          period  = 300
        }
      }
    ]
  })
}

# Application Load Balancer Alarms
resource "aws_cloudwatch_metric_alarm" "alb_target_response_time_high" {
  alarm_name          = "${var.environment}-${var.project_name}-alb-response-time-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Average"
  threshold           = "2"
  alarm_description   = "This metric monitors ALB response time"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
  }

  tags = {
    Name        = "${var.environment}-${var.project_name}-alb-response-time-alarm"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_metric_alarm" "alb_5xx_errors_high" {
  alarm_name          = "${var.environment}-${var.project_name}-alb-5xx-errors-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors ALB 5XX errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
  }

  tags = {
    Name        = "${var.environment}-${var.project_name}-alb-5xx-alarm"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ECS Service Alarms
resource "aws_cloudwatch_metric_alarm" "ecs_cpu_high" {
  alarm_name          = "${var.environment}-${var.project_name}-ecs-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ECS CPU utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ServiceName = var.ecs_service_name
    ClusterName = var.ecs_cluster_name
  }

  tags = {
    Name        = "${var.environment}-${var.project_name}-ecs-cpu-alarm"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_metric_alarm" "ecs_memory_high" {
  alarm_name          = "${var.environment}-${var.project_name}-ecs-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ECS memory utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ServiceName = var.ecs_service_name
    ClusterName = var.ecs_cluster_name
  }

  tags = {
    Name        = "${var.environment}-${var.project_name}-ecs-memory-alarm"
    Environment = var.environment
    Project     = var.project_name
  }
}

# RDS Alarms
resource "aws_cloudwatch_metric_alarm" "rds_cpu_high" {
  count               = var.rds_instance_id != "" ? 1 : 0
  alarm_name          = "${var.environment}-${var.project_name}-rds-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors RDS CPU utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    DBInstanceIdentifier = var.rds_instance_id
  }

  tags = {
    Name        = "${var.environment}-${var.project_name}-rds-cpu-alarm"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_connections_high" {
  count               = var.rds_instance_id != "" ? 1 : 0
  alarm_name          = "${var.environment}-${var.project_name}-rds-connections-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors RDS connection count"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    DBInstanceIdentifier = var.rds_instance_id
  }

  tags = {
    Name        = "${var.environment}-${var.project_name}-rds-connections-alarm"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Custom Application Metrics
resource "aws_cloudwatch_log_metric_filter" "error_count" {
  name           = "${var.environment}-${var.project_name}-error-count"
  log_group_name = aws_cloudwatch_log_group.app_logs.name
  pattern        = "[timestamp, request_id, level=\"ERROR\", ...]"

  metric_transformation {
    name      = "ErrorCount"
    namespace = "Application/${var.project_name}"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "application_error_rate_high" {
  alarm_name          = "${var.environment}-${var.project_name}-error-rate-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ErrorCount"
  namespace           = "Application/${var.project_name}"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors application error rate"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "${var.environment}-${var.project_name}-error-rate-alarm"
    Environment = var.environment
    Project     = var.project_name
  }
}
