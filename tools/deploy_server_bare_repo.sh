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
#   FSTDD_SSH_ALIAS      默认 fstdd-hub（写入本机 ssh config 的别名）
#   FSTDD_HUB_URL        默认 http://127.0.0.1:8788（控制面，镜像告警上报目标）
#   FSTDD_HUB_NODE_ID    默认 fstdd-hub-infra（基础设施节点标识）
#
# 钩子路径也可覆盖 —— 仅供自动化验证；post-receive 由 git 调用时不设，走默认值
#   FSTDD_MIRROR_LOG     默认 /home/ubuntu/fstdd-git/mirror.log
#   FSTDD_MIRROR_FLAG    默认 /home/ubuntu/fstdd-git/mirror-failed.flag
#   FSTDD_MIRROR_URL     镜像目标：remote 名（默认 github）或任意 URL / 本地路径
#
# 注意
# ----
# · 远端命令在部分 agent 环境会执行两次 —— 本脚本全部操作都是幂等的
# · 验证一律看**端状态**（rev-parse / ls-remote），不看命令回显
# · 镜像钩子恒以 exit 0 结束 —— 镜像失败只走输出与故障标记，绝不走退出码
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

echo "=== 0/7 探测远端环境 ==="
REMOTE_GIT="$("${SSH[@]}" 'command -v git')"
[ -n "$REMOTE_GIT" ] || { echo "[FAIL] 远端没有 git"; exit 1; }
echo "    远端 git: $("${SSH[@]}" 'git --version')"

echo "=== 1/7 创建裸库（已存在则保留数据）==="
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

echo "=== 2/7 配置本地 SSH 别名与 remote ==="
ALIAS="${FSTDD_SSH_ALIAS:-fstdd-hub}"
HOST_ONLY="${HOST#*@}"
USER_ONLY="${HOST%%@*}"
# 命令行 -i 用 POSIX 路径，ssh config 用 Windows 风格（D:/...）——
# 后者才被 Windows OpenSSH 正确解析，写成 /d/... 会静默用不到密钥。
IDENTITY_WIN="$(printf '%s' "$KEY" | sed -E 's|^/([a-zA-Z])/|\1:/|')"
SSH_CFG="$HOME/.ssh/config"

mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"
[ -f "$SSH_CFG" ] || touch "$SSH_CFG"
chmod 600 "$SSH_CFG"
if grep -qE "^Host[[:space:]]+${ALIAS}([[:space:]]|\$)" "$SSH_CFG"; then
  echo "    [SKIP] 本地 SSH 别名 $ALIAS 已存在"
else
  cat >> "$SSH_CFG" <<CFGBLOCK

Host $ALIAS
    HostName $HOST_ONLY
    User $USER_ONLY
    IdentityFile $IDENTITY_WIN
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
    ServerAliveInterval 30
    ServerAliveCountMax 4
CFGBLOCK
  echo "    [ADD] 已写入本地 SSH 别名 $ALIAS"
fi

cd "$REPO_ROOT"
# remote 必须走 SSH 别名，不能写裸主机名：裸主机名会绕过 ssh config 的
# IdentityFile，导致 git 退回默认密钥并认证失败（本脚本早期版本踩过）。
REMOTE_URL="$ALIAS:$BARE_DIR"
if git remote get-url server >/dev/null 2>&1; then
  git remote set-url server "$REMOTE_URL"
  echo "    [UPDATE] remote server -> $REMOTE_URL"
else
  git remote add server "$REMOTE_URL"
  echo "    [ADD] remote server -> $REMOTE_URL"
fi
echo "    连通验证: $(git ls-remote server refs/heads/master 2>/dev/null | cut -f1 || echo '(空库)')"

if [ "$SKIP_MIRROR" = "1" ]; then
  echo "[OK] 已跳过 GitHub 镜像配置（FSTDD_SKIP_MIRROR=1）"
  exit 0
fi

echo "=== 3/7 生成镜像专用密钥（已存在则复用）==="
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

echo "=== 4/7 注册 Deploy Key ==="
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

echo "=== 5/7 配置服务器 ssh + 镜像 remote ==="
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

