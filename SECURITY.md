# 安全政策（Security Policy）

## 支持范围

| 版本 | 是否接收安全修复 |
|------|------------------|
| 最新 `main` 发布版（v1.x） | ✅ |
| 更早版本 | ❌ 请先升级 |

## 报告漏洞

**请勿通过公开 Issue 报告安全漏洞。**

优先使用 GitHub 的私密报告入口：

1. 打开仓库 **Security → Advisories → Report a vulnerability**
2. 填写影响范围、复现步骤、可能的修复建议

我们会在 3 个工作日内确认收到，并在修复发布后致谢（如你愿意署名）。

## 重点关注的问题类型

- JWT / 会话 / 权限绕过（越权访问资产、审批流）
- 文件上传绕过（魔数校验、路径穿越、XSS）
- 水印算法被移除或伪造（鲁棒性缺陷）
- 区块链存证数据不一致或可篡改
- API Key / 密钥泄露（`.env`、日志、前端打包产物）
- 依赖供应链漏洞

## 密钥与凭据

- 仓库只允许提交 `.env.example`，真实密钥通过环境变量注入。
- 若怀疑密钥泄露：立即在对应平台轮换，并清除 Git 历史中的泄露内容（`git filter-repo`）。
- CI 使用 GitHub Actions 内置 `GITHUB_TOKEN`，按最小权限声明 `permissions`。

## 安全相关 CI

- CodeQL：Python / JavaScript 静态扫描
- Dependency Review：PR 阻止引入高危依赖
- Dependabot：每周依赖更新与安全公告
