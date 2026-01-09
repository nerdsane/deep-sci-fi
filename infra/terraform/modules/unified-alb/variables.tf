# Deep Sci-Fi Unified ALB Module Variables

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment (prod, staging, dev)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for ALB"
  type        = list(string)
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS (optional)"
  type        = string
  default     = ""
}

variable "enable_deletion_protection" {
  description = "Enable ALB deletion protection"
  type        = bool
  default     = false
}

# Target Group ARNs (from respective service modules)
variable "letta_server_target_group_arn" {
  description = "Letta Server target group ARN"
  type        = string
}

variable "letta_ui_target_group_arn" {
  description = "Letta UI target group ARN"
  type        = string
}

variable "web_app_target_group_arn" {
  description = "Web App target group ARN"
  type        = string
}

variable "websocket_target_group_arn" {
  description = "WebSocket target group ARN"
  type        = string
}
