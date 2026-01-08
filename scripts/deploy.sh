#!/bin/bash
#
# Deep Sci-Fi AWS Deployment Script
#
# Usage:
#   ./scripts/deploy.sh <command>
#
# Commands:
#   prerequisites  - Check required tools are installed
#   init           - Initialize Terraform
#   plan           - Preview infrastructure changes
#   apply          - Create/update infrastructure
#   build-letta    - Build and push Letta Docker image to ECR
#   migrate-db     - Run Prisma database migrations
#   migrate-data   - Migrate worlds and assets from local to cloud
#   update-ecs     - Force ECS service to redeploy
#   full-deploy    - Run all deployment steps in order
#   destroy        - Tear down all infrastructure (DANGEROUS!)
#   outputs        - Show Terraform outputs
#
# Prerequisites:
#   - AWS CLI configured with appropriate credentials
#   - Terraform >= 1.5.0
#   - Docker
#   - Node.js and npm
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TERRAFORM_DIR="$PROJECT_ROOT/infra/terraform"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
  log_info "Checking prerequisites..."

  local missing=()

  # AWS CLI
  if ! command -v aws &> /dev/null; then
    missing+=("aws")
  else
    log_success "AWS CLI: $(aws --version | head -1)"
  fi

  # Terraform
  if ! command -v terraform &> /dev/null; then
    missing+=("terraform")
  else
    log_success "Terraform: $(terraform --version | head -1)"
  fi

  # Docker
  if ! command -v docker &> /dev/null; then
    missing+=("docker")
  else
    log_success "Docker: $(docker --version)"
  fi

  # Node.js
  if ! command -v node &> /dev/null; then
    missing+=("node")
  else
    log_success "Node.js: $(node --version)"
  fi

  # npm
  if ! command -v npm &> /dev/null; then
    missing+=("npm")
  else
    log_success "npm: $(npm --version)"
  fi

  # Check AWS credentials
  if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials not configured or invalid"
    missing+=("aws-credentials")
  else
    log_success "AWS credentials configured"
  fi

  if [ ${#missing[@]} -gt 0 ]; then
    log_error "Missing prerequisites: ${missing[*]}"
    exit 1
  fi

  log_success "All prerequisites met!"
}

# Check if tfvars exists
check_tfvars() {
  if [ ! -f "$TERRAFORM_DIR/terraform.tfvars" ]; then
    log_error "terraform.tfvars not found!"
    log_info "Copy terraform.tfvars.example to terraform.tfvars and fill in your values:"
    log_info "  cp $TERRAFORM_DIR/terraform.tfvars.example $TERRAFORM_DIR/terraform.tfvars"
    exit 1
  fi
}

# Initialize Terraform
terraform_init() {
  log_info "Initializing Terraform..."
  cd "$TERRAFORM_DIR"
  terraform init
  log_success "Terraform initialized"
}

# Plan Terraform changes
terraform_plan() {
  check_tfvars
  log_info "Planning Terraform changes..."
  cd "$TERRAFORM_DIR"
  terraform plan
}

# Apply Terraform changes
terraform_apply() {
  check_tfvars
  log_info "Applying Terraform changes..."
  cd "$TERRAFORM_DIR"
  terraform apply -auto-approve
  log_success "Infrastructure created/updated"
}

# Show Terraform outputs
terraform_outputs() {
  cd "$TERRAFORM_DIR"
  terraform output
}

# Get Terraform output value
get_output() {
  cd "$TERRAFORM_DIR"
  terraform output -raw "$1" 2>/dev/null || echo ""
}

# Build and push Letta Docker image
build_letta() {
  log_info "Building and pushing Letta Docker image..."

  # Get ECR repository URL
  ECR_REPO=$(get_output ecr_repository_url)
  if [ -z "$ECR_REPO" ]; then
    log_error "Could not get ECR repository URL from Terraform outputs"
    exit 1
  fi

  AWS_REGION=$(get_output aws_region)
  AWS_ACCOUNT_ID=$(echo "$ECR_REPO" | cut -d'.' -f1)

  log_info "ECR Repository: $ECR_REPO"

  # Login to ECR
  log_info "Logging in to ECR..."
  aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

  # Build Docker image
  log_info "Building Docker image..."
  cd "$PROJECT_ROOT/letta"
  docker build -t letta-server .

  # Tag and push
  log_info "Tagging and pushing image..."
  docker tag letta-server:latest "$ECR_REPO:latest"
  docker push "$ECR_REPO:latest"

  log_success "Letta image pushed to ECR"
}

# Run database migrations
migrate_db() {
  log_info "Running database migrations..."

  # Get database URL from Terraform outputs
  DATABASE_URL=$(get_output database_url)
  if [ -z "$DATABASE_URL" ]; then
    log_error "Could not get database URL from Terraform outputs"
    exit 1
  fi

  cd "$PROJECT_ROOT/apps/web"

  # Install dependencies if needed
  if [ ! -d "node_modules" ]; then
    log_info "Installing dependencies..."
    npm install
  fi

  # Generate Prisma client
  log_info "Generating Prisma client..."
  DATABASE_URL="$DATABASE_URL" npx prisma generate

  # Run migrations
  log_info "Running Prisma migrations..."
  DATABASE_URL="$DATABASE_URL" npx prisma migrate deploy

  log_success "Database migrations complete"
}

# Migrate data from local to cloud
migrate_data() {
  log_info "Migrating data from local to cloud..."

  # Get configuration from Terraform
  DATABASE_URL=$(get_output database_url)
  S3_BUCKET=$(get_output assets_bucket_name)
  AWS_REGION=$(get_output aws_region)
  CLOUDFRONT_DOMAIN=$(get_output cloudfront_domain)

  if [ -z "$DATABASE_URL" ] || [ -z "$S3_BUCKET" ]; then
    log_error "Could not get required outputs from Terraform"
    exit 1
  fi

  cd "$PROJECT_ROOT"

  # Install ts-node if needed
  if ! command -v ts-node &> /dev/null; then
    log_info "Installing ts-node..."
    npm install -g ts-node typescript @types/node
  fi

  # Run world migration
  log_info "Migrating worlds to database..."
  DATABASE_URL="$DATABASE_URL" npx ts-node scripts/migrate-worlds-to-db.ts

  # Run asset migration
  log_info "Migrating assets to S3..."
  DATABASE_URL="$DATABASE_URL" \
    AWS_S3_BUCKET="$S3_BUCKET" \
    AWS_REGION="$AWS_REGION" \
    CLOUDFRONT_DOMAIN="$CLOUDFRONT_DOMAIN" \
    npx ts-node scripts/migrate-assets-to-s3.ts

  log_success "Data migration complete"
}

# Update ECS service (force redeploy)
update_ecs() {
  log_info "Updating ECS service..."

  CLUSTER_NAME=$(get_output ecs_cluster_name)
  SERVICE_NAME=$(get_output ecs_service_name)

  if [ -z "$CLUSTER_NAME" ] || [ -z "$SERVICE_NAME" ]; then
    log_error "Could not get ECS cluster/service names from Terraform"
    exit 1
  fi

  log_info "Cluster: $CLUSTER_NAME"
  log_info "Service: $SERVICE_NAME"

  aws ecs update-service \
    --cluster "$CLUSTER_NAME" \
    --service "$SERVICE_NAME" \
    --force-new-deployment

  log_info "Waiting for service to stabilize..."
  aws ecs wait services-stable \
    --cluster "$CLUSTER_NAME" \
    --services "$SERVICE_NAME"

  log_success "ECS service updated and stable"
}

# Full deployment
full_deploy() {
  log_info "Starting full deployment..."

  check_prerequisites
  terraform_init
  terraform_apply
  build_letta
  migrate_db
  migrate_data
  update_ecs

  echo ""
  log_success "Deployment complete!"
  echo ""
  terraform_outputs
}

# Destroy infrastructure
terraform_destroy() {
  log_warning "This will destroy ALL infrastructure!"
  read -p "Are you sure? Type 'yes' to confirm: " confirm

  if [ "$confirm" != "yes" ]; then
    log_info "Aborted"
    exit 0
  fi

  cd "$TERRAFORM_DIR"
  terraform destroy
}

# Main command handler
case "${1:-}" in
  prerequisites)
    check_prerequisites
    ;;
  init)
    terraform_init
    ;;
  plan)
    terraform_plan
    ;;
  apply)
    terraform_apply
    ;;
  build-letta)
    build_letta
    ;;
  migrate-db)
    migrate_db
    ;;
  migrate-data)
    migrate_data
    ;;
  update-ecs)
    update_ecs
    ;;
  full-deploy)
    full_deploy
    ;;
  destroy)
    terraform_destroy
    ;;
  outputs)
    terraform_outputs
    ;;
  *)
    echo "Deep Sci-Fi AWS Deployment Script"
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  prerequisites  Check required tools are installed"
    echo "  init           Initialize Terraform"
    echo "  plan           Preview infrastructure changes"
    echo "  apply          Create/update infrastructure"
    echo "  build-letta    Build and push Letta Docker image to ECR"
    echo "  migrate-db     Run Prisma database migrations"
    echo "  migrate-data   Migrate worlds and assets from local to cloud"
    echo "  update-ecs     Force ECS service to redeploy"
    echo "  full-deploy    Run all deployment steps in order"
    echo "  destroy        Tear down all infrastructure (DANGEROUS!)"
    echo "  outputs        Show Terraform outputs"
    exit 1
    ;;
esac
