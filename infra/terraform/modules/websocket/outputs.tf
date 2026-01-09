# Deep Sci-Fi WebSocket Module Outputs

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.websocket.repository_url
}

output "security_group_id" {
  description = "Security group ID"
  value       = aws_security_group.websocket.id
}

output "target_group_arn" {
  description = "Target group ARN"
  value       = aws_lb_target_group.websocket.arn
}

output "service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.websocket.name
}