# --------------------------------------------------------------------------- #
# 自检：HOOKBODY 区域里的 shell 展开字符必须转义
# --------------------------------------------------------------------------- #
# 钩子体经**外层未加引号的 heredoc**（下面的 <<REMOTE）展开，因此正文里的
# `$`、反引号、行尾反斜杠都会在**本机**被处理：
#   · 未转义的 `$`   -> 本机变量未定义则 unbound variable；或静默展开成错误内容
#   · 未转义的反引号 -> 被当作**命令替换执行**（实测真的执行过一个叫 github 的"命令"）
#   · 行尾反斜杠     -> 吃掉换行，把两行粘成一行
# 三类都会让部署「看起来成功」而钩子内容已经错了，所以**在安装之前拦住**。
#
# 为什么做成脚本自检而不是只靠单元测试：同一类缺陷已发作三次，每次都是
# 「知道有守护测试、但改完没跑」。把纪律变成机制，才不依赖记性。
# 守护测试（upstream/tests/test_mirror_alert_ops.py 的 hook_body_escapes_*）仍是
# 更全面的一道 —— 两者互补。
_hookbody_scan() {
  # 起始锚点必须匹配**真实的 heredoc 起始行**（行首 cat ... <<'HOOKBODY'）。
  # 若只写 /<<.HOOKBODY./，本函数自己那一行也含该模式 -> 会把自身函数体
  # （其中有 $ 与反引号）当成 HOOKBODY 内容扫描 -> **必然误报**（实测踩到）。
  awk '/^cat .*<<.HOOKBODY.$/{f=1;next} /^HOOKBODY$/{f=0} f' "$0" | awk '
    {
      n = length($0)
      bad = ""
      for (i = 1; i <= n; i++) {
        c = substr($0, i, 1)
        if (c == "$" || c == "`") {
          if (i > 1 && substr($0, i - 1, 1) == "\\") continue
          bad = bad (c == "$" ? "未转义$ " : "未转义反引号 ")
        }
      }
      if (n > 0 && substr($0, n, 1) == "\\") bad = bad "行尾反斜杠 "
      if (bad != "") printf "    L%d: %s| %s\n", NR, bad, $0
    }'
}

echo "=== 6/7 安装镜像钩子 ==="
_HOOK_ISSUES="$(_hookbody_scan)"
if [ -n "$_HOOK_ISSUES" ]; then
  echo "[FAIL] HOOKBODY 含会被**本机 shell** 展开的写法 —— 拒绝部署。"
  echo "       这些字符在写入远端前就会被处理，钩子内容会静默出错："
  printf '%s\n' "$_HOOK_ISSUES"
  echo "       修法：在 HOOKBODY 正文里给它们各加一个反斜杠转义。"
  exit 1
fi
echo "    [OK] HOOKBODY 转义自检通过"
"${SSH[@]}" "bash -s" <<REMOTE
set -euo pipefail
BARE='$BARE_DIR'
HOOK="\$BARE/hooks/post-receive"
cat > "\$HOOK" <<'HOOKBODY'
#!/usr/bin/env bash
# FSTDD 服务端镜像钩子：裸库（真值源）-> GitHub（镜像）。
# 同步执行，使「push 成功」蕴含「镜像已尝试」。
# 非强制推送：若 GitHub 出现分叉则失败并记录，而不是静默覆盖别人的提交。
#
# 输出契约（REQ-001 / REQ-002）
# ----------------------------
# · 全部输出经 tee **同时回显给推送方**并追加 mirror.log —— 推送方不必再 ssh 看日志
# · 三个标识语义互斥，**MIRROR-OK 只在整体成功时出现**：
#     [MIRROR-STEP]   逐项进度（branches / tags 各自的镜像结果）
#     [MIRROR-OK]     **整体**成功（branches 与 tags 均已同步）
#     [MIRROR-FAILED] 有任一项失败
#   为何要拆开逐项与整体：若逐项成功也打 MIRROR-OK，则「branches 失败、tags 成功」
#   时会同时出现成功与失败标识 —— \`grep MIRROR-OK\` 即把整体失败误读为成功，
#   而分叉（GitHub 领先）恰恰是最需要告警的场景。
# · 失败时输出结构化告警块，明确「裸库已更新 / GitHub 未同步 / 对外通道滞后」
# · 分支与 tag 两次推送相互独立：任一项失败不阻止另一项，失败项被逐一点名
# · 本钩子恒以 exit 0 结束 —— 真值源已更新即 push 语义上成功；
#   失败只通过输出与故障标记表达，绝不通过退出码（否则会诱导 --force 重推）
#
# 路径与镜像目标可经环境变量覆盖，仅为让钩子可被自动化验证；post-receive 由 git
# 调用时不设这些变量，一律走默认值（镜像目标 = remote 名 github），生产行为不变。
#
# ⚠️ 镜像目标**直接作为 git 参数**传递，不用 GIT_CONFIG_KEY_0=remote.github.url
#    去「覆盖」—— remote.<name>.url 是多值键，注入只会往末尾追加一个 push URL，
#    fetch 仍走第一个 URL（实测注入不可达地址后 ls-remote 依旧连真实远端）。
#    同处注释见 tools/check_mirror.sh。
#
# ⚠️ 本文件内容会被**外层未加引号的 heredoc**（部署脚本里的 <<REMOTE）展开，
#    因此正文里的美元符与反引号**必须各加一个反斜杠转义** —— 否则会在**本机**被展开：
#    变量未定义则报 unbound variable；反引号则被当作**命令替换执行**。
#    本注释有意不写这两个字符的示例，免得它自己被扫出来（守护测试会红）。
#    守护测试：upstream/tests/test_mirror_alert_ops.py 的 hook_body_escapes_* 用例。
set -uo pipefail
export HOME=/home/ubuntu
unset GIT_DIR GIT_WORK_TREE

