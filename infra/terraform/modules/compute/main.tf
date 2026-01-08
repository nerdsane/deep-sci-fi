# Compute Module - ECS, ALB, ECR

variable "project_name" { type = string }
variable "environment" { type = string }
variable "aws_region" { type = string }
variable "vpc_id" { type = string }
variable "public_subnet_ids" { type = list(string) }
variable "private_subnet_ids" { type = list(string) }
variable "ecs_execution_role_arn" { type = string }
variable "ecs_task_role_arn" { type = string }
variable "db_host" { type = string }
variable "db_name" { type = string }
variable "db_username" { type = string }
variable "db_password_secret_arn" { type = string }
variable "anthropic_api_key_secret_arn" { type = string }
variable "openai_api_key_secret_arn" { type = string }
variable "google_api_key_secret_arn" { type = string }
variable "s3_assets_bucket" { type = string }
variable "cloudfront_domain" { type = string }
variable "ecs_cpu" { type = number }
variable "ecs_memory" { type = number }
variable "ecs_desired_count" { type = number }

# ECR Repository
resource "aws_ecr_repository" "letta" {
  name                 = "${var.project_name}/letta-server"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-letta-ecr"
  }
}

# ECR Lifecycle Policy - keep last 10 images
resource "aws_ecr_lifecycle_policy" "letta" {
  repository = aws_ecr_repository.letta.name

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

# Security Group for ALB
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-sg-${var.environment}"
  description = "Security group for Application Load Balancer"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS from anywhere"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-alb-sg"
  }
}

# Security Group for ECS Tasks
resource "aws_security_group" "ecs" {
  name        = "${var.project_name}-ecs-sg-${var.environment}"
  description = "Security group for ECS tasks"
  vpc_id      = var.vpc_id

  ingress {
    description     = "HTTP from ALB"
    from_port       = 8283
    to_port         = 8283
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-ecs-sg"
  }
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.project_name}-alb-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids

  enable_deletion_protection = false # Set to true for production

  tags = {
    Name = "${var.project_name}-alb"
  }
}

# ALB Target Group
resource "aws_lb_target_group" "letta" {
  name        = "${var.project_name}-letta-tg-${var.environment}"
  port        = 8283
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/v1/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 3
  }

  tags = {
    Name = "${var.project_name}-letta-tg"
  }
}

# ALB Listener
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.letta.arn
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "${var.project_name}-ecs-cluster"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "letta" {
  name              = "/ecs/${var.project_name}/letta-server"
  retention_in_days = 30

  tags = {
    Name = "${var.project_name}-letta-logs"
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "letta" {
  family                   = "${var.project_name}-letta"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.ecs_cpu
  memory                   = var.ecs_memory
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name  = "letta-server"
      image = "${aws_ecr_repository.letta.repository_url}:latest"

      portMappings = [
        {
          containerPort = 8283
          hostPort      = 8283
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "LETTA_PG_HOST", value = var.db_host },
        { name = "LETTA_PG_PORT", value = "5432" },
        { name = "LETTA_PG_DB", value = var.db_name },
        { name = "LETTA_PG_USER", value = var.db_username },
        { name = "LETTA_SERVER_PORT", value = "8283" },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "S3_ASSETS_BUCKET", value = var.s3_assets_bucket },
        { name = "CLOUDFRONT_DOMAIN", value = var.cloudfront_domain },
      ]

      secrets = [
        {
          name      = "LETTA_PG_PASSWORD"
          valueFrom = var.db_password_secret_arn
        },
        {
          name      = "ANTHROPIC_API_KEY"
          valueFrom = var.anthropic_api_key_secret_arn
        },
        {
          name      = "OPENAI_API_KEY"
          valueFrom = var.openai_api_key_secret_arn
        },
        {
          name      = "GOOGLE_API_KEY"
          valueFrom = var.google_api_key_secret_arn
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.letta.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      essential = true
    }
  ])

  tags = {
    Name = "${var.project_name}-letta-task"
  }
}

# ECS Service
resource "aws_ecs_service" "letta" {
  name            = "${var.project_name}-letta-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.letta.arn
  desired_count   = var.ecs_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.letta.arn
    container_name   = "letta-server"
    container_port   = 8283
  }

  depends_on = [aws_lb_listener.http]

  tags = {
    Name = "${var.project_name}-letta-service"
  }
}

# Outputs
output "ecr_repository_url" {
  value = aws_ecr_repository.letta.repository_url
}

output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "alb_arn" {
  value = aws_lb.main.arn
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecs_cluster_id" {
  value = aws_ecs_cluster.main.id
}

output "ecs_service_name" {
  value = aws_ecs_service.letta.name
}

output "ecs_security_group_id" {
  value = aws_security_group.ecs.id
}
