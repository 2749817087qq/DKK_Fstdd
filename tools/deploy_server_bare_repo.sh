#!/usr/bin/env bash
# 部署 FSTDD 服务器裸库（L1 唯一真值源）+ GitHub 镜像，幂等可反复执行。
#
# 为什么需要这个脚本
# ------------------
# 分布式任务规划里，多台开发机上的多个 agent 需要一个**不依赖任何单机**的
# 权威仓库。选型结论：服务器裸库是真值源，GitHub 只作镜像（上传目标）。
#
#   agent 本地 worktree ──push──> 服务器裸库 ──post-receive──> GitHub 镜像
#                                      ▲
#                                 唯一真值源
#
# 为什么镜像放服务器而不是本地
#   · 服务器直连 GitHub 实测 0.084s，本地走内置代理经常 502
#   · 镜像不占用任何开发机，agent 关机也不影响同步
#
# 为什么用 Deploy Key 而不是 PAT
#   · 服务器是公网机器。PAT 泄露 = 整个账号沦陷
#   · Deploy Key 权限被限定在**单个仓库**，可随时通过 API 单独吊销
#   · 私钥只落在服务器 /home/ubuntu/.ssh，不进任何仓库
#
# 用法
# ----
#   ./tools/deploy_server_bare_repo.sh
#   FSTDD_SSH_HOST=ubuntu@1.2.3.4 ./tools/deploy_server_bare_repo.sh
#
# 可覆盖的环境变量
# ----------------
#   FSTDD_SSH_HOST       默认 ubuntu@43.134.236.80
#   FSTDD_SSH_KEY        默认 /d/id_ed25519
#   FSTDD_BARE_DIR       默认 /home/ubuntu/fstdd-git/stdd-repo.git
#   FSTDD_GITHUB_REPO    默认 2749817087qq/DKK_Fstdd
#   FSTDD_GH_TOKEN_FILE  默认 <工作区>/.workbuddy-ai/.gh_token
#   FSTDD_SKIP_MIRROR    设为 1 则只建裸库，不碰 GitHub 镜像
#
# 注意
# ----
# · 停旧进程一律按端口找 PID 再 kill，绝不用 pkill（会匹配到 ssh 自身）
# · 远端命令在部分 agent 环境会执行两次 —— 本脚本全部操作都是幂等的
# · 验证一律看**端状态**（rev-parse / ls-remote），不看命令回显
set -euo pipefail

HOST="${FSTDD_SSH_HOST:-ubuntu@43.134.236.80}"
KEY="${FSTDD_SSH_KEY:-/d/id_ed25519}"
BARE_DIR="${FSTDD_BARE_DIR:-/home/ubuntu/fstdd-git/stdd-repo.git}"
GH_REPO="${FSTDD_GITHUB_REPO:-2749817087qq/DKK_Fstdd}"
SKIP_MIRROR="${FSTDD_SKIP_MIRROR:-0}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOKEN_FILE="${FSTDD_GH_TOKEN_FILE:-$REPO_ROOT/../.workbuddy-ai/.gh_token}"
GH_KEY="/home/ubuntu/.ssh/fstdd_github_ed25519"

SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=20 "$HOST")

echo "=== 0/6 探测远端环境 ==="
REMOTE_GIT="$("${SSH[@]}" 'command -v git')"
[ -n "$REMOTE_GIT" ] || { echo "[FAIL] 远端没有 git"; exit 1; }
echo "    远端 git: $("${SSH[@]}" 'git --version')"

echo "=== 1/6 创建裸库（已存在则保留数据）==="
"${SSH[@]}" "bash -s" <<REMOTE
set -euo pipefail
BARE_DIR='$BARE_DIR'
mkdir -p "\$(dirname "\$BARE_DIR")"
if [ -d "\$BARE_DIR" ] && [ "\$(git -C "\$BARE_DIR" rev-parse --is-bare-repository 2>/dev/null)" = "true" ]; then
  echo "    [SKIP] 裸库已存在，保留现有数据"
else
  git init --bare --initial-branch=master "\$BARE_DIR" >/dev/null
  echo "    [CREATE] 裸库已初始化"
fi
git -C "\$BARE_DIR" config core.sharedRepository group
git -C "\$BARE_DIR" config gc.auto 0
git -C "\$BARE_DIR" config receive.denyNonFastForwards false
echo "    path=\$BARE_DIR bare=\$(git -C "\$BARE_DIR" rev-parse --is-bare-repository)"
REMOTE

echo "=== 2/6 配置本地 remote ==="
cd "$REPO_ROOT"
if git remote get-url server >/dev/null 2>&1; then
  git remote set-url server "$HOST:$BARE_DIR"
  echo "    [UPDATE] remote server 已更新"
else
  git remote add server "$HOST:$BARE_DIR"
  echo "    [ADD] remote server 已添加"
fi
echo "    $(git remote get-url server)"

if [ "$SKIP_MIRROR" = "1" ]; then
  echo "[OK] 已跳过 GitHub 镜像配置（FSTDD_SKIP_MIRROR=1）"
  exit 0
fi

echo "=== 3/6 生成镜像专用密钥（已存在则复用）==="
PUBKEY="$("${SSH[@]}" "bash -s" <<REMOTE
set -euo pipefail
KEY='$GH_KEY'
mkdir -p /home/ubuntu/.ssh && chmod 700 /home/ubuntu/.ssh
if [ ! -f "\$KEY" ]; then
  ssh-keygen -t ed25519 -N "" -C "fstdd-hub-mirror" -f "\$KEY" >/dev/null
