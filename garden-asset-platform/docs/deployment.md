# 项目部署文档

## 环境要求

### 生产环境
- Ubuntu 20.04+ / CentOS 7+
- Python 3.11+
- Node.js 22+
- PostgreSQL 14+
- Redis 6+
- Nginx 1.20+
- Docker & Docker Compose (可选)

## 部署方式

### 方式一: Docker部署 (推荐)

```bash
# 1. 克隆项目
git clone <repository_url>
cd garden-asset-platform

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件设置生产环境配置

# 3. 启动服务
docker-compose up -d

# 4. 初始化数据库
docker-compose exec backend flask init-gardens

# 5. 创建管理员
docker-compose exec backend flask create-admin
```

### 方式二: 手动部署

#### 后端部署

```bash
# 1. 安装Python依赖
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn

# 2. 配置环境变量
export FLASK_ENV=production
export DATABASE_URL=postgresql://user:pass@localhost:5432/garden_asset
export SECRET_KEY=your-secret-key
export JWT_SECRET_KEY=your-jwt-secret

# 3. 初始化数据库
python scripts/init_db.py

# 4. 使用Gunicorn启动
gunicorn --bind 0.0.0.0:5000 --workers 4 "app:create_app()"
```

#### 前端部署

```bash
# 1. 安装依赖
cd frontend
npm install

# 2. 构建
npm run build

# 3. 部署到Nginx
sudo cp -r dist/* /var/www/garden-asset/
```

#### Nginx配置

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        root /var/www/garden-asset;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 服务管理

### Docker命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend

# 重启服务
docker-compose restart

# 停止服务
docker-compose down
```

### 系统服务 (systemd)

创建 `/etc/systemd/system/garden-backend.service`:

```ini
[Unit]
Description=Garden Asset Platform Backend
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/garden-asset/backend
ExecStart=/opt/garden-asset/backend/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 "app:create_app()"
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable garden-backend
sudo systemctl start garden-backend
```

## 可选 MinIO 原件存储

默认 `STORAGE_BACKEND=local`，升级不会改变现有文件位置。需要把新上传的原件和历史版本放入 MinIO 时，在 `.env` 中设置：

```bash
STORAGE_BACKEND=minio
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=请替换为独立账号
MINIO_SECRET_KEY=请替换为独立密钥
MINIO_BUCKET=garden-assets
MINIO_SECURE=false
```

backend 与 worker 必须使用同一组配置。首次启动会自动建桶；连接失败会明确阻止启用，不会静默写回本地。旧的本地绝对路径与新的 `minio://` 引用可以混存，不自动迁移。

**真实部署验收步骤**（当前开发机未提供 Docker daemon，需在有 Docker 的环境执行）：

```bash
docker compose up -d --build
docker compose ps
docker compose exec backend flask db upgrade
docker compose exec backend flask uploads list
```

然后上传一个文档和一个视频，确认：数据库保存 `minio://` 引用；下载 SHA-256 与原件一致；视频预览返回 200/206；worker 完成水印；版本恢复和证据包导出成功；重启 backend/worker 后仍可读取。停止 MinIO 后应明确报错，不得把新文件静默写回本地。

派生的缩略图、水印、指纹和证据包临时文件仍使用挂载的本地共享卷，生产环境应把这些卷放在可靠存储上；对象桶的备份、HA、容量巡检和旧文件搬迁需另行安排。

## 数据库维护

```bash
# 备份数据库
pg_dump garden_asset > backup_$(date +%Y%m%d).sql

# 恢复数据库
psql garden_asset < backup_20260426.sql

# 数据库迁移
flask db migrate -m "description"
flask db upgrade
```

## 监控与日志

- 应用日志: `/var/log/garden-asset/app.log`
- Nginx日志: `/var/log/nginx/`
- 建议配置日志轮转

## 安全配置

1. 配置HTTPS (Let's Encrypt)
2. 设置防火墙规则
3. 定期更新依赖
4. 配置数据库访问控制
5. 启用Redis密码认证