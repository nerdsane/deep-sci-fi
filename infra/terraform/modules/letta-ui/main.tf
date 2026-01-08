# Letta UI Module - Observability Dashboard

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

# ECR Repository for Letta UI
resource "aws_ecr_repository" "letta_ui" {
  name                 = "${var.project_name}/letta-ui"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-letta-ui-ecr"
  }
}

# Security Group for Letta UI ALB
resource "aws_security_group" "letta_ui_alb" {
  name        = "${var.project_name}-letta-ui-alb-sg-${var.environment}"
  description = "Security group for Letta UI ALB"
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
    Name = "${var.project_name}-letta-ui-alb-sg"
  }
}

# Security Group for Letta UI ECS Tasks
resource "aws_security_group" "letta_ui_ecs" {
  name        = "${var.project_name}-letta-ui-ecs-sg-${var.environment}"
  description = "Security group for Letta UI ECS tasks"
  vpc_id      = var.vpc_id

  ingress {
    description     = "HTTP from ALB"
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.letta_ui_alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-letta-ui-ecs-sg"
  }
}

# Application Load Balancer for Letta UI
resource "aws_lb" "letta_ui" {
  name               = "${var.project_name}-ui-alb-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.letta_ui_alb.id]
  subnets            = var.public_subnet_ids

  tags = {
    Name = "${var.project_name}-letta-ui-alb"
  }
}

# ALB Target Group
resource "aws_lb_target_group" "letta_ui" {
  name        = "${var.project_name}-ui-tg-${var.environment}"
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
    Name = "${var.project_name}-letta-ui-tg"
  }
}

# ALB Listener
resource "aws_lb_listener" "letta_ui" {
  load_balancer_arn = aws_lb.letta_ui.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.letta_ui.arn
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "letta_ui" {
  name              = "/ecs/${var.project_name}/letta-ui"
  retention_in_days = 30

  tags = {
    Name = "${var.project_name}-letta-ui-logs"
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "letta_ui" {
  family                   = "${var.project_name}-letta-ui"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name  = "letta-ui"
      image = "${aws_ecr_repository.letta_ui.repository_url}:latest"

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
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.letta_ui.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      essential = true
    }
  ])

  tags = {
    Name = "${var.project_name}-letta-ui-task"
  }
}

# ECS Service
resource "aws_ecs_service" "letta_ui" {
  name            = "${var.project_name}-letta-ui-service"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.letta_ui.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.letta_ui_ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.letta_ui.arn
    container_name   = "letta-ui"
    container_port   = 3000
  }

  depends_on = [aws_lb_listener.letta_ui]

  tags = {
    Name = "${var.project_name}-letta-ui-service"
  }
}

# Outputs
output "ecr_repository_url" {
  value = aws_ecr_repository.letta_ui.repository_url
}

output "alb_dns_name" {
  value = aws_lb.letta_ui.dns_name
}

output "ui_url" {
  value = "http://${aws_lb.letta_ui.dns_name}"
}
