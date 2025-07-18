#!/bin/bash

# Public repository sync script
# This script synchronizes only non-sensitive files to the public repository

echo "🌐 Syncing to public repository (trading-bot-public)..."

# Switch to public .gitignore
if [ -f .gitignore-public ]; then
    echo "📄 Switching to public .gitignore..."
    cp .gitignore .gitignore-private
    cp .gitignore-public .gitignore
fi

# Remove sensitive files and directories first
git rm -r --cached manual/ 2>/dev/null || true
git rm --cached .env 2>/dev/null || true
git rm --cached .env.* 2>/dev/null || true

# Add only non-sensitive files
git add .
git add -f docker-compose.yml
git add -f requirements.txt
git add -f README.md
git add -f Dockerfile.dev
git add -f Makefile
git add -f .env.template
git add -f postgres/init/
git add -f scripts/
git add -f src/
git add -f tests/
git add -f .github/workflows/

# Final cleanup - ensure sensitive files are removed
git rm -r --cached manual/ 2>/dev/null || true
git rm --cached .env 2>/dev/null || true
git rm --cached .env.* 2>/dev/null || true

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