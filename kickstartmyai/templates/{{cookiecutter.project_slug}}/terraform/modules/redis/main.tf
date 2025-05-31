# Redis ElastiCache cluster for session storage and caching
resource "aws_elasticache_subnet_group" "redis" {
  name       = "${var.environment}-${var.project_name}-redis-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name        = "${var.environment}-${var.project_name}-redis-subnet-group"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_security_group" "redis" {
  name_prefix = "${var.environment}-${var.project_name}-redis-"
  vpc_id      = var.vpc_id

  ingress {
    description = "Redis"
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.environment}-${var.project_name}-redis-sg"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_elasticache_parameter_group" "redis" {
  family = "redis7.x"
  name   = "${var.environment}-${var.project_name}-redis-params"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  tags = {
    Name        = "${var.environment}-${var.project_name}-redis-params"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id         = "${var.environment}-${var.project_name}-redis"
  description                  = "Redis cluster for ${var.project_name} ${var.environment}"
  
  node_type                    = var.node_type
  port                         = 6379
  parameter_group_name         = aws_elasticache_parameter_group.redis.name
  subnet_group_name            = aws_elasticache_subnet_group.redis.name
  security_group_ids           = [aws_security_group.redis.id]
  
  num_cache_clusters           = var.num_cache_nodes
  
  engine_version               = var.engine_version
  automatic_failover_enabled   = var.num_cache_nodes > 1
  multi_az_enabled            = var.multi_az_enabled
  
  at_rest_encryption_enabled   = true
  transit_encryption_enabled   = true
  auth_token                   = var.auth_token
  
  maintenance_window           = var.maintenance_window
  snapshot_retention_limit     = var.snapshot_retention_limit
  snapshot_window             = var.snapshot_window
  
  apply_immediately           = var.apply_immediately
  
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow.name
    destination_type = "cloudwatch-logs"
    log_format       = "text"
    log_type         = "slow-log"
  }

  tags = {
    Name        = "${var.environment}-${var.project_name}-redis"
    Environment = var.environment
    Project     = var.project_name
  }
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "redis_slow" {
  name              = "/aws/elasticache/redis/${var.environment}-${var.project_name}/slow-log"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.environment}-${var.project_name}-redis-slow-log"
    Environment = var.environment
    Project     = var.project_name
  }
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "redis_cpu_high" {
  alarm_name          = "${var.environment}-${var.project_name}-redis-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors redis cpu utilization"
  
  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.redis.id
  }

  alarm_actions = var.alarm_actions

  tags = {
    Name        = "${var.environment}-${var.project_name}-redis-cpu-alarm"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_metric_alarm" "redis_memory_high" {
  alarm_name          = "${var.environment}-${var.project_name}-redis-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors redis memory utilization"
  
  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.redis.id
  }

  alarm_actions = var.alarm_actions

  tags = {
    Name        = "${var.environment}-${var.project_name}-redis-memory-alarm"
    Environment = var.environment
    Project     = var.project_name
  }
}
