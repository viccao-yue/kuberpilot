# 私有交付变更记录

## Unreleased

- 基线：私有交付版仓库初始化

## 2026-07-22

- Docker Compose 去除硬编码敏感项，改为 `.env` 驱动（SECRET_KEY、数据库账号密码、ALLOWED_HOSTS、端口映射）
- 新增 `.env.example` 作为交付模板
- 新增 `docs/DELIVERY.md` 部署说明
- 新增 `docker-compose.override.yml.example`（示例：启用演示数据）
