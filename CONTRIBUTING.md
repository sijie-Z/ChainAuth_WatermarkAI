# 贡献指南（Contributing Guide）

本仓库采用严格的 **Git Flow** 分支模型 + **Conventional Commits** 提交规范 + **PR 强制审查**。所有改动必须通过 Pull Request 进入 `develop`，禁止直接推送 `main` / `develop`。

## 1. 一次性本地配置

```bash
# 启用仓库内置 Git 钩子（提交信息校验、敏感文件拦截、保护分支拦截）
bash scripts/setup-git-hooks.sh

# 确认 Git 身份与外设
git config user.name
git config user.email
```

钩子由 `.githooks/` 提供，随仓库版本管理，不依赖 Node/Husky。

## 2. 分支模型

```
main        ●──────────────●──────────────●   ← 生产，只接受 release/* 与 hotfix/*
             \            / \            /
release/1.5.0 \          /   \          /
               ●────────●     ●────────●
              /            \ /
develop  ●───●───●───●───●───●───●───●        ← 集成，功能分支的合并目标
          \     /     \     /
feature/*  ●───●       ●───●                  ← 新功能
```

| 分支 | 从哪来 | 合并到 | 命名示例 | 用途 |
|------|--------|--------|----------|------|
| `main` | — | — | `main` | 生产分支，永远可发布，禁止直接提交 |
| `develop` | `main` | — | `develop` | 集成分支，日常开发的基线 |
| `feature/*` | `develop` | `develop` | `feature/watermark-robustness` | 新功能 |
| `bugfix/*` | `develop` | `develop` | `bugfix/login-refresh` | 非紧急缺陷修复 |
| `release/*` | `develop` | `main` + `develop` | `release/1.5.0` | 发布准备、版本号与 CHANGELOG |
| `hotfix/*` | `main` | `main` + `develop` | `hotfix/1.5.1` | 线上紧急修复，版本号 +1 |
| `docs/*` `chore/*` `ci/*` `refactor/*` `test/*` `perf/*` | `develop` | `develop` | `ci/add-codeql` | 非功能性改动 |

**硬规则**

- `main` 只接受来自 `release/*`、`hotfix/*` 的 PR。
- `develop` 只接受来自上述允许前缀分支的 PR。
- 分支名使用小写英文 + 连字符，例如 `feature/ai-trace-report`。
- 分支合并后立即删除远端分支。

## 3. 提交规范（Conventional Commits）

格式：`<type>(<scope>): <subject>`

| type | 含义 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(watermark): 支持抗裁剪 DCT 嵌入` |
| `fix` | 缺陷修复 | `fix(auth): 修复刷新令牌过期判断` |
| `docs` | 文档 | `docs(readme): 补充部署说明` |
| `style` | 格式（不影响逻辑） | `style(frontend): 统一缩进` |
| `refactor` | 重构 | `refactor(license): 拆分审批状态机` |
| `perf` | 性能优化 | `perf(ai): 缓存 CLIP 特征` |
| `test` | 测试 | `test(api): 增加授权审批用例` |
| `build` | 构建/依赖 | `build(docker): 升级基础镜像` |
| `ci` | CI/CD | `ci: 增加 CodeQL 扫描` |
| `chore` | 杂项 | `chore: 更新 .gitignore` |
| `revert` | 回滚 | `revert: 回滚 feat(xxx)` |

常用 scope：`backend` `frontend` `watermark` `blockchain` `ai` `auth` `license` `asset` `ci` `docs` `deps`。

标题不超过 72 个字符（中文按字符计），句尾不加句号。本地 `commit-msg` 钩子会校验；PR 标题同样会被 CI 校验（Squash 合并时 PR 标题即最终提交信息）。

## 4. 日常开发流程

```bash
# 1) 同步 develop
git switch develop
git pull --ff-only origin develop

# 2) 创建功能分支
bash scripts/gitflow.sh feature start watermark-robustness
#    等价于: git switch -c feature/watermark-robustness

# 3) 开发并提交
git add -A
git commit -m "feat(watermark): 增加抗裁剪嵌入参数"

