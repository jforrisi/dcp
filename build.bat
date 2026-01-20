@echo off
echo Building frontend...
cd frontend
call npm install
call npm run build

echo Copying frontend build to backend static folder...
cd ..
if exist backend\app\static rmdir /s /q backend\app\static
mkdir backend\app\static
xcopy /E /I /Y frontend\dist\* backend\app\static\

echo Build complete!
