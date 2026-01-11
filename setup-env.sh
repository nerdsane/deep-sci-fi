#!/bin/bash

#
# DSF Agent - Environment Setup Script
# Distributes environment variables from root .env to submodules
#

set -e

# Colors for output
CYAN='\033[38;2;0;255;204m'
PURPLE='\033[38;2;170;0;255m'
RED='\033[38;2;255;0;68m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_ENV="$SCRIPT_DIR/.env"
LETTA_ENV="$SCRIPT_DIR/letta/.env"
LETTA_CODE_ENV="$SCRIPT_DIR/letta-code/.env"
WEB_APP_ENV="$SCRIPT_DIR/apps/web/.env"

# Check if root .env exists
if [ ! -f "$ROOT_ENV" ]; then
    echo -e "${RED}✗ Root .env file not found at $ROOT_ENV${NC}"
    echo -e "${PURPLE}Please copy .env.example to .env and fill in your values${NC}"
    exit 1
fi

echo -e "${PURPLE}Setting up environment files from root .env...${NC}"

# Function to extract value from .env file (strips surrounding quotes)
get_env_value() {
    local key=$1
    local file=$2
    local value
    value=$(grep "^${key}=" "$file" 2>/dev/null | cut -d '=' -f2- || echo "")
    # Strip surrounding quotes (both single and double)
    value="${value#\"}"
    value="${value%\"}"
    value="${value#\'}"
    value="${value%\'}"
    echo "$value"
}

# Extract all values from root .env
ANTHROPIC_API_KEY=$(get_env_value "ANTHROPIC_API_KEY" "$ROOT_ENV")
OPENAI_API_KEY=$(get_env_value "OPENAI_API_KEY" "$ROOT_ENV")
GOOGLE_API_KEY=$(get_env_value "GOOGLE_API_KEY" "$ROOT_ENV")
GEMINI_API_KEY=$(get_env_value "GEMINI_API_KEY" "$ROOT_ENV")
PERPLEXITY_API_KEY=$(get_env_value "PERPLEXITY_API_KEY" "$ROOT_ENV")
PERPLEXITY_TIMEOUT_MS=$(get_env_value "PERPLEXITY_TIMEOUT_MS" "$ROOT_ENV")
LETTA_API_KEY=$(get_env_value "LETTA_API_KEY" "$ROOT_ENV")
LETTA_BASE_URL=$(get_env_value "LETTA_BASE_URL" "$ROOT_ENV")
NOTION_TOKEN=$(get_env_value "NOTION_TOKEN" "$ROOT_ENV")
NOTION_DATABASE_ID=$(get_env_value "NOTION_DATABASE_ID" "$ROOT_ENV")
OLLAMA_BASE_URL=$(get_env_value "OLLAMA_BASE_URL" "$ROOT_ENV")
VLLM_API_BASE=$(get_env_value "VLLM_API_BASE" "$ROOT_ENV")
OPENLLM_API_KEY=$(get_env_value "OPENLLM_API_KEY" "$ROOT_ENV")
OPENLLM_AUTH_TYPE=$(get_env_value "OPENLLM_AUTH_TYPE" "$ROOT_ENV")
EXA_API_KEY=$(get_env_value "EXA_API_KEY" "$ROOT_ENV")
LETTA_DEBUG=$(get_env_value "LETTA_DEBUG" "$ROOT_ENV")
LETTA_CODE_TELEM=$(get_env_value "LETTA_CODE_TELEM" "$ROOT_ENV")
DISABLE_AUTOUPDATER=$(get_env_value "DISABLE_AUTOUPDATER" "$ROOT_ENV")
LETTA_DEBUG_AUTOUPDATE=$(get_env_value "LETTA_DEBUG_AUTOUPDATE" "$ROOT_ENV")
LETTA_DEBUG_KITTY=$(get_env_value "LETTA_DEBUG_KITTY" "$ROOT_ENV")

# AWS Configuration
AWS_ACCESS_KEY_ID=$(get_env_value "AWS_ACCESS_KEY_ID" "$ROOT_ENV")
AWS_SECRET_ACCESS_KEY=$(get_env_value "AWS_SECRET_ACCESS_KEY" "$ROOT_ENV")
AWS_REGION=$(get_env_value "AWS_REGION" "$ROOT_ENV")
AWS_S3_BUCKET=$(get_env_value "AWS_S3_BUCKET" "$ROOT_ENV")

# =============================================================================
# Generate letta/.env (for Letta Docker container)
# =============================================================================
echo -e "${CYAN}Generating letta/.env...${NC}"

cat > "$LETTA_ENV" << EOF
# Auto-generated from root .env by setup-env.sh
# Do not edit directly - edit root .env instead

##########################################################
# Letta Server Configuration
##########################################################

EOF

# Add API keys (only if set)
if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY" >> "$LETTA_ENV"
fi

if [ -n "$OPENAI_API_KEY" ]; then
    echo "OPENAI_API_KEY=$OPENAI_API_KEY" >> "$LETTA_ENV"
fi

if [ -n "$GOOGLE_API_KEY" ]; then
    echo "GOOGLE_API_KEY=$GOOGLE_API_KEY" >> "$LETTA_ENV"
