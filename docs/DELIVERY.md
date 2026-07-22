# 私有交付版部署说明

## 1. 交付约定

- 本仓库为私有交付版，默认不提供线上体验入口与公开演示配置
- 不提交任何真实生产密钥、数据库密码、Redis 密码、云账号、Kubeconfig、SSH Key、模型 API Key
- 使用 `.env.example` 作为交付模板，部署时复制为 `.env` 并替换敏感值

## 2. Docker Compose 一键启动（推荐）

### 2.1 准备环境变量

```bash
cp .env.example .env
```

至少需要修改：

- `SECRET_KEY`
- `MYSQL_PASSWORD`
- `MYSQL_ROOT_PASSWORD`
- `ALLOWED_HOSTS`（如需域名/外网访问）

### 2.2 启动服务

```bash
docker compose up -d --build
```

默认访问：

- http://localhost:8000

首次启动会自动执行：

- 数据库等待（`SXDEVOPS_WAIT_FOR_DB=1`）
- `migrate`（`SXDEVOPS_MIGRATE=1`）

如需导入演示数据，可将以下变量改为 `1` 后重启容器：

- `SXDEVOPS_SEED_DATA`
- `SXDEVOPS_SEED_TEMPLATES`

## 3. 本地开发启动（可选）

### 3.1 后端

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py seed_templates
python -m daphne -b 0.0.0.0 -p 8000 sxdevops.asgi:application
```

### 3.2 前端

```bash
cd frontend
npm install
npm run dev
```

## 4. 常见问题

### 4.1 登录报错 500

- 多数为后端未启动或数据库未就绪导致
- Docker Compose 场景优先检查：`docker compose ps`、`docker compose logs -f sxdevops`