fi
chmod 600 "\$KEY"; chmod 644 "\$KEY.pub"
cat "\$KEY.pub"
REMOTE
)"
echo "    公钥: ${PUBKEY:0:60}..."
echo "    指纹: $("${SSH[@]}" "ssh-keygen -lf '$GH_KEY.pub'" | awk '{print $2}')"

echo "=== 4/6 注册 Deploy Key ==="
if [ ! -f "$TOKEN_FILE" ]; then
  echo "    [SKIP] 找不到 token 文件 $TOKEN_FILE"
  echo "    请手动把下面这把公钥加到 $GH_REPO 的 Deploy Keys（勾选 Allow write access）："
  echo "    $PUBKEY"
else
  TOKEN="$(cat "$TOKEN_FILE")"
  # 用 key 内容前缀判重，避免重复注册
  EXISTING="$(curl -s --max-time 30 -H "Authorization: Bearer $TOKEN" \
      -H "Accept: application/vnd.github+json" \
      "https://api.github.com/repos/$GH_REPO/keys" \
    | grep -c "fstdd-hub-mirror" || true)"
  if [ "$EXISTING" -gt 0 ]; then
    echo "    [SKIP] deploy key 已存在"
  else
    curl -s --max-time 30 -X POST -H "Authorization: Bearer $TOKEN" \
      -H "Accept: application/vnd.github+json" \
      "https://api.github.com/repos/$GH_REPO/keys" \
      -d "{\"title\":\"fstdd-hub-mirror\",\"key\":\"$PUBKEY\",\"read_only\":false}" \
      | grep -E '"(id|title|read_only)"' | sed 's/^/    /'
  fi
fi

echo "=== 5/6 配置服务器 ssh + 镜像 remote ==="
"${SSH[@]}" "bash -s" <<REMOTE
set -euo pipefail
BARE_DIR='$BARE_DIR'
GH_KEY='$GH_KEY'
GH_REPO='$GH_REPO'
CFG=/home/ubuntu/.ssh/config

[ -f "\$CFG" ] && cp "\$CFG" "\$CFG.bak.\$(date +%Y%m%d%H%M%S)"

# 幂等重写 github.com 段：删旧段再追加
python3 - "\$CFG" "\$GH_KEY" <<'PY'
import sys, pathlib
cfg, key = pathlib.Path(sys.argv[1]), sys.argv[2]
block = ("Host github.com\n"
         "    HostName github.com\n"
         "    User git\n"
         f"    IdentityFile {key}\n"
         "    IdentitiesOnly yes\n"
         "    StrictHostKeyChecking accept-new\n"
         "    ServerAliveInterval 30\n"
         "    ServerAliveCountMax 4\n")
text = cfg.read_text() if cfg.exists() else ""
out, skip = [], False
for line in text.splitlines(True):
    if line.startswith("Host "):
        skip = line.strip() == "Host github.com"
    if not skip:
        out.append(line)
new = "".join(out).rstrip("\n")
cfg.write_text((new + "\n\n" if new else "") + block)
PY
chmod 600 "\$CFG"

ssh-keyscan -T 15 github.com >> /home/ubuntu/.ssh/known_hosts 2>/dev/null || true
sort -u /home/ubuntu/.ssh/known_hosts -o /home/ubuntu/.ssh/known_hosts

git -C "\$BARE_DIR" remote remove github 2>/dev/null || true
git -C "\$BARE_DIR" remote add github "git@github.com:\$GH_REPO.git"
echo "    github remote: \$(git -C "\$BARE_DIR" remote get-url github)"
echo "    ssh 认证: \$(ssh -o ConnectTimeout=15 -T git@github.com 2>&1 | head -1)"
REMOTE

echo "=== 6/6 安装镜像钩子 ==="
"${SSH[@]}" "bash -s" <<REMOTE
set -euo pipefail
BARE='$BARE_DIR'
HOOK="\$BARE/hooks/post-receive"
cat > "\$HOOK" <<'HOOKBODY'
#!/usr/bin/env bash
# FSTDD 服务端镜像钩子：裸库（真值源）-> GitHub（镜像）。
# 同步执行，使「push 成功」蕴含「镜像已尝试」。
# 非强制推送：若 GitHub 出现分叉则失败并记录，而不是静默覆盖别人的提交。
set -uo pipefail
export HOME=/home/ubuntu
unset GIT_DIR GIT_WORK_TREE
BARE=$BARE_DIR
LOG=/home/ubuntu/fstdd-git/mirror.log
ts() { date -Is; }
{
  echo "--- \$(ts) post-receive: mirroring to github ---"
  if timeout 180 git -C "\$BARE" push github --all 2>&1; then
    echo "[OK] branches mirrored"
  else
    echo "[WARN] branch mirror failed rc=\$?"
  fi
  if timeout 120 git -C "\$BARE" push github --tags 2>&1; then
    echo "[OK] tags mirrored"
  else
    echo "[WARN] tag mirror failed rc=\$?"
  fi
  echo "--- \$(ts) mirror finished ---"
} >> "\$LOG" 2>&1
exit 0
HOOKBODY
chmod +x "\$HOOK"
bash -n "\$HOOK"
echo "    hook 已安装: \$HOOK"
REMOTE

echo "=== 端状态验证 ==="
"${SSH[@]}" "BARE='$BARE_DIR'; echo \"    裸库 HEAD : \$(git -C \$BARE rev-parse HEAD 2>/dev/null || echo '(空)')\"; echo \"    裸库 提交数: \$(git -C \$BARE rev-list --count master 2>/dev/null || echo 0)\"; echo \"    GitHub HEAD: \$(timeout 30 git -C \$BARE ls-remote github refs/heads/master 2>/dev/null | cut -f1)\""

echo "[OK] 服务器裸库与 GitHub 镜像部署完成"
