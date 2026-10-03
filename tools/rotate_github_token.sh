#!/usr/bin/env bash
# rotate_github_token.sh —— GitHub PAT 一键轮换（服务器端执行）
#
# 覆盖点 / What this script updates
# ──────────────────────────────────
#   1. ~/.github_token                 主 token 文件（原子写入 + chmod 600）
#   2. /home/ubuntu/fstdd-git/stdd-repo.git       bare repo, remote=github, 自动跟随
#   3. /home/ubuntu/fstdd-git/fstdd-hub.git       bare repo, hook 已改为 ~/.github_token 动态读取
#   4. /home/ubuntu/Fstdd-experiences-repo        working clone, remote=origin
#   5. mirror-failed.flag              清除上一轮遗留标记
#   6. fstdd-hub-mirror-failed.flag    同上
#
# 不覆盖 / NOT covered
# ─────────────────────
#   - GitHub Actions secret GH_MIRROR_TOKEN  (GitHub 侧操作，需 gh CLI，见脚本末尾 gh 命令)
#   - Windows Store python stub             (PAT 轮换不涉及)
#
# 用法 / Usage
# ───────────
#   bash rotate_github_token.sh ghp_xxxxx
#   FSTDD_BARE_STDD=/custom/path bash rotate_github_token.sh ghp_xxxxx
#
# 幂等 / Idempotent: yes（重复跑同一 token 不会坏；先备份再替换）
set -euo pipefail

# ── 可覆盖路径（环境变量） ──
TOKEN_FILE="${FSTDD_TOKEN_FILE:-$HOME/.github_token}"
BARE_STDD="${FSTDD_BARE_STDD:-/home/ubuntu/fstdd-git/stdd-repo.git}"
BARE_HUB="${FSTDD_BARE_HUB:-/home/ubuntu/fstdd-git/fstdd-hub.git}"
EXP_REPO="${FSTDD_EXP_REPO:-/home/ubuntu/Fstdd-experiences-repo}"
FLAG_STDD="${FSTDD_FLAG_STDD:-/home/ubuntu/fstdd-git/mirror-failed.flag}"
FLAG_HUB="${FSTDD_FLAG_HUB:-/home/ubuntu/fstdd-git/fstdd-hub-mirror-failed.flag}"

# ── 参数校验 ──
NEW_TOKEN="${1:-}"
if [ -z "$NEW_TOKEN" ]; then
  cat >&2 <<EOF
用法: $0 <new_github_pat>

示例: $0 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
EOF
  exit 1
fi
# GitHub PAT v2: ghp_ + 36 base64url 字符
if ! [[ "$NEW_TOKEN" =~ ^ghp_[A-Za-z0-9]{36}$ ]]; then
  echo "ERROR: token 格式不对，应为 ghp_ + 36 字符 (实测 ${#NEW_TOKEN} 字符)" >&2
  exit 1
fi

echo "══════════════════════════════════════════════"
echo "  GitHub PAT Rotation"
echo "  new token: ${NEW_TOKEN:0:6}*** (len=${#NEW_TOKEN})"
echo "  time: $(date -Is)"
echo "══════════════════════════════════════════════"

# ── Step 1: 备份旧 token ──
OLD_TOKEN=""
if [ -f "$TOKEN_FILE" ]; then
  OLD_TOKEN=$(tr -d '[:space:]' < "$TOKEN_FILE")
  if [ "$OLD_TOKEN" = "$NEW_TOKEN" ]; then
    echo "SKIP: 新旧 token 相同，无需轮换"
    exit 0
  fi
  cp "$TOKEN_FILE" "${TOKEN_FILE}.bak.$(date +%Y%m%d%H%M)"
  echo "[1/6] 旧 token 已备份 (前缀 ${OLD_TOKEN:0:6}*** )"
else
  echo "[1/6] 首次设置 token (之前不存在 $TOKEN_FILE)"
fi

# ── Step 2: 写新 token（原子） ──
tmp="${TOKEN_FILE}.tmp.$$"
echo -n "$NEW_TOKEN" > "$tmp"
chmod 600 "$tmp"
mv -f "$tmp" "$TOKEN_FILE"
echo "[2/6] $TOKEN_FILE 已更新"

# ── Step 3: 更新所有 git remote URL ──
# 策略：遍历所有目标仓库的所有 github remote，把 HTTPS URL 中的 token 替换，
#       SSH URL 则升级为 HTTPS PAT。
echo "[3/6] 更新 git remote URL"
REPO_LIST=(
  "$BARE_STDD:github"
  "$EXP_REPO:origin"
)
# fstdd-hub.git 也扫一遍（之前可能有 SSH 残留）
if [ -d "$BARE_HUB" ]; then
  # 找任何含 github 的 remote
  hub_remotes=$(git -C "$BARE_HUB" remote -v 2>/dev/null | grep github | awk '{print $1}' | sort -u)
  for r in $hub_remotes; do
    REPO_LIST+=("$BARE_HUB:$r")
  done
fi

