#!/usr/bin/env bash
# 空仓库首次推送助手。
#
# 背景：main / develop 的 Ruleset 默认在“创建分支”时也要求必需状态检查，
# 而空仓库上还没有任何工作流运行过，直接 push 会被拒绝。
# 本脚本临时把两条规则设为 disabled，推送四个分支后自动恢复 active。
#
# 用法：
#   bash scripts/bootstrap-push.sh
#   bash scripts/bootstrap-push.sh "D:/Desktop/MyProjects/_chainauth_filtered_ui.git"
#
# 依赖：SSH 可访问 GitHub；Git Credential Manager 中保存了 GitHub token。
# 注意：ruleset 更新走 GraphQL（REST PATCH 对 OAuth token 会返回 404）。
# 如果 token 仍无权限，请在仓库 Settings → Rules 里临时把
# protect-main / protect-develop 设为 Disabled，推送后再改回 Active。
set -euo pipefail

REPO="sijie-Z/ChainAuth_WatermarkAI"
MIRROR="${1:-D:/Desktop/MyProjects/_chainauth_filtered_ui.git}"

token=$(printf 'protocol=https\nhost=github.com\n\n' | git credential fill 2>/dev/null | sed -n 's/^password=//p' | head -n1 || true)
if [ -z "${token}" ]; then
  echo "未能从 Git Credential Manager 读取 GitHub token。请先执行 gh auth login 或配置 PAT。" >&2
  exit 1
fi

graphql() {
  local query="$1"
  QUERY="$query" python -c 'import json, os; print(json.dumps({"query": os.environ["QUERY"]}))' \
    | curl -fsS -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${token}" \
        https://api.github.com/graphql -d @-
}

ruleset_node_id() {
  local name="$1"
  graphql 'query { repository(owner:"sijie-Z", name:"ChainAuth_WatermarkAI") { rulesets(first:50) { nodes { id name } } } }' \
    | RULESET_NAME="$name" python -c 'import json, os, sys
data = json.load(sys.stdin)
nodes = data["data"]["repository"]["rulesets"]["nodes"]
print(next(item["id"] for item in nodes if item["name"] == os.environ["RULESET_NAME"]))'
}

set_enforcement() {
  local name="$1" value="$2" id upper
  id=$(ruleset_node_id "$name")
  upper=$(printf '%s' "$value" | tr '[:lower:]' '[:upper:]')
  if ! graphql "mutation { updateRepositoryRuleset(input:{repositoryRulesetId:\"${id}\", enforcement:${upper}}) { ruleset { name enforcement } } }" >/dev/null; then
    echo "修改 ${name} 失败：token 无 ruleset 写权限。请在仓库 Settings → Rules 临时把 ${name} 设为 Disabled 后重试。" >&2
    return 1
  fi
  echo "  ${name} -> ${value}"
}

restore() {
  echo "恢复分支保护…"
  set_enforcement protect-main active || true
  set_enforcement protect-develop active || true
}
trap restore EXIT

echo "临时关闭分支保护，准备首次推送…"
set_enforcement protect-main disabled
set_enforcement protect-develop disabled
sleep 3

echo "推送 main / develop / feature 分支…"
git -C "${MIRROR}" push origin main develop feature/git-flow-ci-setup feature/ui-refresh

echo "完成。后续所有变更请走 PR，不要再直接推送 main / develop。"
