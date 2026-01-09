#!/bin/bash
set -e

# Logging
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
echo "Starting user data script..."

# Update system
dnf update -y

# Install Docker
dnf install -y docker git
systemctl start docker
systemctl enable docker
usermod -aG docker ec2-user

# Install Docker Compose v2
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Also install as standalone for compatibility
ln -sf /usr/local/lib/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose

# Install Caddy (reverse proxy + automatic SSL)
dnf install -y 'dnf-command(copr)'
dnf copr enable -y @caddy/caddy
dnf install -y caddy

# Install AWS CLI v2 (for secrets management)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
dnf install -y unzip
unzip -q awscliv2.zip
./aws/install
rm -rf aws awscliv2.zip

# Install Node.js and Bun (for some services)
dnf install -y nodejs npm
curl -fsSL https://bun.sh/install | bash
export BUN_INSTALL="/root/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

# Clone repository
cd /home/ec2-user
if [ ! -d "deep-sci-fi" ]; then
  git clone --recurse-submodules ${github_repo} deep-sci-fi
fi
cd deep-sci-fi

# Set ownership
chown -R ec2-user:ec2-user /home/ec2-user/deep-sci-fi

# Create environment file placeholder (will be configured manually or via CI/CD)
if [ ! -f ".env" ]; then
  cat > .env << 'ENVEOF'
# Deep Sci-Fi Environment Configuration
# Fill in these values after deployment

# Database
DB_PASSWORD=changeme_secure_password

# API Keys (required)
ANTHROPIC_API_KEY=sk-ant-...

# API Keys (optional)
OPENAI_API_KEY=
GOOGLE_API_KEY=

# Domain (for SSL - leave empty to use IP only)
DOMAIN=
ENVEOF
  chown ec2-user:ec2-user .env
fi

# Create systemd service for Docker Compose
cat > /etc/systemd/system/deep-sci-fi.service << 'EOF'
[Unit]
Description=Deep Sci-Fi Application Stack
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ec2-user/deep-sci-fi
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=300
User=ec2-user
Group=docker

[Install]
WantedBy=multi-user.target
EOF

# Enable service (will start after docker-compose.prod.yml is created)
systemctl daemon-reload
# systemctl enable deep-sci-fi.service

echo "User data script completed!"
echo "Next steps:"
echo "1. SSH into the instance"
echo "2. Edit /home/ec2-user/deep-sci-fi/.env with your API keys"
echo "3. Run: docker-compose -f docker-compose.prod.yml up -d"
