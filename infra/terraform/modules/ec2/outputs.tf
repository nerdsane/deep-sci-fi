# Deep Sci-Fi EC2 Module Outputs

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.app.id
}

output "public_ip" {
  description = "Elastic IP address"
  value       = aws_eip.app.public_ip
}

output "public_dns" {
  description = "Public DNS name"
  value       = aws_eip.app.public_dns
}

output "private_ip" {
  description = "Private IP address"
  value       = aws_instance.app.private_ip
}

output "security_group_id" {
  description = "Security group ID"
  value       = aws_security_group.app.id
}

output "iam_role_arn" {
  description = "IAM role ARN"
  value       = aws_iam_role.app.arn
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i ~/.ssh/${var.key_pair_name}.pem ec2-user@${aws_eip.app.public_ip}"
}

output "service_urls" {
  description = "Service URLs (direct access)"
  value = {
    letta_server = "http://${aws_eip.app.public_ip}:8283"
    letta_ui     = "http://${aws_eip.app.public_ip}:4000"
    web_app      = "http://${aws_eip.app.public_ip}:3000"
    websocket    = "ws://${aws_eip.app.public_ip}:8284"
  }
}
