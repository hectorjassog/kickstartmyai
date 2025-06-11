# CloudWatch Log Groups - Cost Optimized
resource "aws_cloudwatch_log_group" "app_logs" {
  name              = "/ecs/${var.name_prefix}"
  retention_in_days = var.log_retention_days  # Reduced retention for cost savings
  kms_key_id        = var.enable_log_encryption ? aws_kms_key.cloudwatch[0].arn : null

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-app-logs"
    CostOptimized = "true"
    RetentionDays = var.log_retention_days
  })
}

# Cost Monitoring CloudWatch Log Group
resource "aws_cloudwatch_log_group" "cost_logs" {
  count             = var.enable_cost_monitoring ? 1 : 0
  name              = "/aws/cost/${var.name_prefix}"
  retention_in_days = 30  # Longer retention for cost analysis

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-cost-logs"
    Purpose = "cost-monitoring"
  })
}

# KMS Key for log encryption (optional)
resource "aws_kms_key" "cloudwatch" {
  count                   = var.enable_log_encryption ? 1 : 0
  description             = "KMS key for CloudWatch logs encryption"
  deletion_window_in_days = 7  # Reduced for cost optimization

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-cloudwatch-kms"
  })
}

resource "aws_kms_alias" "cloudwatch" {
  count         = var.enable_log_encryption ? 1 : 0
  name          = "alias/${var.name_prefix}-cloudwatch"
  target_key_id = aws_kms_key.cloudwatch[0].key_id
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
  alarm_name          = "${var.name_prefix}-error-rate-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ErrorCount"
  namespace           = "Application/${var.name_prefix}"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors application error rate"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-error-rate-alarm"
  })
}

# Cost Budget - Critical for staying under $100/month
resource "aws_budgets_budget" "monthly_cost" {
  count        = var.enable_cost_monitoring ? 1 : 0
  name         = "${var.name_prefix}-monthly-budget"
  budget_type  = "COST"
  limit_amount = var.monthly_budget_limit
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  time_period_start = "2024-01-01_00:00"

  cost_filters = {
    TagKey = ["Project"]
    TagValue = [var.name_prefix]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                 = 80  # Alert at 80% of budget
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_email_addresses = var.alert_email_addresses
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                 = 100  # Alert when budget exceeded
    threshold_type            = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = var.alert_email_addresses
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-budget"
    Purpose = "cost-control"
  })
}

# Cost Anomaly Detection
resource "aws_ce_anomaly_detector" "cost_anomaly" {
  count         = var.enable_cost_monitoring ? 1 : 0
  name          = "${var.name_prefix}-cost-anomaly"
  monitor_type  = "DIMENSIONAL"

  specification = jsonencode({
    Dimension = "SERVICE"
    MatchOptions = ["EQUALS"]
    Values = ["Amazon Elastic Container Service", "Amazon Relational Database Service", "Amazon ElastiCache"]
  })

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-cost-anomaly"
  })
}

# Cost Anomaly Subscription
resource "aws_ce_anomaly_subscription" "cost_anomaly_alerts" {
  count     = var.enable_cost_monitoring && length(var.alert_email_addresses) > 0 ? 1 : 0
  name      = "${var.name_prefix}-cost-anomaly-alerts"
  frequency = "DAILY"
  
  monitor_arn_list = [
    aws_ce_anomaly_detector.cost_anomaly[0].arn
  ]
  
  subscriber {
    type    = "EMAIL"
    address = var.alert_email_addresses[0]
  }

  threshold_expression {
    and {
      dimension {
        key           = "ANOMALY_TOTAL_IMPACT_ABSOLUTE"
        values        = ["10"]  # Alert for anomalies over $10
        match_options = ["GREATER_THAN_OR_EQUAL"]
      }
    }
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-cost-anomaly-subscription"
  })
}
