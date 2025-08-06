#!/bin/bash

# Automate deployment of the TAIPPA platform to Railway.
#
# This script uses the Railway CLI to create a new project, add a
# PostgreSQL plugin, set environment variables and deploy the backend
# and static front‑end services.  It minimises manual steps: you will
# be prompted for your Railway login, secret keys and any API tokens.
# Ensure you have the Railway CLI installed (`npm i -g @railway/cli`)
# before running this script.  Run this script from the root of the
# TAIPPA repository.

set -euo pipefail

PROJECT_NAME=${RAILWAY_PROJECT_NAME:-taippa-staging}

command -v railway >/dev/null 2>&1 || {
  echo >&2 "Railway CLI is not installed.  Install it with: npm i -g @railway/cli";
  exit 1;
}

echo "=== Railway Deployment Script ==="

# 1. Login to Railway.  This will open a browser window for OAuth if
#    required.  The script will wait until login is complete.
echo "\nStep 1: Logging into Railway..."
railway login

# 2. Create or select project
echo "\nStep 2: Creating Railway project '$PROJECT_NAME'..."
# Check if project exists
if railway project list | grep -q "$PROJECT_NAME"; then
  echo "Project already exists.  Using existing project."
  railway project switch --project "$PROJECT_NAME"
else
  railway init --name "$PROJECT_NAME"
fi

# 3. Add PostgreSQL plugin if none exists
echo "\nStep 3: Adding managed PostgreSQL..."
if ! railway addon list | grep -q postgres; then
  railway addon add postgres
  echo "Waiting for database to provision..."
  sleep 10
else
  echo "PostgreSQL addon already present."
fi

# 4. Retrieve database connection URL from the addon.  The Railway CLI
#    stores addon variables under the addon name.  We extract the
#    DATABASE_URL and transform it for SQLAlchemy's asyncpg driver.
echo "\nRetrieving database connection URL..."
DB_URL_RAW=$(railway variables list | grep DATABASE_URL | awk '{print $2}' || true)
if [ -z "$DB_URL_RAW" ]; then
  echo "Could not automatically retrieve DATABASE_URL.  Please paste the Postgres connection string (e.g. postgres://user:pass@host:port/dbname):"
  read -r DB_URL_RAW
fi
# Prefix with asyncpg if not already present
if [[ "$DB_URL_RAW" != postgresql+asyncpg* ]]; then
  DB_URL="postgresql+asyncpg://${DB_URL_RAW#postgres://}"
else
  DB_URL="$DB_URL_RAW"
fi

# 5. Prompt for secret keys and other sensitive configuration
echo "\nEnter a strong random SECRET_KEY (used for password hashing):"
read -r SECRET_KEY
echo "Enter a strong random JWT_SECRET_KEY (used to sign JWT tokens):"
read -r JWT_SECRET_KEY
echo "Enter your Stripe secret key (or leave blank for none):"
read -r STRIPE_SECRET_KEY
echo "Enter your Stripe webhook secret (or leave blank for none):"
read -r STRIPE_WEBHOOK_SECRET
echo "Enter your domain for Stripe success redirects (e.g. https://<your-domain>.up.railway.app):"
read -r STRIPE_SUCCESS_DOMAIN
echo "Enter the default tenant ID (leave blank if seeding later):"
read -r DEFAULT_TENANT_ID

# 6. Set environment variables on the project
echo "\nStep 4: Setting environment variables..."
railway variables set \
  DATABASE_URL="$DB_URL" \
  SECRET_KEY="$SECRET_KEY" \
  JWT_SECRET_KEY="$JWT_SECRET_KEY" \
  ACCESS_TOKEN_EXPIRE_MINUTES="60" \
  STRIPE_SECRET_KEY="$STRIPE_SECRET_KEY" \
  STRIPE_WEBHOOK_SECRET="$STRIPE_WEBHOOK_SECRET" \
  STRIPE_SUCCESS_DOMAIN="$STRIPE_SUCCESS_DOMAIN" \
  DEFAULT_TENANT_ID="$DEFAULT_TENANT_ID" \
  LOG_LEVEL="info"

# 7. Deploy backend service
echo "\nStep 5: Deploying backend service..."
# If a backend service already exists, update it; otherwise create
if railway service list | grep -q backend; then
  echo "Backend service exists.  Deploying..."
  railway up --service backend --detach
else
  railway up --service backend --detach --dockerfile Dockerfile.backend
fi

# 8. Deploy static front‑end
echo "\nStep 6: Deploying static front‑end..."
if railway service list | grep -q frontend; then
  echo "Frontend service exists.  Deploying..."
  railway up --service frontend --detach
else
  # Railway infers static site when pointing to a folder.  We specify the
  # 'source' flag to deploy only the 'frontend' directory.
  railway up --service frontend --detach --root frontend
fi

# 9. Completion message
echo "\nDeployment initiated.  Railway will now build and deploy your services."
echo "Monitor the build progress in the Railway dashboard.  Once complete,"
echo "visit the provided domain names to access your backend API and front‑end."
echo "You can run 'railway logs' to view logs and 'railway open' to open the project in a browser."