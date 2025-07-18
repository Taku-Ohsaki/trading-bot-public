#!/bin/bash

# Public repository sync script
# This script synchronizes only non-sensitive files to the public repository

echo "🌐 Syncing to public repository (trading-bot-public)..."

# Ensure we're using the public .gitignore
if [ -f .gitignore-public ]; then
    mv .gitignore .gitignore-private
    mv .gitignore-public .gitignore
fi

# Remove sensitive files first
git rm -r --cached manual/ 2>/dev/null || true

# Add only non-sensitive files
git add .
git add -f docker-compose.yml
git add -f requirements.txt
git add -f README.md
git add -f Dockerfile.dev
git add -f Makefile
git add -f .env.template
git add -f postgres/init/
git add -f scripts/etl_nightly.sh
git add -f scripts/fetch_prices_daily.py
git add -f src/data/
git add -f .github/workflows/

# Explicitly exclude manual directory
git rm -r --cached manual/ 2>/dev/null || true

# Commit changes
git commit -m "🌐 Public sync: Infrastructure and non-sensitive code update

- Update Docker configuration
- Update requirements and documentation
- Update ETL scripts and data clients
- Update CI/CD configuration
- Exclude ML algorithms and sensitive implementations

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push to public repository
git push origin main

echo "✅ Public repository sync completed!"
echo "🌐 Public repo contains only infrastructure and non-sensitive code"