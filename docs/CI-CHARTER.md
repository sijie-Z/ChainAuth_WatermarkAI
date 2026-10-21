# CI 章程

> 本文件定义 CI 的边界：有哪些门禁、各自管什么、什么时候该加、什么时候该删。**改 CI 之前先读它。**
> 参考来源：作者在 `DocMind-RAG` 中沉淀的 CI 章程（见 `docs/REFERENCE-NOTES.md`）。

## 1. 目标

用尽量短的墙钟时间，在合并前拦住真实回归；拦不住的部分必须在 nightly / 每周例行中**真实执行**——挂在页面上当绿装饰的检查等于不存在。

## 2. 门禁全景

### PR / push 门禁

| 工作流 | 检查 | 触发 | 阻断 | 超时 |
|--------|------|------|------|------|
| `ci.yml` | 后端 ruff（致命规则）+ pytest + 覆盖率 | PR / push → main/develop | ✅ | 20 min |
| `ci.yml` | 前端 ESLint（只读）+ Vitest 单元测试 + Vite 构建 | PR / push → main/develop | ✅ | 15 min |
| `ci.yml` | `ci-pass` 聚合门禁 | 同上 | ✅ | 5 min |
| `gitflow.yml` | 分支来源/目标校验 | PR → main/develop | ✅ | 5 min |
| `gitflow.yml` | PR 标题 Conventional Commits | PR → main/develop | ✅ | 5 min |
| `gitflow.yml` | commitlint（PR 内提交） | PR → main/develop | ✅ | 10 min |
| `gitflow.yml` | 冲突标记扫描 | PR → main/develop | ✅ | 5 min |
| `dependency-review.yml` | 新增依赖漏洞（runtime + development，high+） | PR → main/develop | ✅ | 10 min |
| `secret-scan.yml` | gitleaks 全历史扫描 | push / PR / 每周 | ✅ | 15 min |
| `codeql.yml` | CodeQL（python + javascript-typescript） | push / PR / 每周 | ✅ | 30 min |
| `workflow-lint.yml` | actionlint | 工作流文件变化 | ✅ | 10 min |
| `docker-build.yml` | 后端/前端镜像构建 | Docker 相关文件变化 | ✅ | 25 min |
| `e2e.yml` | Playwright 前端点击流 + 真实后端 | `garden-asset-platform/**` 变化 | ✅（暂未加入 Ruleset 必需检查） | 25 min |
| `labeler.yml` | 路径标签 | PR | ❌（辅助） | 5 min |
| `welcome.yml` | 首次贡献欢迎 | Issue/PR | ❌（辅助） | 5 min |
| `dependabot-auto-merge.yml` | 依赖 PR 自动合并 | Dependabot PR | ❌（辅助） | 10 min |

### 非 PR 工作流

| 工作流 | 职责 | 频率 |
|--------|------|------|
| `sync-main-into-develop.yml` | main 更新后创建回合并提醒 issue（GITHUB_TOKEN 建的 PR 不会触发必需检查） | 每次 main push |
| `release-drafter.yml` | 维护发布说明草稿 | 每次 main push |
| `release.yml` | 发布 Release + 推送 GHCR 镜像 | 标签 `v*` |
| `stale.yml` | 标记/关闭长期无活动 Issue/PR | 每周一 |
| `scorecard.yml` | OpenSSF 供应链评分 | 每周一 + main push |
| `dependency-review.yml` | PR 依赖审查 | 每个 PR |
| `codeql.yml` / `secret-scan.yml` | 定期补扫 | 每周一 |

## 3. main / develop 的语义

- **develop**：集成分支。合入 = 已过 PR 门禁；判断“链路是否通”以 develop 为准。
- **main**：发版分支，只在发布时更新。main 上的绿只代表某个发布快照。
- 发布必须经过 `release/*` 或 `hotfix/*` 分支；`main` 不接受来自 `develop` 的直接 PR。

## 4. 明确不做的事

