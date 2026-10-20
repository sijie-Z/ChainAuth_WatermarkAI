#!/usr/bin/env bash
# GitHub 仓库初始化：标签、合并策略、安全开关、分支 Ruleset
# 前置条件：安装官方 GitHub CLI 并登录（gh auth login）
#
# 用法:
#   bash scripts/setup-github.sh                 # 全部执行
#   bash scripts/setup-github.sh labels          # 只同步标签
#   bash scripts/setup-github.sh settings        # 只改仓库设置
#   bash scripts/setup-github.sh rulesets        # 只创建/更新分支规则
set -euo pipefail

REPO="${REPO:-sijie-Z/ChainAuth_WatermarkAI}"
MODE="${1:-all}"

if ! command -v gh >/dev/null 2>&1; then
  echo "❌ 未找到官方 GitHub CLI（gh）。" >&2
  echo "   Windows: winget install --id GitHub.cli -e" >&2
  echo "   然后: gh auth login" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "❌ GitHub CLI 未登录，请先执行: gh auth login" >&2
  exit 1
fi

echo "➜ 目标仓库: $REPO"

sync_labels() {
  echo "➜ 同步标签"
  while IFS='|' read -r name color desc; do
    [ -z "$name" ] && continue
    gh label create "$name" --color "$color" --description "$desc" --force >/dev/null
  done <<'LABELS'
bug|d73a4a|Something isn't working
fix|d73a4a|缺陷修复
feature|a2eeef|新功能
enhancement|a2eeef|功能改进
docs|0075ca|文档
documentation|0075ca|文档
ci|1d76db|CI / 工作流
tests|0e8a16|测试
dependencies|0366d6|依赖更新
backend|5319e7|后端
frontend|fbca04|前端
watermark|8b5cf6|数字水印
blockchain|24292e|区块链存证
ai|ff6b6b|AI / 溯源
docker|0db7ed|Docker / 部署
security|b60205|安全
performance|fbca04|性能
refactor|d4c5f9|重构
chore|ededed|杂项
needs-triage|fbca04|待分类
stale|ededed|长期无活动
pinned|0052cc|固定，不自动关闭
skip-changelog|ededed|不进入发布说明
major|b60205|主版本更新
minor|fbca04|次版本更新
patch|0e8a16|补丁版本更新
breaking-change|b60205|破坏性变更
good first issue|7057ff|适合新贡献者
LABELS
  echo "✅ 标签同步完成"
}

configure_settings() {
  echo "➜ 更新仓库合并与功能设置"
  gh api --method PATCH "repos/$REPO" --input - <<'JSON' >/dev/null
{
  "has_issues": true,
  "has_wiki": false,
  "has_projects": false,
  "allow_squash_merge": true,
  "allow_merge_commit": true,
  "allow_rebase_merge": false,
  "allow_auto_merge": true,
  "delete_branch_on_merge": true,
  "squash_merge_commit_title": "PR_TITLE",
  "squash_merge_commit_message": "PR_BODY",
  "merge_commit_title": "PR_TITLE",
  "merge_commit_message": "PR_BODY",
  "web_commit_signoff_required": false
}
JSON

  echo "➜ 启用私密漏洞报告"
  gh api --method PUT "repos/$REPO/private-vulnerability-reporting" >/dev/null 2>&1 \
    || echo "   (跳过：仓库不支持或已启用)"

  echo "➜ 启用 secret scanning / push protection"
  if ! gh api --method PATCH "repos/$REPO" --input - >/dev/null 2>&1 <<'JSON'
{
  "security_and_analysis": {
    "secret_scanning": { "status": "enabled" },
    "secret_scanning_push_protection": { "status": "enabled" }
  }
}
JSON
  then
    echo "   (跳过：需要 GitHub Code Security，公开仓库通常可用)"
  fi

  echo "➜ 启用 Dependabot alerts / 安全修复"
  gh api --method PUT "repos/$REPO/vulnerability-alerts" >/dev/null 2>&1 \
    || echo "   (跳过：Dependabot alerts 启用失败)"
  gh api --method PUT "repos/$REPO/automated-security-fixes" >/dev/null 2>&1 \
    || echo "   (跳过：automated-security-fixes 启用失败)"

  echo "➜ 设置 Actions 默认权限为只读"
  gh api --method PUT "repos/$REPO/actions/permissions/workflow" --input - >/dev/null 2>&1 <<'JSON' \
    || echo "   (跳过：Actions 权限设置失败)"
{
  "default_workflow_permissions": "read",
  "can_approve_pull_request_reviews": false
}
JSON

  echo "➜ 设置 topics"
  gh repo edit "$REPO" \
    --add-topic digital-watermark \
    --add-topic blockchain \
    --add-topic fisco-bcos \
    --add-topic vue3 \
    --add-topic flask \
    --add-topic copyright-protection \
    --add-topic ai-traceability \
    --add-topic digital-heritage >/dev/null 2>&1 \
    || echo "   (跳过：topics 设置失败)"

  echo "✅ 仓库设置完成"
}

