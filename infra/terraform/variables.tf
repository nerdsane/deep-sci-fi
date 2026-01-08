# Deep Sci-Fi AWS Infrastructure Variables

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (prod, staging, dev)"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "deep-sci-fi"
}

# Database
variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

# ECS
variable "ecs_cpu" {
  description = "ECS task CPU units"
  type        = number
  default     = 1024 # 1 vCPU
}

variable "ecs_memory" {
  description = "ECS task memory (MB)"
  type        = number
  default     = 2048 # 2 GB
}

variable "ecs_desired_count" {
  description = "Number of ECS tasks"
  type        = number
  default     = 1
}

# API Keys (sensitive)
variable "anthropic_api_key" {
  description = "Anthropic API key for Claude"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key (optional)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "google_api_key" {
  description = "Google API key for Gemini (optional)"
  type        = string
  sensitive   = true
  default     = ""
}
