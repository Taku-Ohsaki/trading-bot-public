#!/bin/bash

# Public repository sync script
# This script synchronizes only non-sensitive files to the public repository

echo "🌐 Syncing to public repository (trading-bot-public)..."

# Remove sensitive files and directories first
git rm -r --cached manual/ 2>/dev/null || true
git rm --cached .env 2>/dev/null || true
git rm --cached .env.* 2>/dev/null || true
git rm -r --cached src/models/ 2>/dev/null || true

# Switch to public .gitignore
if [ -f .gitignore-public ]; then
    echo "📄 Switching to public .gitignore..."
    cp .gitignore .gitignore-private
    cp .gitignore-public .gitignore
fi

# Add only specific non-sensitive files (avoiding git add .)
git add .gitignore
git add sync-public.sh
git add sync-private.sh
git add docker-compose.yml
git add requirements.txt
git add README.md
git add Dockerfile.dev
git add Makefile
git add postgres/init/
git add scripts/etl_nightly.sh
git add scripts/fetch_prices_daily.py
git add scripts/fetch_prices_intraday.py
git add scripts/produce_signals.py
git add src/data/
git add tests/pytorch_test.py
git add .github/workflows/ 2>/dev/null || true

# Final cleanup - ensure sensitive files are removed
git rm -r --cached manual/ 2>/dev/null || true
git rm --cached .env 2>/dev/null || true
git rm --cached .env.* 2>/dev/null || true
git rm -r --cached src/models/ 2>/dev/null || true

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

# Restore private .gitignore
if [ -f .gitignore-private ]; then
    echo "📄 Restoring private .gitignore..."
    cp .gitignore-private .gitignore
fi

echo "✅ Public repository sync completed!"
echo "🌐 Public repo contains only infrastructure and non-sensitive code"