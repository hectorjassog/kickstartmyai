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

# RDS Instance
resource "aws_db_instance" "main" {
  identifier = "${var.name_prefix}-db"

  # Engine
  engine         = "postgres"
  engine_version = var.engine_version

  # Instance
  instance_class    = var.instance_class
  allocated_storage = var.allocated_storage
  storage_type      = "gp2"
  storage_encrypted = true

  # Database
  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  # Network
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  # Backup
  backup_retention_period = var.backup_retention_period
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  # Monitoring
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_enhanced_monitoring.arn

  # Other
  skip_final_snapshot = var.skip_final_snapshot
  deletion_protection = var.deletion_protection

  tags = var.tags
}

# IAM Role for Enhanced Monitoring
resource "aws_iam_role" "rds_enhanced_monitoring" {
  name = "${var.name_prefix}-rds-enhanced-monitoring"

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
  role       = aws_iam_role.rds_enhanced_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# Data sources
data "aws_vpc" "main" {
  id = var.vpc_id
}
