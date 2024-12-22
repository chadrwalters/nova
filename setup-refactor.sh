#!/bin/bash
set -e  # Exit on error

echo "Creating backup branch..."
git checkout -b refactor-backup
git add .
git commit -m "Create backup branch before refactoring processors"
git push origin refactor-backup

echo "Creating working branch..."
git checkout main
git checkout -b refactor-processors

echo "Verifying branches..."
echo "Current branch: $(git branch --show-current)"
echo "Backup branch exists: $(git branch -a | grep refactor-backup || echo 'NO')"

git status 