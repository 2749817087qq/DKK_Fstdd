#!/usr/bin/env bash
# 把「安装及运行问题清单」推送到 GitHub。
#
# 前置（二选一，做一次即可）：
#   A. SSH：把本机公钥加到 GitHub 账号 2749817087qq → Settings → SSH and GPG keys → New SSH key
#      ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIqPX/TIIpqSQdJgkMBOgKuJ5UIhBNH9LsY3E4IK7aPD administrator@DESKTOP-TBJSBQ5
#   B. HTTPS + token：把 token 写入 ~/.workbuddy-ai/tmp/.gh_token，并配到 Credential Manager
#
# 为什么走 SSH：本机 github.com:443 直连不通，本地代理 127.0.0.1:65321 对 github.com
# 的 CONNECT 返回 502；但 github.com:22 与 ssh.github.com:443 均可达。
#
# 用法： bash push_issues.sh
set -uo pipefail

REPORT="C:/Users/Administrator/.workbuddy-ai/FSTDD/docs/INSTALL_RUN_ISSUES_2026-09-16.md"
EXP_DIR="C:/Users/Administrator/.workbuddy-ai/_Fstdd-experiences"
SSH_BASE="git@github.com:2749817087qq"

echo "=============================================="
echo " 推送问题清单"
echo "=============================================="

if [ ! -f "$REPORT" ]; then
  echo "[FAIL] 报告不存在: $REPORT"
  exit 1
fi

# ---------- 1. DKK_Fstdd ----------
echo
echo "[1/2] 推送 commit 到 DKK_Fstdd"
cd "C:/Users/Administrator/.workbuddy-ai/FSTDD" || exit 1
git remote remove sshorigin 2>/dev/null
git remote add sshorigin "$SSH_BASE/DKK_Fstdd.git"
if git push sshorigin HEAD; then
  echo "  [OK] DKK_Fstdd 已推送"
else
  echo "  [FAIL] 推送失败 —— 确认 SSH 公钥已加入 GitHub 账号，或改用 HTTPS + token"
fi

# ---------- 2. Fstdd-experiences ----------
echo
echo "[2/2] 推送报告到 Fstdd-experiences"
if [ ! -d "$EXP_DIR/.git" ]; then
  rm -rf "$EXP_DIR"
  git clone --depth 1 "$SSH_BASE/Fstdd-experiences.git" "$EXP_DIR" || {
    echo "  [FAIL] 无法 clone（凭证未配置或仓库不存在）"
    exit 1
  }
fi

cd "$EXP_DIR" || exit 1
mkdir -p install-run-issues
cp "$REPORT" "install-run-issues/"
git add -A
if git diff --cached --quiet; then
  echo "  [SKIP] 无变更"
else
  git -c user.name="CCREITs" -c user.email="13708386842@139.com" \
    commit -q -m "docs: FSTDD 安装与运行问题清单 2026-09-16（4 项已修 + 5 项待修）" \
    && git push origin HEAD \
    && echo "  [OK] Fstdd-experiences 已推送" \
    || echo "  [FAIL] 推送失败"
fi

echo
echo "完成。"