for entry in "${REPO_LIST[@]}"; do
  target="${entry%%:*}"
  remote="${entry##*:}"
  [ -e "$target" ] || { echo "  - $target (不存在，跳过)"; continue; }

  url=$(git -C "$target" config --get remote.${remote}.url 2>/dev/null || echo "")
  if [ -z "$url" ]; then
    echo "  - $target remote $remote (无 URL，跳过)"
    continue
  fi

  if echo "$url" | grep -q "x-access-token:"; then
    # HTTPS PAT → 换 token 部分
    owner_repo=$(echo "$url" | sed 's|.*github.com[:/]||;s|\.git$||')
    new_url="https://x-access-token:${NEW_TOKEN}@github.com/${owner_repo}.git"
    git -C "$target" remote set-url "${remote}" "$new_url"
    echo "  ✓ $(basename "$target") remote $remote (PAT replaced)"
  elif echo "$url" | grep -qE "^git@github\.com[:/]"; then
    # SSH → 升级 HTTPS PAT
    owner_repo=$(echo "$url" | sed 's|git@github.com[:/]||;s|\.git$||')
    new_url="https://x-access-token:${NEW_TOKEN}@github.com/${owner_repo}.git"
    git -C "$target" remote set-url "${remote}" "$new_url"
    echo "  ✓ $(basename "$target") remote $remote (SSH → HTTPS)"
  else
    echo "  - $(basename "$target") remote $remote (非 github，跳过)"
  fi
done

# ── Step 4: fstdd-hub.git hook 检查 ──
# 设计：hook 已改为从 ~/.github_token 动态读取 → 自动跟随新 token，无需改动。
# 仅当 hook 内仍硬编码旧 token 时才 sed 替换（防御性）。
HOOK="${BARE_HUB}/hooks/post-receive"
echo "[4/6] fstdd-hub.git hook 检查"
if [ -f "$HOOK" ]; then
  if grep -q 'TOKEN_FILE=.*\.github_token' "$HOOK"; then
    echo "  ✓ hook 已读 $TOKEN_FILE，自动跟随（无需改动）"
  elif grep -q 'x-access-token:' "$HOOK"; then
    # 还有硬编码 token，替换
    sed -i "s|x-access-token:[^@]*@github|x-access-token:${NEW_TOKEN}@github|g" "$HOOK"
    echo "  ✓ hook 硬编码 token 已替换"
  elif grep -q 'git@github' "$HOOK"; then
    echo "  ⚠ hook 仍含 SSH URL！需手动替换为 HTTPS PAT 版模板"
  else
    echo "  - hook 无 github URL，跳过"
  fi
else
  echo "  - $HOOK 不存在，跳过"
fi

# ── Step 5: Push 验证 ──
echo "[5/6] Push 验证"
FAILED=0

# stdd-repo.git (bare, branch=master)
if [ -d "$BARE_STDD" ]; then
  branch="master"
  # 先查 bare 里有哪些 heads
  heads=$(git -C "$BARE_STDD" for-each-ref --format='%(refname:short)' refs/heads/ | head -1)
  [ -n "$heads" ] && branch="$heads"
  if timeout 30 git -C "$BARE_STDD" push github "$branch" 2>&1 | tail -3; then
    echo "  ✓ stdd-repo.git push OK"
  else
    echo "  ✗ stdd-repo.git push FAILED (branch=$branch)"
    FAILED=1
  fi
fi

# Fstdd-experiences-repo (clone, branch=main)
if [ -d "$EXP_REPO" ]; then
  branch=$(git -C "$EXP_REPO" symbolic-ref --short HEAD 2>/dev/null || echo main)
  if timeout 30 git -C "$EXP_REPO" push origin "$branch" 2>&1 | tail -3; then
    echo "  ✓ Fstdd-experiences-repo push OK"
  else
    echo "  ✗ Fstdd-experiences-repo push FAILED (branch=$branch)"
    FAILED=1
  fi
fi

# fstdd-hub.git: 从 hook 里读 TARGET
if [ -d "$BARE_HUB" ] && [ -f "$HOOK" ]; then
  target_from_hook=$(grep -oP 'TARGET="https://[^"]+"' "$HOOK" 2>/dev/null | head -1 | sed 's/TARGET=//' || echo "")
  if [ -z "$target_from_hook" ]; then
    # 兜底：直接读 token 拼 URL
    tok=$(tr -d '[:space:]' < "$TOKEN_FILE")
    target_from_hook="https://x-access-token:${tok}@github.com/2749817087qq/DKK_Fstdd-hub.git"
  fi
  if timeout 30 git -C "$BARE_HUB" push "$target_from_hook" --all 2>&1 | tail -3; then
    echo "  ✓ fstdd-hub.git push OK"
  else
    echo "  ✗ fstdd-hub.git push FAILED"
    FAILED=1
  fi
fi

# ── Step 6: 清除故障标记 ──
rm -f "$FLAG_STDD" "$FLAG_HUB" 2>/dev/null || true
echo "[6/6] 故障标记已清除"

# ── 汇总 ──
echo "══════════════════════════════════════════════"
if [ "$FAILED" -eq 0 ]; then
  echo "  ✓ PAT rotation 完成，全部通过"
  exit 0
else
  echo "  ⚠ PAT rotation 完成，但部分 push 失败"
  echo "    建议检查: tools/check_mirror.sh"
  exit 1
fi