| 不做 | 原因 |
|------|------|
| mypy / 全量类型检查 | 当前代码为纯 JS + 无类型注解 Python，整改成本大于收益 |
| SonarCloud / Codecov 上传 | 需要额外账号与 Token；覆盖率以 artifact 形式保留，不设外部依赖 |
| license gate | 暂无许可证合规策略；Dependency Review 只阻断高危漏洞 |
| bandit | CodeQL 已覆盖语义级安全扫描；若后续需要 bandit，必须按 §7 验证 fail-closed 后加入 |
| 自动 semantic-release | 版本号由发布分支人工确认，避免自动改版本 |

## 5. 时间 / 墙钟预算

- 快速门禁（PR 必需）目标：**≤ 6 分钟**（后端测试 ~2-3 分钟，前端 ~1-2 分钟）。
- 每个 job 必须设置 `timeout-minutes`，超时即失败（`ci-pass` 除外，仅做聚合）。
- Docker 构建与 CodeQL 不进入快速路径的关键依赖；它们并行执行，不阻塞 `ci-pass` 的判定（但属于 Ruleset 必需检查的，必须在合并前完成）。
- 同一分支的新 push 取消旧 run（`concurrency.cancel-in-progress: true`）。

## 6. 覆盖率策略

- 当前基线：**49%**（88 个后端用例 + 41 个前端用例 + 5 个 Playwright 用例，2026-10-20 实测）。
- CI 使用棘轮下限 `--cov-fail-under=43`（留 2 个点余量防环境波动），只拦“继续下滑”，不追高分；下限写在 CI 命令里，不写进全局 pytest 配置。
- 覆盖率报告以 artifact 形式保存（7 天），不依赖外部 Codecov 账号。
- 前端已加入 Vitest 单元测试（工具函数与共享组件）；覆盖率暂不作为门禁，后续按棘轮方式引入。

## 7. Security 工具职责边界

| 工具 | 管什么 | 触发 | 阻断 |
|------|--------|------|------|
| CodeQL | 语义级漏洞（数据流） | PR / push / 每周 | ✅ |
| Dependency Review | 本 PR 新增依赖的已知漏洞（runtime + development） | PR | high+ |
| gitleaks | 密钥/凭据泄露（含历史） | push / PR / 每周 | ✅ |
| OpenSSF Scorecard | 供应链与仓库配置评分 | 每周 + main | ❌（报告） |
| Dependabot | 存量依赖更新 | 每周 | 走 PR |
| 本地 pre-commit | 私钥 / 令牌 / 大文件 / 冲突标记 | 每次提交 | ✅ |

## 8. Fail-closed 原则

- **工具崩溃 / 报告解析失败 = 红，不是绿。**
- 新增检查时，至少构造一次“预期失败场景”和一次“工具异常场景”，证明它不会在检查失效时错误地返回 green。
- **一个永远绿的检查，比没有检查更危险。**
- 仅报告的检查必须在名称或摘要中标注 `advisory`，避免把绿勾误读为“没有问题”。

## 9. 什么时候允许新增 CI

仅在出现“现有 CI 无法发现的**真实回归类型**”时。新增前回答三问：

1. 这个回归真实发生过（或高概率）吗？
2. 哪个现有 job 覆盖不了它？
3. 失败场景演示过了吗（§8）？

## 10. 什么时候必须删除 / 收缩 CI

- 连续 30 天没红过、**也没拦下过任何东西**（先区分“没红”与“没跑”）。
- 它发现的问题已有更早的门禁覆盖。
- 它长期红 / 跳过且无人修（orphan gate）。
- 它拦的是仅报告性质、修复受上游制约的问题（降级为 advisory）。

## 11. 停止扩张的达成条件

以下条件全部满足后，不再主动增加 CI 检查：

- PR 快速门禁 ≤ 6 分钟
- 后端测试稳定，覆盖率有棘轮下限
- 前端 lint + build 稳定
- CodeQL、Dependency Review、gitleaks 有效执行
- 回合并（main → develop）自动化真实运行
- 所有阻断检查均通过“失败场景验证”

之后只有出现“现有 CI 无法发现的真实回归类型”时，才允许新增（回到 §9）。