# 兜底：**无论从哪条路径结束，本钩子恒以 exit 0 退出。**
# 真值源已更新，push 在语义上已经成功；若此处返回非零，会制造
# 「报失败但其实成功」的混乱，并诱导使用者改用 --force 重推（REQ-006）。
# 只在正常路径末尾写 \`exit 0\` 是不够的 —— 中途若死于 set -u 触发的
# 未绑定变量，或 tee 失败使管道在 pipefail 下非零，那一行根本执行不到。
# 内部错误只报错，不改退出码。
trap 'rc=\$?; if [ "\$rc" -ne 0 ]; then echo "[MIRROR-FAILED] 钩子内部错误（rc=\$rc）—— 退出码仍置 0"; fi; exit 0' EXIT

BARE="\${FSTDD_BARE_DIR:-/home/ubuntu/fstdd-git/stdd-repo.git}"
LOG="\${FSTDD_MIRROR_LOG:-/home/ubuntu/fstdd-git/mirror.log}"
FLAG="\${FSTDD_MIRROR_FLAG:-/home/ubuntu/fstdd-git/mirror-failed.flag}"
HUB_URL="\${FSTDD_HUB_URL:-http://127.0.0.1:8788}"
HUB_NODE_ID="\${FSTDD_HUB_NODE_ID:-fstdd-hub-infra}"
# 镜像目标：默认 remote 名 github；自动化验证时经 FSTDD_MIRROR_URL 指向临时库。
MIRROR_TARGET="\${FSTDD_MIRROR_URL:-github}"
ts() { date -Is; }

FAILED_ITEMS=""
FAILED_DETAIL=""

# 记录一项失败：输出失败标识并累积失败项与原因。
# 调用方保持「两项都尝试」的语义 —— 失败不短路，另一项仍会执行。
record_failure() {  # \$1=项名 \$2=超时秒数 \$3=退出码
  local item="\$1" secs="\$2" rc="\$3"
  if [ "\$rc" -eq 124 ]; then
    echo "[MIRROR-FAILED] \$item push timed out (>\${secs}s)"
    FAILED_DETAIL="\${FAILED_DETAIL}\${item}=timeout(>\${secs}s);"
  else
    echo "[MIRROR-FAILED] \$item push failed rc=\$rc"
    FAILED_DETAIL="\${FAILED_DETAIL}\${item}=rc\${rc};"
  fi
  FAILED_ITEMS="\${FAILED_ITEMS}\${item} "
}

