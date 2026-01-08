# Deep Sci-Fi AWS Architecture

## Overview

Full AWS deployment for Deep Sci-Fi with all components hosted on AWS infrastructure.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS CLOUD                                       │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         Route 53 (DNS)                               │    │
│  │                    deepscifi.app → CloudFront                        │    │
│  └────────────────────────────┬────────────────────────────────────────┘    │
│                               │                                              │
│  ┌────────────────────────────▼────────────────────────────────────────┐    │
│  │                     CloudFront (CDN)                                 │    │
│  │              • SSL termination                                       │    │
│  │              • Global edge caching                                   │    │
│  │              • Routes: /* → S3, /api/* → ALB                        │    │
│  └───────────┬─────────────────────────────────┬───────────────────────┘    │
│              │                                 │                             │
│              ▼                                 ▼                             │
│  ┌───────────────────────┐       ┌───────────────────────────────────┐     │
│  │    S3 Bucket          │       │    Application Load Balancer      │     │
│  │    (Static Assets)    │       │                                   │     │
│  │                       │       │    • /api/* → ECS Service         │     │
│  │  • Next.js build      │       │    • Health checks                │     │
│  │  • World/story assets │       │                                   │     │
│  │  • Cover images       │       └─────────────┬─────────────────────┘     │
│  └───────────────────────┘                     │                            │
│                                                │                            │
│  ┌─────────────────────────────────────────────▼────────────────────────┐  │
│  │                         VPC (10.0.0.0/16)                             │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────┐     │  │
│  │  │                    Private Subnets                           │     │  │
│  │  │                                                              │     │  │
│  │  │  ┌─────────────────────┐    ┌─────────────────────────┐     │     │  │
│  │  │  │   ECS Fargate       │    │   RDS PostgreSQL        │     │     │  │
│  │  │  │   (Letta Server)    │    │   (pgvector)            │     │     │  │
│  │  │  │                     │    │                         │     │     │  │
│  │  │  │  • letta-server     │◀──▶│  • Worlds table         │     │     │  │
│  │  │  │  • Port 8283        │    │  • Stories table        │     │     │  │
│  │  │  │  • Auto-scaling     │    │  • Users table          │     │     │  │
│  │  │  │                     │    │  • Agents table         │     │     │  │
│  │  │  └─────────────────────┘    └─────────────────────────┘     │     │  │
│  │  │                                                              │     │  │
│  │  └──────────────────────────────────────────────────────────────┘     │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────┐     │  │
│  │  │                    Public Subnets                            │     │  │
│  │  │                                                              │     │  │
│  │  │  • NAT Gateway (outbound internet for ECS)                  │     │  │
│  │  │  • ALB endpoints                                            │     │  │
│  │  └──────────────────────────────────────────────────────────────┘     │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Supporting Services                             │    │
│  │                                                                      │    │
│  │  • ECR (Docker images)      • Secrets Manager (API keys)            │    │
│  │  • CloudWatch (Logs)        • IAM (Permissions)                     │    │
│  │  • ElastiCache Redis        • Certificate Manager (SSL)             │    │
│  │    (optional, for caching)                                          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Frontend (Next.js)

**Option A: S3 + CloudFront (Static Export)** - Recommended for simplicity
- Export Next.js as static site (`next export`)
- Host on S3 with CloudFront CDN
- API routes run on separate backend

**Option B: AWS Amplify** - Alternative
- Managed Next.js hosting
- Automatic CI/CD from GitHub
- Server-side rendering support

**Chosen: Option A** (S3 + CloudFront) for maximum control and cost efficiency.

### 2. Backend (Letta Server)

**ECS Fargate**
- Serverless container hosting (no EC2 management)
- Auto-scaling based on CPU/memory
- Uses existing Letta Dockerfile
- Connects to RDS PostgreSQL

**Container Registry (ECR)**
- Store Letta Docker images
- Versioned deployments
- Integrated with ECS

### 3. Database

**RDS PostgreSQL with pgvector**
- db.t3.medium (2 vCPU, 4GB RAM) for start
- pgvector extension for embeddings
- Multi-AZ for production reliability
- Automated backups

**Tables:**
- `users` - User accounts
- `worlds` - World data (JSON)
- `stories` - Story data (JSON)
- `agents` - Letta agent references
- `assets` - Asset metadata (files in S3)

### 4. Storage (S3)

**Buckets:**
- `deepscifi-frontend` - Next.js static build
- `deepscifi-assets` - World/story images and media

**Access:**
- Frontend bucket: Public read via CloudFront
- Assets bucket: Presigned URLs for uploads, public read for serving

### 5. Networking

**VPC Configuration:**
- CIDR: 10.0.0.0/16
- Public subnets: 10.0.1.0/24, 10.0.2.0/24 (2 AZs)
- Private subnets: 10.0.3.0/24, 10.0.4.0/24 (2 AZs)
- NAT Gateway for outbound internet access
- Security groups for fine-grained access control

### 6. Security

**Secrets Manager:**
- ANTHROPIC_API_KEY
- OPENAI_API_KEY
- DATABASE_URL
- JWT_SECRET

**IAM Roles:**
- ECS Task Role (S3 access, Secrets access)
- ECS Execution Role (ECR pull, CloudWatch logs)

---

## Data Flow

### User Request Flow
```
User Browser
    │
    ▼
CloudFront (deepscifi.app)
    │
    ├── Static files (/, /worlds, etc.) → S3 Frontend Bucket
    │
    └── API calls (/api/*) → ALB → ECS (Letta Server)
                                        │
                                        ├── Agent operations → RDS PostgreSQL
                                        └── Asset operations → S3 Assets Bucket
```

### Chat Message Flow
```
User types message in Chat Sidebar
    │
    ▼
POST /api/chat { message, worldId? }
    │
    ▼
ALB → ECS (Letta Server)
    │
    ▼
LettaOrchestrator.sendMessage()
    │
    ├── No worldId: Route to User Agent (orchestrator)
    │   └── Can generate world drafts, list worlds
    │
    └── With worldId: Route to World Agent
        └── Can manage world, write stories
    │
    ▼
Response streamed back to browser
```

---

## Cost Estimate (Monthly)

| Service | Spec | Est. Cost |
|---------|------|-----------|
| ECS Fargate | 0.5 vCPU, 1GB, always-on | $15-25 |
| RDS PostgreSQL | db.t3.micro, 20GB | $15-20 |
| S3 | 10GB storage, moderate traffic | $1-5 |
| CloudFront | 100GB transfer | $10-15 |
| NAT Gateway | Minimal traffic | $5-10 |
| Secrets Manager | 5 secrets | $2 |
| **Total** | | **~$50-80/month** |

*Can be reduced with Reserved Instances or Savings Plans*

---

## Deployment Strategy

### Phase 1: Infrastructure Setup
1. Create VPC with subnets
2. Set up RDS PostgreSQL
3. Create S3 buckets
4. Configure ECR repository
5. Set up Secrets Manager

### Phase 2: Backend Deployment
1. Build and push Letta Docker image to ECR
2. Create ECS cluster and service
3. Configure ALB with health checks
4. Test Letta API endpoints

### Phase 3: Frontend Deployment
1. Update Next.js for cloud data sources
2. Build static export
3. Deploy to S3
4. Configure CloudFront distribution

### Phase 4: DNS & SSL
1. Create Route 53 hosted zone
2. Request ACM certificate
3. Configure custom domain

---

## Files to Create

```
infra/aws/
├── ARCHITECTURE.md          (this file)
├── terraform/               (Infrastructure as Code)
│   ├── main.tf
│   ├── vpc.tf
│   ├── rds.tf
│   ├── ecs.tf
│   ├── s3.tf
│   ├── cloudfront.tf
│   └── variables.tf
├── docker/
│   └── Dockerfile.web       (Next.js container if needed)
└── scripts/
    ├── deploy-backend.sh
    └── deploy-frontend.sh
```

---

## Environment Variables

### Letta Server (ECS)
```
LETTA_PG_URI=postgresql://user:pass@rds-endpoint:5432/letta
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
LETTA_SERVER_PORT=8283
AWS_S3_BUCKET=deepscifi-assets
AWS_REGION=us-west-2
```

### Next.js Frontend
```
NEXT_PUBLIC_API_URL=https://api.deepscifi.app
NEXT_PUBLIC_ASSETS_URL=https://assets.deepscifi.app
```

---

## Next Steps

1. **Do you have an AWS account ready?**
2. **Do you want to use Terraform (IaC) or AWS Console for initial setup?**
3. **What domain will you use?** (e.g., deepscifi.app)
4. **Which AWS region?** (recommend us-west-2 or us-east-1)