upsert_ruleset() {
  local name="$1"
  local payload="$2"
  local existing_id
  existing_id="$(gh api "repos/$REPO/rulesets" --jq ".[] | select(.name == \"$name\") | .id" 2>/dev/null || true)"
  if [ -n "$existing_id" ]; then
    echo "➜ 更新 Ruleset: $name (id=$existing_id)"
    printf '%s' "$payload" | gh api --method PUT "repos/$REPO/rulesets/$existing_id" --input - >/dev/null
  else
    echo "➜ 创建 Ruleset: $name"
    printf '%s' "$payload" | gh api --method POST "repos/$REPO/rulesets" --input - >/dev/null
  fi
}

configure_rulesets() {
  echo "➜ 配置分支保护 Ruleset"

  # main：生产分支，最严格；发布只允许 release/* 与 hotfix/*
  upsert_ruleset "protect-main" '{
    "name": "protect-main",
    "target": "branch",
    "enforcement": "active",
    "conditions": {
      "ref_name": { "include": ["refs/heads/main"], "exclude": [] }
    },
    "rules": [
      { "type": "deletion" },
      { "type": "non_fast_forward" },
      {
        "type": "pull_request",
        "parameters": {
          "required_approving_review_count": 0,
          "dismiss_stale_reviews_on_push": false,
          "require_code_owner_review": false,
          "require_last_push_approval": false,
          "required_review_thread_resolution": true,
          "allowed_merge_methods": ["merge"]
        }
      },
      {
        "type": "required_status_checks",
        "parameters": {
          "strict_required_status_checks_policy": true,
          "do_not_enforce_on_create": false,
          "required_status_checks": [
            { "context": "ci-pass" },
            { "context": "branch-policy" },
            { "context": "pr-title" },
            { "context": "commitlint" },
            { "context": "conflict-check" },
            { "context": "gitleaks" },
            { "context": "dependency-review" },
            { "context": "analyze (python)" },
            { "context": "analyze (javascript-typescript)" }
          ]
        }
      }
    ],
    "bypass_actors": []
  }'

  # develop：集成分支；功能分支经 Squash 进入
  upsert_ruleset "protect-develop" '{
    "name": "protect-develop",
    "target": "branch",
    "enforcement": "active",
    "conditions": {
      "ref_name": { "include": ["refs/heads/develop"], "exclude": [] }
    },
    "rules": [
      { "type": "deletion" },
      { "type": "non_fast_forward" },
      {
        "type": "pull_request",
        "parameters": {
          "required_approving_review_count": 0,
          "dismiss_stale_reviews_on_push": false,
          "require_code_owner_review": false,
          "require_last_push_approval": false,
          "required_review_thread_resolution": true,
          "allowed_merge_methods": ["squash", "merge"]
        }
      },
      {
        "type": "required_status_checks",
        "parameters": {
          "strict_required_status_checks_policy": false,
          "do_not_enforce_on_create": false,
          "required_status_checks": [
            { "context": "ci-pass" },
            { "context": "branch-policy" },
            { "context": "pr-title" },
            { "context": "commitlint" },
            { "context": "conflict-check" },
            { "context": "gitleaks" },
            { "context": "dependency-review" }
          ]
        }
      }
    ],
    "bypass_actors": []
  }'

  # 版本标签保护：禁止删除/移动 v* 标签
  upsert_ruleset "protect-release-tags" '{
    "name": "protect-release-tags",
    "target": "tag",
    "enforcement": "active",
    "conditions": {
      "ref_name": { "include": ["refs/tags/v*"], "exclude": [] }
    },
    "rules": [
      { "type": "deletion" },
      { "type": "non_fast_forward" },
      { "type": "update" }
    ],
    "bypass_actors": []
  }'

  echo "✅ Ruleset 配置完成"
}

case "$MODE" in
  labels)    sync_labels ;;
  settings)  configure_settings ;;
  rulesets)  configure_rulesets ;;
  all)
    sync_labels
    configure_settings
    configure_rulesets
    ;;
  *)
    echo "用法: bash scripts/setup-github.sh [labels|settings|rulesets|all]" >&2
    exit 1
    ;;
esac

echo ""
echo "✅ 完成。别忘了在 GitHub 上安装 CodeRabbit App: https://github.com/apps/coderabbitai"
