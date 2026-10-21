# Git Flow 工作流说明

本文档是本仓库分支管理的唯一权威说明；日常操作速查见 [CONTRIBUTING.md](../CONTRIBUTING.md)。

## 1. 两条长期分支

| 分支 | 角色 | 保护规则 |
|------|------|----------|
| `main` | 生产分支，任何提交都应可发布 | 禁止直推、禁止强推、禁止删除；PR 必须来自 `release/*` 或 `hotfix/*`（Dependabot 安全更新 `dependabot/*` 例外）；批准要求见 §5；CI/CodeQL/Dependency Review 全绿 |
| `develop` | 集成分支，下一版本的内容都先进入这里 | 禁止直推、禁止强推；PR 来源必须是允许的分支前缀；批准要求见 §5；CI 全绿 |

## 2. 生命周期

### 功能开发（feature）

```
develop ──●──────────────●──→ develop
           \            /
            ●──●──●──●──●   feature/watermark-robustness
```

1. 从最新 `develop` 创建 `feature/<slug>`。
2. 小步提交，提交信息遵循 Conventional Commits。
3. 推送并发起 PR → `develop`。
4. CI 全绿、审查通过后 Squash 合并，删除分支。

### 发布（release）

```
develop ──●───●───●───●──────────────●──→ develop
               \                    /
release/1.5.0   ●──●──●────────────●      （只做版本准备）
                     \              \
main                  ●──────────────●──→ main   + tag v1.5.0
```

1. 从 `develop` 创建 `release/<x.y.z>`。
2. 只允许：版本号、CHANGELOG、发布配置、必要的发布修复。禁止加入新功能。
3. PR → `main`，合并后打 `v<x.y.z>` 标签。
4. 必须在 `develop` 上回合并 release 分支，避免版本提交丢失。
5. 删除 release 分支。

### 紧急修复（hotfix）

```
main   ●────────────●────────→ main  + tag v1.5.1
        \          /
hotfix/1.5.1 ●──●
              \
develop        ●──────────────→ develop（回合并）
```

流程与 release 相同，但分支从 `main` 拉出，版本号在补丁位 +1，修复完成后必须回合并 `develop`。

## 3. 合并策略

| PR 类型 | 合并方式 | 原因 |
|---------|----------|------|
| `feature/*` → `develop` | Squash and merge | 一个功能一个提交，历史干净 |
| `bugfix/*` `docs/*` `ci/*` → `develop` | Squash and merge | 同上 |
| `release/*` → `main` | Merge commit | 保留发布边界 |
| `hotfix/*` → `main` | Merge commit | 保留热修边界 |
| 发布分支回合并 `develop` | Merge commit | 保留版本对齐关系 |

发布/热修分支会同时产生 `main` 与 `develop` 的合并提交，这是 Git Flow 的预期行为。

## 4. 版本号（SemVer）

- 主版本：不兼容的 API 或数据结构变更
- 次版本：向后兼容的新功能（`release/*` 常规发布）
- 补丁版本：向后兼容的缺陷修复（`hotfix/*`）

标签格式：`vMAJOR.MINOR.PATCH`，例如 `v1.5.0`。标签只在 `main` 上创建，且必须指向发布合并提交。

每次发布同步更新：

- `garden-asset-platform/frontend/package.json` 的 `version`
- `garden-asset-platform/CHANGELOG.md`（Keep a Changelog 格式）

## 5. 分支保护与 CI 强制

GitHub 侧使用仓库 Ruleset（脚本 `scripts/setup-github.sh` 可自动创建）：

- `main`：Require PR（当前 0 人批准，单人项目；添加协作者后应改为 1）+ 必需检查 `ci-pass`、`branch-policy`、`pr-title`、`commitlint`、`conflict-check`、`gitleaks`、`dependency-review`、`analyze (python)`、`analyze (javascript-typescript)` + 分支必须最新 + Block force pushes + Restrict deletions。
- `develop`：Require PR（同上）+ 必需检查 `ci-pass`、`branch-policy`、`pr-title`、`commitlint`、`conflict-check`、`gitleaks`、`dependency-review` + Block force pushes。
- 合并后自动删除 head 分支。
- `v*` 标签受保护：禁止删除或移动。

> 单人项目无法自我批准（GitHub 不允许 PR 作者批准自己的 PR），因此批准数设为 0；CI、CodeRabbit 与 Ruleset 仍然强制。新增协作者后请把 `required_approving_review_count` 调整为 1。

### 空仓库首次推送

仓库刚创建时 `main` / `develop` 尚不存在，而 Ruleset 在创建分支时也会要求状态检查。使用一次性脚本：

```bash
bash scripts/bootstrap-push.sh
```

脚本会临时把 `protect-main` / `protect-develop` 设为 `disabled`，推送 `main`、`develop` 与两个 feature 分支后自动恢复 `active`。仅在空仓库首次推送时使用。

工作流 `gitflow.yml` 会在每次 PR 时检查来源/目标分支组合，配置错误会直接红灯。

> **Dependabot 安全更新**：GitHub 的安全更新 PR 固定指向默认分支 `main`，不受 `target-branch` 控制。因此 `main` 额外接受 `dependabot/*`，并跳过标题与 commit 信息检查；自动合并按目标分支选择 merge commit（main）或 squash（develop）。合并到 main 后必须回合并 `develop`。

## 6. 常见问题

**可以直接 push 到 develop 吗？**
不可以。本地 `pre-push` 钩子会拦截，GitHub Ruleset 也会拒绝。唯一例外是仓库初始化，用 `ALLOW_DIRECT_PUSH=1 git push` 一次性放行。

**hotfix 合并进 main 后忘了回合并 develop 怎么办？**
立即补一个 `hotfix/<same-version>` → `develop` 的 PR（分支已删除时可从 main 拉 `bugfix/backport-x.y.z`），确保修复进入下一次发布。

**release 分支合并到 main 后 CI 挂了怎么办？**
在 release 分支上修复、重新推送；不要在 main 上直接改动。main 已打标签时，用新的 hotfix 版本发布修正。

**为什么 CI 只在 garden-asset-platform 目录跑？**
仓库仍保留历史资料目录；工作流通过 `paths` 过滤，只有 `garden-asset-platform/**` 的改动会触发构建与测试，节省 Actions 配额。

**Dependabot 的 PR 目标分支是什么？**
`develop`。所有依赖更新同样走 PR + CI，不允许直接合入 `main`。
