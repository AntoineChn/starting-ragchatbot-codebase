#!/usr/bin/env bash
# Frontend code quality checks
# Runs Prettier format check on all frontend JS, CSS, and HTML files

set -e

FRONTEND_DIR="$(cd "$(dirname "$0")/../frontend" && pwd)"

echo "Running frontend quality checks..."
echo ""

# Install dependencies if node_modules is missing
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "Installing frontend dev dependencies..."
  (cd "$FRONTEND_DIR" && npm install)
  echo ""
fi

# Run Prettier format check
echo "Checking formatting with Prettier..."
(cd "$FRONTEND_DIR" && npx prettier --check "**/*.{js,css,html}")

echo ""
echo "All frontend quality checks passed."
