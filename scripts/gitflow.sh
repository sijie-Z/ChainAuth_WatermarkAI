#!/usr/bin/env bash
# 轻量 Git Flow 助手（无需安装 git-flow 扩展）
# 分支模型: main（生产） / develop（集成） / feature / release / hotfix
#
# 用法:
#   bash scripts/gitflow.sh feature start <名称>
#   bash scripts/gitflow.sh feature finish <名称>
#   bash scripts/gitflow.sh release start <x.y.z>
#   bash scripts/gitflow.sh release finish <x.y.z>
#   bash scripts/gitflow.sh hotfix start <x.y.z>
#   bash scripts/gitflow.sh hotfix finish <x.y.z>
#   bash scripts/gitflow.sh sync
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
cd "$ROOT_DIR"

die() { echo "❌ $*" >&2; exit 1; }
info() { echo "➜ $*"; }

has_remote() { git remote get-url origin >/dev/null 2>&1; }

require_clean() {
  [ -z "$(git status --porcelain)" ] || die "工作区不干净，请先提交或暂存改动"
}

ensure_branch() {
  git show-ref --verify --quiet "refs/heads/$1" || die "分支 $1 不存在（首次使用请先创建: git branch $1 main）"
}

sync_branch() {
  local branch="$1"
  ensure_branch "$branch"
  info "切换到 $branch 并同步远端"
  git switch "$branch"
  if has_remote; then
    git pull --ff-only origin "$branch"
  fi
}

slugify() {
  printf '%s' "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9._-]+/-/g; s/^-+//; s/-+$//'
}

validate_version() {
  [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "版本号必须形如 1.5.0（语义化版本）"
}

cmd="${1:-}"
action="${2:-}"
arg="${3:-}"

case "$cmd:$action" in
  feature:start)
    [ -n "$arg" ] || die "用法: gitflow.sh feature start <名称>"
    name="$(slugify "$arg")"
    [ -n "$name" ] || die "名称无效"
    sync_branch develop
    git switch -c "feature/$name"
    info "已创建 feature/$name，开始开发吧"
    ;;

  feature:finish)
    [ -n "$arg" ] || die "用法: gitflow.sh feature finish <名称>"
    name="$(slugify "$arg")"
    require_clean
    ensure_branch "feature/$name"
    sync_branch develop
    info "合并 feature/$name → develop (--no-ff)"
    git merge --no-ff "feature/$name" -m "Merge branch 'feature/$name' into develop"
    git branch -d "feature/$name"
    info "完成。推送: git push origin develop（建议改走 Pull Request）"
    ;;

  release:start)
    [ -n "$arg" ] || die "用法: gitflow.sh release start <x.y.z>"
    validate_version "$arg"
    sync_branch develop
    git switch -c "release/$arg"
    info "已创建 release/$arg：只允许版本号、CHANGELOG、发布配置的改动"
    info "发布前检查通过后: bash scripts/gitflow.sh release finish $arg"
    ;;

  release:finish)
    [ -n "$arg" ] || die "用法: gitflow.sh release finish <x.y.z>"
    validate_version "$arg"
    require_clean
    ensure_branch "release/$arg"

    sync_branch main
    info "合并 release/$arg → main (--no-ff)"
    git merge --no-ff "release/$arg" -m "Merge branch 'release/$arg' into main"
    info "打标签 v$arg"
    git tag -a "v$arg" -m "Release v$arg"

    sync_branch develop
    info "回合并 release/$arg → develop (--no-ff)"
    git merge --no-ff "release/$arg" -m "Merge branch 'release/$arg' into develop"
    git branch -d "release/$arg"

    info "完成。推送（GitHub 写操作请小批量执行）:"
    echo "   git push origin main"
    echo "   git push origin develop"
    echo "   git push origin v$arg"
    ;;

  hotfix:start)
    [ -n "$arg" ] || die "用法: gitflow.sh hotfix start <x.y.z>"
    validate_version "$arg"
    sync_branch main
    git switch -c "hotfix/$arg"
    info "已创建 hotfix/$arg：修复后执行 bash scripts/gitflow.sh hotfix finish $arg"
    ;;

  hotfix:finish)
    [ -n "$arg" ] || die "用法: gitflow.sh hotfix finish <x.y.z>"
    validate_version "$arg"
    require_clean
    ensure_branch "hotfix/$arg"

    sync_branch main
    info "合并 hotfix/$arg → main (--no-ff)"
    git merge --no-ff "hotfix/$arg" -m "Merge branch 'hotfix/$arg' into main"
    info "打标签 v$arg"
    git tag -a "v$arg" -m "Hotfix v$arg"

    sync_branch develop
    info "回合并 hotfix/$arg → develop (--no-ff)"
    git merge --no-ff "hotfix/$arg" -m "Merge branch 'hotfix/$arg' into develop"
    git branch -d "hotfix/$arg"

    info "完成。推送: git push origin main develop v$arg"
    ;;

  sync:)
    require_clean
    sync_branch develop
    ;;

  *)
    cat <<'USAGE'
Git Flow 助手

  bash scripts/gitflow.sh feature start <名称>
  bash scripts/gitflow.sh feature finish <名称>
  bash scripts/gitflow.sh release start <x.y.z>
  bash scripts/gitflow.sh release finish <x.y.z>
  bash scripts/gitflow.sh hotfix start <x.y.z>
  bash scripts/gitflow.sh hotfix finish <x.y.z>
  bash scripts/gitflow.sh sync

分支模型:
  main      生产分支，只接受 release/* 与 hotfix/* 的 PR
  develop   集成分支，功能分支的合并目标
  feature/* 新功能（从 develop 拉出）
  release/* 发布准备（从 develop 拉出，合入 main 后回合并 develop）
  hotfix/*  线上紧急修复（从 main 拉出，合入 main 后回合并 develop）
USAGE
    exit 1
    ;;
esac
