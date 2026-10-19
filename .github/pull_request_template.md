## 变更类型

<!-- 至少勾选一项；PR 标题需符合 Conventional Commits -->

- [ ] ✨ 新功能（feat）
- [ ] 🐛 缺陷修复（fix）
- [ ] ♻️ 重构（refactor）
- [ ] ⚡ 性能优化（perf）
- [ ] ✅ 测试（test）
- [ ] 📝 文档（docs）
- [ ] 🔧 构建 / CI（build / ci / chore）

## 关联 Issue

<!-- 例如 Closes #123；没有则写“无” -->

Closes #

## 变更内容

<!-- 做了什么、为什么这样做。涉及算法/接口变更请写清楚 -->

-
-

## 测试与验证

<!-- 列出你实际执行过的命令或步骤，CI 之外的人工验证也写在这里 -->

- [ ] 后端：`cd garden-asset-platform/backend && python -m pytest`
- [ ] 前端：`cd garden-asset-platform/frontend && npm run lint:check && npm run test:ci && npm run build`
- [ ] Docker：`docker compose build`（如涉及）
- [ ] 手工验证步骤：

## 影响范围

<!-- 受影响的模块 / API / 数据表 / 环境变量 / 部署方式；无则写“无” -->

- 模块：
- API：
- 数据迁移：
- 环境变量：

## 截图 / 录屏（UI 改动必填）

## 自查清单

- [ ] PR 标题符合 Conventional Commits（如 `feat(watermark): ...`）
- [ ] 目标分支正确：功能 → `develop`；发布/热修 → `main`
- [ ] 没有提交密钥、`.env`、个人配置或大文件
- [ ] 新增环境变量已同步到 `.env.example`
- [ ] 新增/修改的逻辑有对应测试，或说明了无法测试的原因
- [ ] 文档已同步更新（README / DEVELOPMENT / API 说明）
- [ ] 我已本地自测，并确认不会破坏现有功能
