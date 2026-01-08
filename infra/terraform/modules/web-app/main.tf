# Web App Module - Next.js Chat + Canvas UI

variable "project_name" { type = string }
variable "environment" { type = string }
variable "aws_region" { type = string }
variable "vpc_id" { type = string }
variable "public_subnet_ids" { type = list(string) }
variable "private_subnet_ids" { type = list(string) }
variable "ecs_cluster_id" { type = string }
variable "ecs_execution_role_arn" { type = string }
variable "ecs_task_role_arn" { type = string }
variable "letta_api_url" { type = string }
variable "cloudfront_domain" { type = string }

# ECR Repository for Web App
resource "aws_ecr_repository" "web_app" {
  name                 = "${var.project_name}/web-app"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-web-app-ecr"
  }
}

# Security Group for Web App ALB
resource "aws_security_group" "web_app_alb" {
  name        = "${var.project_name}-web-app-alb-sg-${var.environment}"
  description = "Security group for Web App ALB"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
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
    Name = "${var.project_name}-web-app-alb-sg"
  }
}

# Security Group for Web App ECS Tasks
resource "aws_security_group" "web_app_ecs" {
  name        = "${var.project_name}-web-app-ecs-sg-${var.environment}"
  description = "Security group for Web App ECS tasks"
  vpc_id      = var.vpc_id

  ingress {
    description     = "HTTP from ALB"
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.web_app_alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-web-app-ecs-sg"
  }
}

# Application Load Balancer for Web App
resource "aws_lb" "web_app" {
  name               = "${var.project_name}-web-alb-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.web_app_alb.id]
  subnets            = var.public_subnet_ids

  tags = {
    Name = "${var.project_name}-web-app-alb"
  }
}

# ALB Target Group
resource "aws_lb_target_group" "web_app" {
  name        = "${var.project_name}-web-tg-${var.environment}"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 3
  }

  tags = {
    Name = "${var.project_name}-web-app-tg"
  }
}

# ALB Listener
resource "aws_lb_listener" "web_app" {
  load_balancer_arn = aws_lb.web_app.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web_app.arn
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "web_app" {
  name              = "/ecs/${var.project_name}/web-app"
  retention_in_days = 30

  tags = {
    Name = "${var.project_name}-web-app-logs"
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "web_app" {
  family                   = "${var.project_name}-web-app"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name  = "web-app"
      image = "${aws_ecr_repository.web_app.repository_url}:latest"

      portMappings = [
        {
          containerPort = 3000
          hostPort      = 3000
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "PORT", value = "3000" },
        { name = "LETTA_BASE_URL", value = var.letta_api_url },
        { name = "CLOUDFRONT_DOMAIN", value = var.cloudfront_domain },
        { name = "NODE_ENV", value = "production" },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.web_app.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      essential = true
    }
  ])

  tags = {
    Name = "${var.project_name}-web-app-task"
  }
}

# ECS Service
resource "aws_ecs_service" "web_app" {
  name            = "${var.project_name}-web-app-service"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.web_app.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.web_app_ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.web_app.arn
    container_name   = "web-app"
    container_port   = 3000
  }

  depends_on = [aws_lb_listener.web_app]

  tags = {
    Name = "${var.project_name}-web-app-service"
  }
}

# Outputs
output "ecr_repository_url" {
  value = aws_ecr_repository.web_app.repository_url
}

output "alb_dns_name" {
  value = aws_lb.web_app.dns_name
}

output "web_app_url" {
  value = "http://${aws_lb.web_app.dns_name}"
}