# 4) 推送并发起 PR → develop
git push -u origin feature/watermark-robustness
```

PR 要求：

- 标题符合 Conventional Commits（CI 自动校验）。
- 描述使用模板，写明变更内容、测试方式、影响范围。
- 至少 1 名审查者通过；所有必选检查（CI、CodeQL、Dependency Review）通过。
- 功能类 PR 使用 **Squash and merge**；`release/*`、`hotfix/*` 使用 **Merge commit** 保留历史。
- 合并后删除分支。

## 5. 发布流程

```bash
# 1) 从 develop 创建发布分支
bash scripts/gitflow.sh release start 1.5.0

# 2) 只做发布准备：版本号、CHANGELOG、发布配置
#    - garden-asset-platform/frontend/package.json -> version
#    - garden-asset-platform/CHANGELOG.md
git commit -m "chore(release): 准备 v1.5.0"

# 3) 推送并向 main 发起 PR（GitHub 上 CI 全绿后合并）
git push -u origin release/1.5.0

# 4) 合并后回合并 develop，并在 main 上打标签
git switch main
git pull --ff-only origin main
git merge --no-ff release/1.5.0
git tag -a v1.5.0 -m "Release v1.5.0"
git push origin main v1.5.0

git switch develop
git merge --no-ff release/1.5.0
git push origin develop
git branch -d release/1.5.0
git push origin --delete release/1.5.0
```

推送 `v*` 标签会触发镜像构建与 GitHub Release（Release Drafter 已生成的发布说明）。

## 6. 线上紧急修复（Hotfix）

```bash
bash scripts/gitflow.sh hotfix start 1.5.1
# 修复 bug -> 提交 -> 推送
git push -u origin hotfix/1.5.1
# PR → main；合并后打 v1.5.1 标签，并回合并 develop
```

## 7. CI 会检查什么

| 检查 | 工作流 | 说明 |
|------|--------|------|
| 后端测试 | `ci.yml` | Python 3.11 + pytest + 覆盖率 |
| 前端构建 | `ci.yml` | ESLint（只读）+ Vite 构建 |
| CI 聚合门禁 | `ci.yml` | `ci-pass`，Ruleset 的必需检查 |
| 分支规范 | `gitflow.yml` | PR 目标/来源分支校验 |
| PR 标题 | `gitflow.yml` | Conventional Commits 校验 |
| 提交信息 | `gitflow.yml` | commitlint 校验 PR 内所有提交 |
| 冲突标记 | `gitflow.yml` | 阻止未解决的冲突标记 |
| 代码安全 | `codeql.yml` | CodeQL Python / JavaScript 扫描 |
| 依赖安全 | `dependency-review.yml` | 阻止引入高危依赖 |
| 密钥扫描 | `secret-scan.yml` | gitleaks 全历史扫描 |
| 供应链评分 | `scorecard.yml` | OpenSSF Scorecard（每周） |
| 工作流校验 | `workflow-lint.yml` | actionlint |
| Docker | `docker-build.yml` | PR 构建后端/前端镜像 |
| 发布说明 | `release-drafter.yml` | 自动生成草稿 |
| 回合并 | `sync-main-into-develop.yml` | main 更新后自动创建 → develop PR |
| 依赖更新 | `dependabot.yml` | 每周自动 PR（目标 `develop`） |
| 代码审查 | CodeRabbit | 自动 AI 审查（`.coderabbit.yaml`） |

> 本地先跑测试再推送：`cd garden-asset-platform/backend && python -m pytest`；前端 `cd garden-asset-platform/frontend && npm run lint:check && npm run build`。

## 8. 代码组织约定

- 后端：`resources/` 只做参数校验与响应，业务逻辑放 `services/`，数据模型放 `models/`。
- 前端：页面放 `views/`，可复用组件放 `components/`，API 调用统一走 `api/`。
- 新增环境变量必须同步更新 `.env.example`，禁止提交真实密钥。
- 水印 / 区块链 / AI 相关改动必须补充对应测试。

## 9. 安全

发现安全漏洞请勿公开提 Issue，按 [SECURITY.md](SECURITY.md) 私下报告。
