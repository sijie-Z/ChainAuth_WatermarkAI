#!/bin/bash
# 启动脚本 - Linux/Mac

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "苏州园林数字资产安全分发与溯源系统"
echo "========================================"

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 未安装${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python3 已安装${NC}"

# 检查Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}Node.js 未安装${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Node.js 已安装${NC}"

# 创建虚拟环境
if [ ! -d "backend/venv" ]; then
    echo -e "${YELLOW}创建Python虚拟环境...${NC}"
    cd backend && python3 -m venv venv && cd ..
fi

# 安装后端依赖
echo -e "${YELLOW}安装后端依赖...${NC}"
source backend/venv/bin/activate
pip install -r backend/requirements.txt

# 安装前端依赖
echo -e "${YELLOW}安装前端依赖...${NC}"
cd frontend && npm install && cd ..

# 初始化数据库
echo -e "${YELLOW}初始化数据库...${NC}"
cd backend && python scripts/init_db.py && cd ..

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}安装完成!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "启动命令:"
echo "  后端: cd backend && source venv/bin/activate && python run.py"
echo "  前端: cd frontend && npm run dev"
echo ""
echo "默认账号: admin / admin123"