fi

if [ -n "$OLLAMA_BASE_URL" ]; then
    echo "OLLAMA_BASE_URL=$OLLAMA_BASE_URL" >> "$LETTA_ENV"
fi

if [ -n "$VLLM_API_BASE" ]; then
    echo "VLLM_API_BASE=$VLLM_API_BASE" >> "$LETTA_ENV"
fi

if [ -n "$OPENLLM_API_KEY" ]; then
    echo "OPENLLM_API_KEY=$OPENLLM_API_KEY" >> "$LETTA_ENV"
fi

if [ -n "$OPENLLM_AUTH_TYPE" ]; then
    echo "OPENLLM_AUTH_TYPE=$OPENLLM_AUTH_TYPE" >> "$LETTA_ENV"
fi

if [ -n "$EXA_API_KEY" ]; then
    echo "EXA_API_KEY=$EXA_API_KEY" >> "$LETTA_ENV"
fi

echo -e "${CYAN}✓ Created $LETTA_ENV${NC}"

# =============================================================================
# Generate letta-code/.env (for letta-code UI)
# =============================================================================
echo -e "${CYAN}Generating letta-code/.env...${NC}"

cat > "$LETTA_CODE_ENV" << EOF
# Auto-generated from root .env by setup-env.sh
# Do not edit directly - edit root .env instead

# =============================================================================
# Letta Configuration
# =============================================================================

EOF

# Letta connection
if [ -n "$LETTA_BASE_URL" ]; then
    echo "LETTA_BASE_URL=$LETTA_BASE_URL" >> "$LETTA_CODE_ENV"
fi

if [ -n "$LETTA_API_KEY" ]; then
    echo "LETTA_API_KEY=$LETTA_API_KEY" >> "$LETTA_CODE_ENV"
fi

cat >> "$LETTA_CODE_ENV" << EOF

# =============================================================================
# Image Generation (Optional)
# =============================================================================

EOF

# Image generation keys
if [ -n "$OPENAI_API_KEY" ]; then
    echo "OPENAI_API_KEY=$OPENAI_API_KEY" >> "$LETTA_CODE_ENV"
fi

if [ -n "$GOOGLE_API_KEY" ]; then
    echo "GOOGLE_API_KEY=$GOOGLE_API_KEY" >> "$LETTA_CODE_ENV"
fi

if [ -n "$GEMINI_API_KEY" ]; then
    echo "GEMINI_API_KEY=$GEMINI_API_KEY" >> "$LETTA_CODE_ENV"
fi

cat >> "$LETTA_CODE_ENV" << EOF

# =============================================================================
# Perplexity (Optional)
# =============================================================================

EOF

# Perplexity
if [ -n "$PERPLEXITY_API_KEY" ]; then
    echo "PERPLEXITY_API_KEY=$PERPLEXITY_API_KEY" >> "$LETTA_CODE_ENV"
fi

if [ -n "$PERPLEXITY_TIMEOUT_MS" ]; then
    echo "PERPLEXITY_TIMEOUT_MS=$PERPLEXITY_TIMEOUT_MS" >> "$LETTA_CODE_ENV"
fi

cat >> "$LETTA_CODE_ENV" << EOF

# =============================================================================
# Notion Publishing (Optional)
# =============================================================================

EOF

# Notion
if [ -n "$NOTION_TOKEN" ]; then
    echo "NOTION_TOKEN=$NOTION_TOKEN" >> "$LETTA_CODE_ENV"
fi

if [ -n "$NOTION_DATABASE_ID" ]; then
    echo "NOTION_DATABASE_ID=$NOTION_DATABASE_ID" >> "$LETTA_CODE_ENV"
fi

cat >> "$LETTA_CODE_ENV" << EOF

# =============================================================================
# Development & Debug (Optional)
# =============================================================================

EOF

# Debug flags
if [ -n "$LETTA_DEBUG" ]; then
    echo "LETTA_DEBUG=$LETTA_DEBUG" >> "$LETTA_CODE_ENV"
fi

if [ -n "$LETTA_CODE_TELEM" ]; then
    echo "LETTA_CODE_TELEM=$LETTA_CODE_TELEM" >> "$LETTA_CODE_ENV"
fi

if [ -n "$DISABLE_AUTOUPDATER" ]; then
    echo "DISABLE_AUTOUPDATER=$DISABLE_AUTOUPDATER" >> "$LETTA_CODE_ENV"
fi

if [ -n "$LETTA_DEBUG_AUTOUPDATE" ]; then
    echo "LETTA_DEBUG_AUTOUPDATE=$LETTA_DEBUG_AUTOUPDATE" >> "$LETTA_CODE_ENV"
fi

if [ -n "$LETTA_DEBUG_KITTY" ]; then
    echo "LETTA_DEBUG_KITTY=$LETTA_DEBUG_KITTY" >> "$LETTA_CODE_ENV"
fi

echo -e "${CYAN}✓ Created $LETTA_CODE_ENV${NC}"

# =============================================================================
# Generate apps/web/.env (for Next.js web app)
# =============================================================================
echo -e "${CYAN}Generating apps/web/.env...${NC}"

