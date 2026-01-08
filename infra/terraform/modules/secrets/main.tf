# Secrets Module - AWS Secrets Manager

variable "project_name" { type = string }
variable "environment" { type = string }
variable "db_password" { type = string }
variable "anthropic_api_key" { type = string }
variable "openai_api_key" { type = string }
variable "google_api_key" { type = string }

# Database Password
resource "aws_secretsmanager_secret" "db_password" {
  name                    = "${var.project_name}/${var.environment}/db-password"
  recovery_window_in_days = 0 # Allow immediate deletion for dev

  tags = {
    Name = "${var.project_name}-db-password"
  }
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = var.db_password
}

# Anthropic API Key
resource "aws_secretsmanager_secret" "anthropic_api_key" {
  name                    = "${var.project_name}/${var.environment}/anthropic-api-key"
  recovery_window_in_days = 0

  tags = {
    Name = "${var.project_name}-anthropic-api-key"
  }
}

resource "aws_secretsmanager_secret_version" "anthropic_api_key" {
  secret_id     = aws_secretsmanager_secret.anthropic_api_key.id
  secret_string = var.anthropic_api_key
}

# OpenAI API Key (optional)
resource "aws_secretsmanager_secret" "openai_api_key" {
  name                    = "${var.project_name}/${var.environment}/openai-api-key"
  recovery_window_in_days = 0

  tags = {
    Name = "${var.project_name}-openai-api-key"
  }
}

resource "aws_secretsmanager_secret_version" "openai_api_key" {
  secret_id     = aws_secretsmanager_secret.openai_api_key.id
  secret_string = var.openai_api_key != "" ? var.openai_api_key : "not-configured"
}

# Google API Key (optional)
resource "aws_secretsmanager_secret" "google_api_key" {
  name                    = "${var.project_name}/${var.environment}/google-api-key"
  recovery_window_in_days = 0

  tags = {
    Name = "${var.project_name}-google-api-key"
  }
}

resource "aws_secretsmanager_secret_version" "google_api_key" {
  secret_id     = aws_secretsmanager_secret.google_api_key.id
  secret_string = var.google_api_key != "" ? var.google_api_key : "not-configured"
}

# Outputs
output "db_password_secret_arn" {
  value = aws_secretsmanager_secret.db_password.arn
}

output "anthropic_api_key_secret_arn" {
  value = aws_secretsmanager_secret.anthropic_api_key.arn
}

output "openai_api_key_secret_arn" {
  value = aws_secretsmanager_secret.openai_api_key.arn
}

output "google_api_key_secret_arn" {
  value = aws_secretsmanager_secret.google_api_key.arn
}

output "secret_arns" {
  value = [
    aws_secretsmanager_secret.db_password.arn,
    aws_secretsmanager_secret.anthropic_api_key.arn,
    aws_secretsmanager_secret.openai_api_key.arn,
    aws_secretsmanager_secret.google_api_key.arn,
  ]
}
