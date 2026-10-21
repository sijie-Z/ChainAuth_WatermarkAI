# 参考资料吸收记录

> 本文件记录本仓库在搭建 Git Flow / CI / 机器人之前，从本地参考项目与 GitHub 参考仓库中吸收的内容。
> 参考目录已在吸收完成后从工作区与 Git 历史中移除，原始出处仍可在 GitHub / 本地备份中找到。

## 1. 本地参考项目（已移除）

| 参考目录 | 内容 | 吸收到本仓库的内容 |
|----------|------|--------------------|
| `Spatial_Data_Tracking_System_lastvension - 副本/` | 旧版空间数据追踪系统：Flask + Vue3、双级审批、矢量/栅格水印、二维码溯源、旧版需求与设计资料 | 水印算法（DCT/QIM、矢量坐标扰动）、双重审批（adm1 + adm2）状态机、溯源查询流程、水印 ID 编码规则，均已迁移到 `garden-asset-platform/backend/algorithm` 与 `app/services`；旧版资料归档不再入库 |
| `Spatial.../Remote_sensing_image_algorithm_debug/CRMark-main/` | CRMark 遥感图像水印参考实现（DCT + BCH 纠错 + 压缩） | `watermark_service.py` 的鲁棒性参数与 BCH 纠错思路 |
| 旧版 Vue3 前端参考项目 | 旧版 Vue3 前端（无 package.json，无法独立构建） | 页面结构、导航信息架构、Element Plus 组件选型；新前端在 `garden-asset-platform/frontend` 重建 |
| `项目文档/` | 技术架构设计文档、开发日志 | **保留**，作为本系统设计依据 |

## 2. GitHub 参考仓库（仅吸收工程实践，不复制业务代码）

### `sijie-Z/GeoData-Security-System`（同领域前身项目）

- CI 结构：后端 ruff + 前端 lint/build + Playwright 无障碍审计 + Docker 构建/冒烟 + CodeQL + gitleaks + OpenSSF Scorecard
- 采纳：CodeQL、gitleaks、Scorecard、Docker 构建校验，以及“安全扫描作为常规 CI 的一部分”的思路

### `sijie-Z/DocMind-RAG`（Git Flow + 质量门禁参考）

- `CONTRIBUTING.md` 明确 `main` = 生产、`develop` = 集成、`feat/` / `fix/` / `docs/` 分支
- `ci-fast.yml` 使用 `ci-pass` 聚合任务作为唯一必需检查
- `ci-hygiene.yml`：commitlint（`wagoid/commitlint-github-action@v6`）、`actions/labeler@v5`、冲突标记扫描
- `dependency-review-action@v5`、Dependabot 显式 `target-branch: develop`
- 采纳：`ci-pass` 聚合门禁、commitlint、labeler、冲突扫描、依赖审查、Dependabot 目标分支

### `miqro-org/MiqroForge-Desktop`（Git Flow 自动化参考）

- `sync-main-into-develop.yml`：`main` 更新后自动创建回合并 PR
- `weekly-release.yml` / `release.yml`：发布列车与 semantic-release
- `pr-title-semantic-check.yml`：`amannn/action-semantic-pull-request@v6`
- `conflict-watchdog.yml`：定期扫描冲突
- 采纳：`main → develop` 自动回合并、Conventional Commits PR 标题校验、冲突扫描

### `sijie-Z/miqro-gate`（工程纪律参考）

- `docs/git-workflow.md`：分支命名、禁止直推 `main`、一个 Issue 一个 PR、push 不等于验收
- CI：path filter、shellcheck、多平台测试、OpenAPI 兼容检查、Playwright E2E、SBOM、actionlint
- 采纳：工作流 lint（actionlint）、Dependabot 目标 `develop`、分支保护与 PR 纪律；多平台/OpenAPI/SBOM 待项目规模扩大后再引入

## 3. 未采纳项与原因

| 参考做法 | 未采纳原因 |
|----------|------------|
| `develop → main` 直接 PR（MiqroForge weekly-release） | 与本仓库严格 Git Flow 冲突；本仓库要求 `release/*` / `hotfix/*` 才能进入 `main` |
| semantic-release 自动发版 | 当前版本号由发布分支人工确认，避免自动改版本；Release Drafter 负责发布说明草稿 |
| SonarCloud / Codecov 上传 | 需要额外账号与 Token；当前用本地覆盖率 artifact + CodeQL 替代 |
| `anthropics/claude-code-action` AI 审查 | 需要 Anthropic API Secret；已配置 CodeRabbit 作为默认 AI 审查，如需可后续加装 |

Playwright E2E 已采纳（5 个前端点击流用例，见 `.github/workflows/e2e.yml`）；后端测试为 194 个用例。

## 4. UI 设计参考（2026-10-19 补充）

前端从“绿色渐变模板”重构为“青绿山水 · 档案册”方向，吸收以下参考：

- 苏州博物馆官网：墨色/暖灰/朱砂的信号色关系、几何框架与印章式标识
- 故宫博物院数字文物库：松绿 + 古金 + 暖纸的档案气质、密集藏品网格、70/30 详情布局
- 故宫名画记：纸面 + 墨褐 + 宋体标题、时间轴与画作查看器层级
- 数字藏经洞：羊皮纸/朱砂/深褐的证书纸面层
- Han Design（GitHub）：青绿山水/水墨/青瓷 token 结构与“朱砂 ≤5%、金 <3%”的克制原则
- cultural-relics-museum（GitHub）：验证过的中式深色界面与金/朱砂/玉色比例
- vue-pure-admin / Geeker-Admin / Soybean Admin：后台壳几何与 Element Plus token 思路

详细令牌、页面模式与禁用项见 [UI-DESIGN.md](UI-DESIGN.md)。

## 5. 删除记录

- 已删除：`Spatial_Data_Tracking_System_lastvension - 副本/`、`Collegiate_Computing_Competition/`
- 已从待发布的改写历史中剔除上述路径（`git filter-repo`），避免账号密码、GeoScene 许可证等文件进入公开仓库；原始本地仓库的旧历史仅保留在本机，禁止推送
- 保留：`garden-asset-platform/`、`项目文档/`
