# Test AI Project - Production Environment

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    # Configure your S3 backend here
    # bucket = "test-ai-project-terraform-state"
    # key    = "prod/terraform.tfstate"
    # region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "Test AI Project"
      Environment = "prod"
      ManagedBy   = "terraform"
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

# Local values
locals {
  name_prefix = "test-ai-project-prod"
  azs         = slice(data.aws_availability_zones.available.names, 0, 2)
}

# Networking
module "networking" {
  source = "../../modules/networking"
  
  name_prefix        = local.name_prefix
  vpc_cidr          = var.vpc_cidr
  availability_zones = local.azs
  
  tags = {
    Environment = "prod"
  }
}

# Database
module "database" {
  source = "../../modules/database"
  
  name_prefix = local.name_prefix
  vpc_id      = module.networking.vpc_id
  subnet_ids  = module.networking.private_subnet_ids
  
  db_name     = var.db_name
  db_username = var.db_username
  db_password = var.db_password
  
  instance_class    = var.db_instance_class
  allocated_storage = var.db_allocated_storage
  
  tags = {
    Environment = "prod"
  }
}

# Redis
module "redis" {
  source = "../../modules/redis"
  
  name_prefix = local.name_prefix
  vpc_id      = module.networking.vpc_id
  subnet_ids  = module.networking.private_subnet_ids
  
  node_type = var.redis_node_type
  
  tags = {
    Environment = "prod"
  }
}

# Application Load Balancer
module "alb" {
  source = "../../modules/alb"
  
  name_prefix = local.name_prefix
  vpc_id      = module.networking.vpc_id
  subnet_ids  = module.networking.public_subnet_ids
  
  certificate_arn = var.certificate_arn
  
  tags = {
    Environment = "prod"
  }
}

# ECS Cluster
module "ecs" {
  source = "../../modules/ecs"
  
  name_prefix = local.name_prefix
  vpc_id      = module.networking.vpc_id
  subnet_ids  = module.networking.private_subnet_ids
  
  # ALB configuration
  target_group_arn = module.alb.target_group_arn
  security_group_ids = [module.alb.ecs_security_group_id]
  
  # Application configuration
  app_image                = var.app_image
  app_port                = var.app_port
  desired_count           = var.desired_count
  cpu                     = var.cpu
  memory                  = var.memory
  
  # Environment variables
  environment_variables = {
    DATABASE_URL = "postgresql://${var.db_username}:${var.db_password}@${module.database.endpoint}:5432/${var.db_name}"
    REDIS_URL    = "redis://${module.redis.endpoint}:6379/0"
    AWS_REGION   = var.aws_region
  }
  
  # Secrets
  secrets = {
    SECRET_KEY      = var.secret_key_arn
    OPENAI_API_KEY  = var.openai_api_key_arn
    ANTHROPIC_API_KEY = var.anthropic_api_key_arn
    GEMINI_API_KEY = var.gemini_api_key_arn
  }
  
  tags = {
    Environment = "prod"
  }
}

# CloudWatch
module "cloudwatch" {
  source = "../../modules/cloudwatch"
  
  name_prefix = local.name_prefix
  
  # ECS cluster name for monitoring
  ecs_cluster_name = module.ecs.cluster_name
  ecs_service_name = module.ecs.service_name
  
  tags = {
    Environment = "prod"
  }
}

# Secrets Manager
module "secrets" {
  source = "../../modules/secrets"
  
  name_prefix = local.name_prefix
  
  secrets = {
    secret_key        = var.secret_key
    openai_api_key    = var.openai_api_key
    anthropic_api_key = var.anthropic_api_key
    gemini_api_key    = var.gemini_api_key
  }
  
  tags = {
    Environment = "prod"
  }
}
