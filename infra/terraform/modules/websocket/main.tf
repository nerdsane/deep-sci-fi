# Deep Sci-Fi WebSocket Server Module (Future ECS)
# WebSocket server for real-time communication
# NOTE: This module is for future ECS deployment, not currently used

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ECR Repository for WebSocket server
resource "aws_ecr_repository" "websocket" {
  name                 = "${var.project_name}/websocket"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "${var.project_name}-websocket"
    Environment = var.environment
  }
}

# ECR Lifecycle Policy
resource "aws_ecr_lifecycle_policy" "websocket" {
  repository = aws_ecr_repository.websocket.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "websocket" {
  name              = "/ecs/${var.project_name}/websocket"
  retention_in_days = 30

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Security Group for WebSocket ECS tasks
resource "aws_security_group" "websocket" {
  name        = "${var.project_name}-websocket-sg-${var.environment}"
  description = "Security group for WebSocket ECS tasks"
  vpc_id      = var.vpc_id

  ingress {
    description     = "WebSocket from ALB"
    from_port       = 8284
    to_port         = 8284
    protocol        = "tcp"
    security_groups = [var.alb_security_group_id]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-websocket-sg"
    Environment = var.environment
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "websocket" {
  family                   = "${var.project_name}-websocket"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name      = "websocket"
      image     = "${aws_ecr_repository.websocket.repository_url}:latest"
      essential = true

      portMappings = [
        {
          containerPort = 8284
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "WS_PORT"
          value = "8284"
        },
        {
          name  = "NODE_ENV"
          value = "production"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.websocket.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8284/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = {
    Name        = "${var.project_name}-websocket-task"
    Environment = var.environment
  }
}

# ALB Target Group for WebSocket
resource "aws_lb_target_group" "websocket" {
  name        = "${var.project_name}-ws-tg-${var.environment}"
  port        = 8284
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/health"
    port                = "traffic-port"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }

  # Sticky sessions for WebSocket connections
  stickiness {
    type            = "lb_cookie"
    cookie_duration = 86400
    enabled         = true
  }

  tags = {
    Name        = "${var.project_name}-websocket-tg"
    Environment = var.environment
  }
}

# ECS Service
resource "aws_ecs_service" "websocket" {
  name            = "${var.project_name}-websocket-service"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.websocket.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.websocket.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.websocket.arn
    container_name   = "websocket"
    container_port   = 8284
  }

  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 50
  }

  tags = {
    Name        = "${var.project_name}-websocket-service"
    Environment = var.environment
  }

  lifecycle {
    ignore_changes = [desired_count]
  }
}
