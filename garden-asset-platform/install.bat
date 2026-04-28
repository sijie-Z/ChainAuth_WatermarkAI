@echo off
REM 启动脚本 - Windows

echo ========================================
echo 苏州园林数字资产安全分发与溯源系统
echo ========================================

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Python 未安装
    exit /b 1
)
echo [OK] Python 已安装

REM 检查Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Node.js 未安装
    exit /b 1
)
echo [OK] Node.js 已安装

REM 创建虚拟环境
if not exist "backend\venv" (
    echo 创建Python虚拟环境...
    cd backend
    python -m venv venv
    cd ..
)

REM 激活虚拟环境并安装依赖
echo 安装后端依赖...
call backend\venv\Scripts\activate.bat
pip install -r backend\requirements.txt

REM 安装前端依赖
echo 安装前端依赖...
cd frontend
call npm install
cd ..

REM 初始化数据库
echo 初始化数据库...
cd backend
python scripts\init_db.py
cd ..

echo.
echo ========================================
echo 安装完成!
echo ========================================
echo.
echo 启动命令:
echo   后端: cd backend ^&^& venv\Scripts\activate ^&^& python run.py
echo   前端: cd frontend ^&^& npm run dev
echo.
echo 默认账号: admin / admin123
pause