#!/bin/bash

# Private repository sync script
# This script synchronizes all files (including ML algorithms) to the private repository

echo "🔒 Syncing to private repository (trading-bot-live)..."

# Create a temporary branch for private sync
git checkout -b private-sync

# Temporarily use the private .gitignore
mv .gitignore .gitignore-public
mv .gitignore-private .gitignore

# Add all files that were previously ignored
git add .
git add -f src/models/
git add -f tests/test_*_transformer*.py
git add -f tests/test_*_model*.py
git add -f algorithms/
git add -f strategies/
git add -f *.pkl
git add -f *.pt
git add -f *.pth
git add -f checkpoints/
git add -f saved_models/
git add -f project_documentation.html
git add -f specification.txt

# Commit all changes
git commit -m "🔒 Private sync: Include all files including ML algorithms and documentation

- Add ML model implementations (src/models/)
- Add ML algorithm test files
- Add project documentation
- Add specification.txt
- Include all previously ignored files for complete backup

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push to private repository
git push private private-sync:main --force

# Restore public .gitignore
mv .gitignore .gitignore-private
mv .gitignore-public .gitignore

# Return to main branch
git checkout main
git branch -D private-sync

echo "✅ Private repository sync completed!"
echo "🔒 Private repo now contains all files including ML algorithms"
echo "🌐 Public repo continues to exclude sensitive algorithms"