{
  echo "--- \$(ts) post-receive: mirroring to github ---"

  if timeout 180 git -C "\$BARE" push "\$MIRROR_TARGET" --all 2>&1; then
    echo "[MIRROR-STEP] branches mirrored"
  else
    record_failure branches 180 \$?
  fi

  if timeout 120 git -C "\$BARE" push "\$MIRROR_TARGET" --tags 2>&1; then
    echo "[MIRROR-STEP] tags mirrored"
  else
    record_failure tags 120 \$?
  fi

  if [ -z "\$FAILED_ITEMS" ]; then
    rm -f "\$FLAG"
    echo "[MIRROR-OK] mirror complete: branches + tags up to date"
  else
    bare_head="\$(git -C "\$BARE" rev-parse HEAD 2>/dev/null || echo unknown)"

    # 原子写入：先写临时文件再 mv（同一文件系统内 mv 是原子的）。
    # 直接 \`> "\$FLAG"\` 时，并发的巡检命令可能读到**写了一半**的标记，
    # 结构化解析随即失败 —— 而标记的全部价值就在于「可被程序可靠读取」。
    # 读者要么看到旧内容，要么看到新内容，不会看到半成品。
    if {
      echo "failed_at=\$(ts)"
      echo "failed_items=\${FAILED_ITEMS% }"
      echo "failed_detail=\${FAILED_DETAIL%;}"
      echo "bare_head=\$bare_head"
    } > "\${FLAG}.tmp" 2>/dev/null; then
      mv -f "\${FLAG}.tmp" "\$FLAG" 2>/dev/null || true
    else
      rm -f "\${FLAG}.tmp" 2>/dev/null || true
      echo "[MIRROR-ALERT] 故障标记写入失败（\$FLAG）—— 回显与退出码不受影响"
    fi

    # 上报控制面（REQ-005）：尽力而为 —— 短超时 + 失败容忍。
    # 控制面是单机自建服务，强依赖它等于用一个单点去解决另一个单点：
    # 上报失败不得改变退出码、不得阻塞推送（SC-012）。
    hub_body="镜像未完成：失败项=\${FAILED_ITEMS% }；原因=\${FAILED_DETAIL%;}；时间=\$(ts)；裸库=\$bare_head"
    hub_json="\$(printf '{"idempotency_key":"%s","from_node_id":"%s","kind":"notice","body":"%s"}' "mirror-fail:\${bare_head}:\${FAILED_ITEMS% }" "\$HUB_NODE_ID" "\$hub_body")"
    if command -v curl >/dev/null 2>&1; then
      curl -s --max-time 3 -X POST "\$HUB_URL/messages" -H 'Content-Type: application/json' -d "\$hub_json" >/dev/null 2>&1 || true
    else
      echo "[MIRROR-ALERT] 控制面告警未上报：服务器缺少 curl（回显与故障标记不受影响）"
    fi

    echo "============================================================"
    echo "[MIRROR-FAILED] 镜像未完成 —— 服务器裸库已更新，GitHub 未同步"
    echo "------------------------------------------------------------"
    echo "  真值源（服务器裸库）: 已更新，本次推送已落库，数据安全"
    echo "  GitHub 镜像        : 未同步，对外通道滞后"
    echo "  失败项             : \${FAILED_ITEMS% }"
    echo "  失败原因           : \${FAILED_DETAIL%;}"
    echo "  发生时间           : \$(ts)"
    echo "  故障标记           : \$FLAG"
    echo "  处置               : 执行 tools/check_mirror.sh 查看镜像状态；"
    echo "                       恢复镜像目标后再次 push 即自动重试并清除标记"
    echo "============================================================"
  fi

  echo "--- \$(ts) mirror finished ---"
} 2>&1 | tee -a "\$LOG"

exit 0
HOOKBODY
chmod +x "\$HOOK"
bash -n "\$HOOK"
echo "    hook 已安装: \$HOOK"
REMOTE

echo "=== 7/7 注册基础设施节点身份 ==="
"${SSH[@]}" "bash -s" <<REMOTE
set -uo pipefail
HUB_URL='${FSTDD_HUB_URL:-http://127.0.0.1:8788}'
if ! command -v curl >/dev/null 2>&1; then
  echo "    [SKIP] 服务器上没有 curl —— 镜像告警无法上报控制面（回显与故障标记仍生效）"
  echo "           如需控制面告警：sudo apt-get install -y curl"
  exit 0
fi
resp="\$(curl -s --max-time 10 -X POST "\$HUB_URL/nodes/register" -H 'Content-Type: application/json' -d '{"node_id":"fstdd-hub-infra","machine_name":"fstdd-hub","platform":"linux","os":"ubuntu","capabilities":["mirror-monitor"],"ssh_fingerprint":"server"}' 2>&1)"
echo "    register: \$resp"
REMOTE

echo "=== 端状态验证 ==="
"${SSH[@]}" "BARE='$BARE_DIR'; echo \"    裸库 HEAD : \$(git -C \$BARE rev-parse HEAD 2>/dev/null || echo '(空)')\"; echo \"    裸库 提交数: \$(git -C \$BARE rev-list --count master 2>/dev/null || echo 0)\"; echo \"    GitHub HEAD: \$(timeout 30 git -C \$BARE ls-remote github refs/heads/master 2>/dev/null | cut -f1)\""

echo "[OK] 服务器裸库与 GitHub 镜像部署完成"
