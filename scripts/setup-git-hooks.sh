#!/usr/bin/env bash
# 一键启用仓库内置 Git 钩子与常用配置
# 用法: bash scripts/setup-git-hooks.sh
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
cd "$ROOT_DIR"

git config core.hooksPath .githooks
chmod +x .githooks/* 2>/dev/null || true

# 常用配置
git config fetch.prune true
git config pull.ff only          # 拉取只允许快进，避免意外的合并提交
git config rebase.autoStash true

# 如果安装了 git-flow（AVH edition），顺手初始化分支约定
if command -v git-flow >/dev/null 2>&1; then
  git config gitflow.branch.master main
  git config gitflow.branch.develop develop
  git config gitflow.prefix.feature feature/
  git config gitflow.prefix.bugfix bugfix/
  git config gitflow.prefix.release release/
  git config gitflow.prefix.hotfix hotfix/
  git config gitflow.prefix.support support/
  git config gitflow.prefix.versiontag v
fi

echo "✅ Git 钩子已启用: core.hooksPath = .githooks"
echo "   - commit-msg  校验 Conventional Commits"
echo "   - pre-commit  拦截敏感文件 / 私钥 / 令牌 / 超大文件 / 冲突标记"
echo "   - pre-push    禁止直接推送 main / develop"
echo ""
echo "下一步:"
echo "   git switch develop   # 日常开发从 develop 拉功能分支"
echo "   bash scripts/gitflow.sh feature start <名称>"