# Check if the web app .env exists, if not create from template
if [ -f "$WEB_APP_ENV" ]; then
    # Update existing .env with values from root
    # Read existing DATABASE_URL and NEXTAUTH settings
    EXISTING_DATABASE_URL=$(get_env_value "DATABASE_URL" "$WEB_APP_ENV")
    EXISTING_NEXTAUTH_URL=$(get_env_value "NEXTAUTH_URL" "$WEB_APP_ENV")
    EXISTING_NEXTAUTH_SECRET=$(get_env_value "NEXTAUTH_SECRET" "$WEB_APP_ENV")
    EXISTING_GOOGLE_CLIENT_ID=$(get_env_value "GOOGLE_CLIENT_ID" "$WEB_APP_ENV")
    EXISTING_GOOGLE_CLIENT_SECRET=$(get_env_value "GOOGLE_CLIENT_SECRET" "$WEB_APP_ENV")
fi

# Set defaults if not present
DATABASE_URL=${EXISTING_DATABASE_URL:-"postgresql://deepscifi:deepscifi@localhost:5433/deepscifi?schema=app"}
NEXTAUTH_URL=${EXISTING_NEXTAUTH_URL:-"http://localhost:3030"}
NEXTAUTH_SECRET=${EXISTING_NEXTAUTH_SECRET:-"$(openssl rand -base64 32 2>/dev/null || echo 'change-me-in-production')"}
WEB_GOOGLE_CLIENT_ID=${EXISTING_GOOGLE_CLIENT_ID:-""}
WEB_GOOGLE_CLIENT_SECRET=${EXISTING_GOOGLE_CLIENT_SECRET:-""}

cat > "$WEB_APP_ENV" << 'ENVEOF'
# Auto-generated from root .env by setup-env.sh
# Do not edit directly - edit root .env instead (except for web-specific settings below)

# =============================================================================
# Database (web-specific)
# =============================================================================
ENVEOF

echo "DATABASE_URL=\"$DATABASE_URL\"" >> "$WEB_APP_ENV"

cat >> "$WEB_APP_ENV" << 'ENVEOF'

# =============================================================================
# NextAuth.js (web-specific)
# =============================================================================
ENVEOF

echo "NEXTAUTH_URL=\"$NEXTAUTH_URL\"" >> "$WEB_APP_ENV"
echo "NEXTAUTH_SECRET=\"$NEXTAUTH_SECRET\"" >> "$WEB_APP_ENV"

cat >> "$WEB_APP_ENV" << 'ENVEOF'

# OAuth Providers (web-specific - edit these directly)
ENVEOF

echo "GOOGLE_CLIENT_ID=\"$WEB_GOOGLE_CLIENT_ID\"" >> "$WEB_APP_ENV"
echo "GOOGLE_CLIENT_SECRET=\"$WEB_GOOGLE_CLIENT_SECRET\"" >> "$WEB_APP_ENV"

cat >> "$WEB_APP_ENV" << 'ENVEOF'

# =============================================================================
# Letta Server (from root .env)
# =============================================================================
ENVEOF

echo "LETTA_BASE_URL=\"${LETTA_BASE_URL:-http://localhost:8285}\"" >> "$WEB_APP_ENV"
echo "LETTA_API_KEY=\"${LETTA_API_KEY:-}\"" >> "$WEB_APP_ENV"

cat >> "$WEB_APP_ENV" << 'ENVEOF'

# =============================================================================
# AWS S3 Storage (from root .env)
# =============================================================================
ENVEOF

echo "AWS_ACCESS_KEY_ID=\"${AWS_ACCESS_KEY_ID:-}\"" >> "$WEB_APP_ENV"
echo "AWS_SECRET_ACCESS_KEY=\"${AWS_SECRET_ACCESS_KEY:-}\"" >> "$WEB_APP_ENV"
echo "AWS_REGION=\"${AWS_REGION:-us-east-1}\"" >> "$WEB_APP_ENV"
echo "AWS_S3_BUCKET=\"${AWS_S3_BUCKET:-deep-sci-fi-assets}\"" >> "$WEB_APP_ENV"

cat >> "$WEB_APP_ENV" << 'ENVEOF'

# =============================================================================
# API Keys (from root .env)
# =============================================================================
ENVEOF

echo "ANTHROPIC_API_KEY=\"${ANTHROPIC_API_KEY:-}\"" >> "$WEB_APP_ENV"
echo "GOOGLE_API_KEY=\"${GOOGLE_API_KEY:-}\"" >> "$WEB_APP_ENV"
echo "OPENAI_API_KEY=\"${OPENAI_API_KEY:-}\"" >> "$WEB_APP_ENV"

echo -e "${CYAN}✓ Created $WEB_APP_ENV${NC}"

echo ""
echo -e "${PURPLE}✓ Environment setup complete!${NC}"
echo -e "${CYAN}  • letta/.env configured for Docker container${NC}"
echo -e "${CYAN}  • letta-code/.env configured for CLI${NC}"
echo -e "${CYAN}  • apps/web/.env configured for Next.js web app${NC}"
echo ""
