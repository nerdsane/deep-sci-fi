# AWS Architecture Guide: Avoiding Expensive NAT Gateway Costs

## The Problem You Hit (Jan 2026)

ECS tasks in **private subnets** have no public IP. To pull Docker images, they routed through NAT Gateway:

```
ECS Task (private subnet)
    → NAT Gateway ($0.045/hr + $0.045/GB)
    → Internet
    → Docker Hub / ECR

Result: $30/day just for Docker pulls + package installs
```

## The Solution: VPC Endpoints

VPC Endpoints let private resources access AWS services **directly** without NAT:

```
ECS Task (private subnet)
    → VPC Endpoint (free or ~$7/mo each)
    → ECR / S3 / CloudWatch

Result: ~$0/day for AWS service traffic
```

---

## Cost Comparison

| Architecture | Monthly Cost | Docker Pull Cost |
|--------------|--------------|------------------|
| Private Subnet + NAT Gateway | ~$32 + $0.045/GB | **EXPENSIVE** |
| Private Subnet + VPC Endpoints | ~$21-35 (fixed) | **FREE** |
| Public Subnet (no NAT) | ~$0 | **FREE** |

---

## Recommended Architecture for ECS

### Option A: Private Subnets + VPC Endpoints (Recommended for Production)

```
┌─────────────────────────────────────────────────────────────────┐
│                            VPC                                   │
│                                                                  │
│  ┌─────────────────────┐     ┌─────────────────────┐            │
│  │   PUBLIC SUBNET     │     │   PRIVATE SUBNET    │            │
│  │                     │     │                     │            │
│  │  ┌───────────────┐  │     │  ┌───────────────┐  │            │
│  │  │      ALB      │◄─┼─────┼──│   ECS Tasks   │  │            │
│  │  └───────────────┘  │     │  └───────┬───────┘  │            │
│  │                     │     │          │          │            │
│  │  ┌───────────────┐  │     │          ▼          │            │
│  │  │  NAT Gateway  │◄─┼─────┼── (external only)   │            │
│  │  │ (OPTIONAL)    │  │     │                     │            │
│  │  └───────────────┘  │     │  ┌───────────────┐  │            │
│  │                     │     │  │ VPC Endpoints │──┼──► ECR     │
│  └─────────────────────┘     │  │ (FREE traffic)│──┼──► S3      │
│                              │  │               │──┼──► Logs    │
│                              │  └───────────────┘  │            │
│                              └─────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

**Required VPC Endpoints:**
| Endpoint | Type | Cost | Purpose |
|----------|------|------|---------|
| `ecr.api` | Interface | ~$7/mo | ECR API calls |
| `ecr.dkr` | Interface | ~$7/mo | Docker pull |
| `s3` | Gateway | **FREE** | ECR image layers |
| `logs` | Interface | ~$7/mo | CloudWatch logs |
| `secretsmanager` | Interface | ~$7/mo | Secrets (optional) |

**Total: ~$21-28/mo fixed** (vs $30+/day with NAT data transfer)

**NAT Gateway:** Only needed if you pull from Docker Hub, PyPI, npm, or external APIs. If you use ECR exclusively, you can skip NAT entirely.

---

### Option B: Public Subnets (Simplest, Cheapest)

```
┌─────────────────────────────────────────────────────────────────┐
│                            VPC                                   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    PUBLIC SUBNET                         │    │
│  │                                                          │    │
│  │  ┌───────────────┐         ┌───────────────┐            │    │
│  │  │      ALB      │◄────────│   ECS Tasks   │            │    │
│  │  └───────────────┘         │ (public IP)   │────────────┼───►│ Internet
│  │                            └───────────────┘            │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

**Cost: $0 extra** - ECS tasks get public IPs and access internet directly.

**Trade-off:** Less "secure" (tasks are internet-accessible), but fine for dev/staging. Use security groups to restrict inbound traffic.

---

## Terraform Implementation

### Adding VPC Endpoints (add to `modules/networking/main.tf`)

```hcl
# S3 Gateway Endpoint (FREE)
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]

  tags = { Name = "${var.project_name}-s3-endpoint" }
}

# ECR API Endpoint
resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = { Name = "${var.project_name}-ecr-api-endpoint" }
}

# ECR Docker Endpoint
resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = { Name = "${var.project_name}-ecr-dkr-endpoint" }
}

# CloudWatch Logs Endpoint
resource "aws_vpc_endpoint" "logs" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.logs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = { Name = "${var.project_name}-logs-endpoint" }
}

# Security group for VPC endpoints
resource "aws_security_group" "vpc_endpoints" {
  name   = "${var.project_name}-vpc-endpoints-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  tags = { Name = "${var.project_name}-vpc-endpoints-sg" }
}
```

### Making NAT Gateway Optional

```hcl
variable "enable_nat_gateway" {
  description = "Enable NAT Gateway (only needed for external registries like Docker Hub, PyPI)"
  type        = bool
  default     = false  # OFF by default!
}

resource "aws_nat_gateway" "main" {
  count         = var.enable_nat_gateway ? 1 : 0
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id
  # ...
}
```

---

## Decision Flowchart

```
Do you need to pull from Docker Hub, PyPI, npm, or external APIs?
    │
    ├── YES → Enable NAT Gateway (but use VPC Endpoints for ECR/S3/Logs)
    │         Cost: ~$32/mo + ~$21/mo endpoints = ~$53/mo fixed
    │
    └── NO (ECR only) → VPC Endpoints only, NO NAT Gateway
                        Cost: ~$21/mo fixed
```

---

## Quick Reference: What Goes Where

| Traffic | Route | Cost |
|---------|-------|------|
| ECR (Docker pull) | VPC Endpoint | ~$7/mo fixed |
| S3 (ECR layers) | VPC Endpoint | FREE |
| CloudWatch Logs | VPC Endpoint | ~$7/mo fixed |
| Secrets Manager | VPC Endpoint | ~$7/mo fixed |
| Docker Hub | NAT Gateway | $0.045/GB |
| PyPI / npm | NAT Gateway | $0.045/GB |
| External APIs | NAT Gateway | $0.045/GB |

---

## Current Setup (Jan 2026)

You're using **EC2 in a public subnet** with Docker Compose:
- Cost: ~$38/month
- No NAT Gateway needed
- Direct internet access

When ready for ECS, use this guide to set up VPC Endpoints FIRST, then optionally add NAT Gateway only if needed.
