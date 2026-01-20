#!/bin/bash
set -e

echo "Building frontend..."
cd frontend
npm install
npm run build

echo "Copying frontend build to backend static folder..."
cd ..
rm -rf backend/app/static/*
cp -r frontend/dist/* backend/app/static/

echo "Build complete!"
