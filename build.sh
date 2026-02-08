#!/bin/bash
set -e

echo "Building frontend..."
cd frontend
npm install
npm run build

echo "Copying frontend build to backend static folder..."
cd ..
# Remove entire static directory and recreate it to ensure clean state
rm -rf backend/app/static
mkdir -p backend/app/static
# Copy all files from dist, including hidden files
cp -r frontend/dist/. backend/app/static/

echo "Build complete!"
