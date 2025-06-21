# ECS Module - Container orchestration for {{cookiecutter.project_name}}

resource "aws_ecs_cluster" "main" {
  name = "${var.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = var.tags
}

# Task Definition
resource "aws_ecs_task_definition" "app" {
  family                   = "${var.name_prefix}-app"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn           = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "app"
      image = var.app_image
      
      portMappings = [
        {
          containerPort = var.app_port
          protocol      = "tcp"
        }
      ]
      
      environment = [
        for key, value in var.environment_variables : {
          name  = key
          value = value
        }
      ]
      
      secrets = [
        for key, value in var.secrets : {
          name      = key
          valueFrom = value
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.app.name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = "ecs"
        }
      }
      
      healthCheck = {
        command = ["CMD-SHELL", "curl -f http://localhost:${var.app_port}/health || exit 1"]
        interval = 30
        timeout = 5
        retries = 3
        startPeriod = 60
      }
    }
  ])

  tags = var.tags
}

# ECS Service with Cost-Effective Auto Scaling
resource "aws_ecs_service" "app" {
  name            = "${var.name_prefix}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  # Enable auto scaling
  enable_execute_command = false  # Disabled for cost optimization

  network_configuration {
    security_groups  = var.security_group_ids
    subnets          = var.subnet_ids
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "app"
    container_port   = var.app_port
  }

  # Deployment configuration for cost optimization
  deployment_configuration {
    maximum_percent         = 150  # Reduced from default 200
    minimum_healthy_percent = 50   # Allow some downtime for cost savings
    
    deployment_circuit_breaker {
      enable   = true
      rollback = true
    }
  }

  # Cost optimization: Don't maintain service during low usage
  lifecycle {
    ignore_changes = [desired_count]  # Allow auto scaling to manage
  }

  depends_on = [var.target_group_arn]

  tags = merge(var.tags, {
    AutoScaling = "enabled"
    CostOptimized = "true"
  })
}

# Auto Scaling Target
resource "aws_appautoscaling_target" "ecs_target" {
  count              = var.enable_auto_scaling ? 1 : 0
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.app.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-autoscaling-target"
  })
}

# CPU-based Auto Scaling Policy (Scale Up)
resource "aws_appautoscaling_policy" "scale_up_cpu" {
  count              = var.enable_auto_scaling ? 1 : 0
  name               = "${var.name_prefix}-scale-up-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target[0].resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0  # Scale up when CPU > 70%
    scale_out_cooldown = 300   # 5 minutes cooldown
    scale_in_cooldown  = 300   # 5 minutes cooldown
  }
}

# Memory-based Auto Scaling Policy (Scale Up)
resource "aws_appautoscaling_policy" "scale_up_memory" {
  count              = var.enable_auto_scaling ? 1 : 0
  name               = "${var.name_prefix}-scale-up-memory"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target[0].resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value       = 80.0  # Scale up when Memory > 80%
    scale_out_cooldown = 300   # 5 minutes cooldown
    scale_in_cooldown  = 600   # 10 minutes cooldown (longer for cost optimization)
  }
}

# Cost Optimization: Scheduled Scaling (Scale down during low usage hours)
resource "aws_appautoscaling_scheduled_action" "scale_down_night" {
  count              = var.enable_scheduled_scaling ? 1 : 0
  name               = "${var.name_prefix}-scale-down-night"
  service_namespace  = aws_appautoscaling_target.ecs_target[0].service_namespace
  resource_id        = aws_appautoscaling_target.ecs_target[0].resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target[0].scalable_dimension

  # Scale down to minimum during night hours (UTC)
  schedule = "cron(0 2 * * ? *)"  # 2 AM UTC daily

  scalable_target_action {
    min_capacity = 1
    max_capacity = var.min_capacity
  }
}

resource "aws_appautoscaling_scheduled_action" "scale_up_morning" {
  count              = var.enable_scheduled_scaling ? 1 : 0
  name               = "${var.name_prefix}-scale-up-morning"
  service_namespace  = aws_appautoscaling_target.ecs_target[0].service_namespace
  resource_id        = aws_appautoscaling_target.ecs_target[0].resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target[0].scalable_dimension

  # Scale up during business hours (UTC)
  schedule = "cron(0 8 * * ? *)"  # 8 AM UTC daily

  scalable_target_action {
    min_capacity = var.min_capacity
    max_capacity = var.max_capacity
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${var.name_prefix}"
  retention_in_days = 7

  tags = var.tags
}

# Data sources
data "aws_region" "current" {}

# IAM Roles
resource "aws_iam_role" "ecs_execution_role" {
  name = "${var.name_prefix}-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task_role" {
  name = "${var.name_prefix}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# Task role policy for accessing AWS services
resource "aws_iam_role_policy" "ecs_task_policy" {
  name = "${var.name_prefix}-ecs-task-policy"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = "*"
      }
    ]
  })
}
