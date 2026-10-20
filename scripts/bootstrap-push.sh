#!/usr/bin/env bash
# 空仓库首次推送助手。
#
# 背景：main / develop 的 Ruleset 默认在“创建分支”时也要求必需状态检查，
# 而空仓库上还没有任何工作流运行过，直接 push 会被拒绝。
# 本脚本临时把两条规则降为 evaluate，推送四个分支后自动恢复 active。
#
# 用法：
#   bash scripts/bootstrap-push.sh
#   bash scripts/bootstrap-push.sh "D:/Desktop/MyProjects/_chainauth_filtered_ui.git"
#
# 依赖：SSH 可访问 GitHub；Git Credential Manager 中保存了有 repo 权限的 GitHub token。
set -euo pipefail

REPO="sijie-Z/ChainAuth_WatermarkAI"
MIRROR="${1:-D:/Desktop/MyProjects/_chainauth_filtered_ui.git}"
API="https://api.github.com/repos/${REPO}"

token=$(printf 'protocol=https\nhost=github.com\n\n' | git credential fill 2>/dev/null | sed -n 's/^password=//p' | head -n1 || true)
if [ -z "${token}" ]; then
  echo "未能从 Git Credential Manager 读取 GitHub token。请先执行 gh auth login 或配置 PAT。" >&2
  exit 1
fi

api() {
  curl -fsS -H "Accept: application/vnd.github+json" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${token}" \
    -H "X-GitHub-Api-Version: 2022-11-28" "$@"
}

ruleset_id() {
  local name="$1"
  api "${API}/rulesets" | RULESET_NAME="$name" python -c 'import json, os, sys
data = json.load(sys.stdin)
print(next(item["id"] for item in data if item["name"] == os.environ["RULESET_NAME"]))'
}

set_enforcement() {
  local name="$1" value="$2" id
  id=$(ruleset_id "$name")
  api -X PATCH "${API}/rulesets/${id}" -d "{\"enforcement\":\"${value}\"}" >/dev/null
  echo "  ${name} (id=${id}) -> ${value}"
}

restore() {
  echo "恢复分支保护…"
  set_enforcement protect-main active || true
  set_enforcement protect-develop active || true
}
trap restore EXIT

echo "临时降低分支保护，准备首次推送…"
set_enforcement protect-main evaluate
set_enforcement protect-develop evaluate
sleep 3

echo "推送 main / develop / feature 分支…"
git -C "${MIRROR}" push origin main develop feature/git-flow-ci-setup feature/ui-refresh

echo "完成。后续所有变更请走 PR，不要再直接推送 main / develop。"
