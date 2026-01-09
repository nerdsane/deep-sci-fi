# Deep Sci-Fi EC2 Module Variables

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

variable "public_subnet_id" {
  description = "Public subnet ID for EC2 instance"
  type        = string
}

variable "key_pair_name" {
  description = "EC2 key pair name for SSH access"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}

variable "volume_size" {
  description = "Root volume size in GB"
  type        = number
  default     = 40
}

variable "ssh_cidr_blocks" {
  description = "CIDR blocks allowed for SSH access"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Restrict in production
}

variable "github_repo" {
  description = "GitHub repository URL for the project"
  type        = string
  default     = "https://github.com/nerdsane/deep-sci-fi.git"
}

variable "s3_assets_bucket" {
  description = "S3 bucket name for assets"
  type        = string
}

variable "secrets_arns" {
  description = "List of Secrets Manager ARNs to access"
  type        = list(string)
  default     = []
}
