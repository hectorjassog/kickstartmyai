# Database Module - RDS PostgreSQL

# Security Group for RDS
resource "aws_security_group" "rds" {
  name_prefix = "${var.name_prefix}-rds-"
  vpc_id      = var.vpc_id

  ingress {
    description = "PostgreSQL"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-rds-sg"
  })
}

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${var.name_prefix}-db-subnet-group"
  subnet_ids = var.subnet_ids

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-db-subnet-group"
  })
}

# RDS Instance - Cost Optimized
resource "aws_db_instance" "main" {
  identifier = "${var.name_prefix}-db"

  # Engine
  engine         = "postgres"
  engine_version = var.engine_version

  # Instance - Cost optimized
  instance_class    = var.instance_class
  allocated_storage = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage  # Enable storage autoscaling
  storage_type      = var.storage_type  # gp3 is more cost effective
  storage_encrypted = true

  # Performance Insights - Conditionally enabled
  performance_insights_enabled          = var.enable_performance_insights
  performance_insights_retention_period = var.enable_performance_insights ? 7 : null  # Free tier

  # Database
  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  # Network
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  # Backup - Cost optimized
  backup_retention_period   = var.backup_retention_period  # Reduced to 7 days
  backup_window            = "03:00-04:00"  # Off-peak hours
  maintenance_window       = "sun:04:00-sun:05:00"  # Off-peak hours
  copy_tags_to_snapshot    = true
  delete_automated_backups = true  # Delete automated backups when instance is deleted

  # Monitoring - Conditionally enabled for cost savings
  monitoring_interval = var.enable_enhanced_monitoring ? 60 : 0
  monitoring_role_arn = var.enable_enhanced_monitoring ? aws_iam_role.rds_enhanced_monitoring[0].arn : null

  # Cost optimization features
  auto_minor_version_upgrade = true  # Automatic minor version upgrades
  apply_immediately         = false  # Apply changes during maintenance window

  # Other
  skip_final_snapshot = var.skip_final_snapshot
  deletion_protection = var.deletion_protection

  tags = merge(var.tags, {
    CostOptimized = "true"
    BackupRetention = var.backup_retention_period
  })
}

# IAM Role for Enhanced Monitoring - Only created if monitoring is enabled
resource "aws_iam_role" "rds_enhanced_monitoring" {
  count = var.enable_enhanced_monitoring ? 1 : 0
  name  = "${var.name_prefix}-rds-enhanced-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "rds_enhanced_monitoring" {
  count      = var.enable_enhanced_monitoring ? 1 : 0
  role       = aws_iam_role.rds_enhanced_monitoring[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# Data sources
data "aws_vpc" "main" {
  id = var.vpc_id
}
