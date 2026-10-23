# Makefile - 项目管理命令

.PHONY: help install run test test-backend test-backend-safe test-frontend test-frontend-safe lint ci clean docker-up docker-down

help:
	@echo "可用命令:"
	@echo "  make install       安装依赖（含测试依赖）"
	@echo "  make run           启动开发服务器"
	@echo "  make test          运行后端 + 前端测试"
	@echo "  make test-backend  运行后端 pytest"
	@echo "  make test-backend-safe 逐文件隔离运行后端测试（内存受限环境）"
	@echo "  make test-frontend 运行前端 Vitest"
	@echo "  make test-frontend-safe 逐文件运行前端测试（内存受限环境）"
	@echo "  make lint          前端 ESLint + 后端 ruff"
	@echo "  make ci            本地复现 CI（lint + test + build）"
	@echo "  make e2e           对运行中的后端跑端到端业务流程"
	@echo "  make clean         清理临时文件"
	@echo "  make docker-up     启动Docker容器"
	@echo "  make docker-down   停止Docker容器"
	@echo "  make init-db       初始化数据库"
	@echo "  make create-data   创建测试数据"

# 安装依赖
install:
	cd backend && pip install -r requirements-dev.txt
	cd frontend && npm ci

# 启动开发服务器
run:
	@echo "启动后端..."
	cd backend && python run.py &
	@echo "启动前端..."
	cd frontend && npm run dev

# 运行测试
test: test-backend test-frontend

test-backend:
	cd backend && python -m pytest -v

test-backend-safe:
	cd backend && python scripts/run_tests.py

test-frontend:
	cd frontend && npm run test:ci

test-frontend-safe:
	cd frontend && npm run test:ci:safe

lint:
	cd backend && ruff check app algorithm --select E9,F63,F7,F82
	cd frontend && npm run lint:check

ci: lint test
	cd frontend && npm run build

# 端到端业务流程（需要先启动后端并初始化数据库）
e2e:
	cd backend && python scripts/e2e_flow.py

# 清理临时文件
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "node_modules" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +
	rm -rf backend/uploads/*
	rm -rf backend/test_uploads

# Docker命令
docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

# 数据库命令
init-db:
	cd backend && python scripts/init_db.py

create-data:
	cd backend && python scripts/create_test_data.py

create-watermark:
	cd backend && python scripts/create_watermark.py

# Flask命令
create-admin:
	cd backend && flask create-admin

reset-password:
	cd backend && flask reset-password

# 构建命令
build-frontend:
	cd frontend && npm run build

build-backend:
	cd backend && pip wheel . --no-deps -w dist/