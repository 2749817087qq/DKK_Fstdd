#!/usr/bin/env bash
# 把 FSTDD 经验接收端点部署到云服务器（幂等，可反复执行）。
#
# 为什么需要这个脚本
# ------------------
# 端点最初是手工 nohup 起的，服务端代码只存在于 /tmp/inbox_server.py：
#   · /tmp 重启即清空 —— 代码会永久丢失，且服务器上没有任何仓库副本
#   · 进程被 init 收养（PPID=1），没有 systemd、没有 crontab —— 不会开机自启
#   · 进程一挂，服务就彻底没了，无法原样拉起
# 这里把它落到固定目录，并交给 systemd 托管。
#
# 本次加固（change: 2026-09-18-inbox-api-only-write）
# --------------------------------------------------
# · 收口写入通道：收目录归专用**系统用户** fstdd-inbox（nologin），节点以 ubuntu
#   身份 scp 直写将被内核拒绝；服务单元显式 `User=fstdd-inbox` +
#   `EnvironmentFile=<远端 inbox.env>` + `UMask=0022`（日志 other 可读，巡检链路保留）。
# · inbox.env 属机密：脚本只校验其**存在性**，缺失即中止（不生成、不覆盖、不上传、不回显）。
# · 后置校验逐条输出 PASS/FAIL，且含**负向断言**（ubuntu 写入必须被拒）；
#   任一 FAIL 使整体非 0 退出（“测试绿了 ≠ 断言有效”的历史教训）。
#
# 用法
# ----
#   ./tools/deploy_inbox_server.sh
#   FSTDD_SSH_HOST=ubuntu@1.2.3.4 FSTDD_SSH_KEY=~/.ssh/id_ed25519 ./tools/deploy_inbox_server.sh
#
# 可覆盖的环境变量
# ----------------
#   FSTDD_SSH_HOST       默认 ubuntu@43.134.236.80
#   FSTDD_SSH_KEY        默认 /d/id_ed25519
#   FSTDD_INBOX_PORT     默认 8787
#   FSTDD_REMOTE_DIR     默认 /home/ubuntu/fstdd-inbox-server
#   FSTDD_REMOTE_DATA_DIR 默认 /home/ubuntu/fstdd-inbox
#
# 注意
# ----
# 本脚本**不碰收件目录里的数据内容**（不删除、不迁移）；quarantine 迁移另行人工执行。
# 停旧进程只按端口找 PID 再 kill —— 绝不用按进程名模式匹配（pkill 类方式）：
# 那会匹配到 ssh 命令行自身，把自己的会话杀掉（踩过，挂了 12 分钟）。
set -euo pipefail

HOST="${FSTDD_SSH_HOST:-ubuntu@43.134.236.80}"
KEY="${FSTDD_SSH_KEY:-/d/id_ed25519}"
PORT="${FSTDD_INBOX_PORT:-8787}"
REMOTE_DIR="${FSTDD_REMOTE_DIR:-/home/ubuntu/fstdd-inbox-server}"
DATA_DIR="${FSTDD_REMOTE_DATA_DIR:-/home/ubuntu/fstdd-inbox}"
SERVICE="fstdd-inbox"
SERVICE_USER="fstdd-inbox"
ENV_FILE="$REMOTE_DIR/inbox.env"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO_ROOT/tools/inbox_server.py"
[ -f "$SRC" ] || { echo "[FAIL] 找不到 $SRC"; exit 1; }

SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=20 "$HOST")
HOSTNAME_ONLY="${HOST#*@}"

echo "=== 0/7 探测远端 python3 ==="
REMOTE_PY="$("${SSH[@]}" 'command -v python3')"
echo "    远端解释器: $REMOTE_PY"
[ -n "$REMOTE_PY" ] || { echo "[FAIL] 远端没有 python3"; exit 1; }

echo "=== 1/7 校验远端 $ENV_FILE 存在（缺失即中止；不生成/不覆盖/不上传）==="
if "${SSH[@]}" "[ -f '$ENV_FILE' ]"; then
    echo "    [OK] 远端 env 存在（内容不回显，token 属机密）"
else
    echo "    [FAIL] 远端缺少 $ENV_FILE —— 拒绝继续："
    echo "           token 属机密，本脚本不生成、不覆盖、不上传该文件。"
    echo "           处置：先在远端恢复 $ENV_FILE（须含 FSTDD_INBOX_TOKEN=... 行），再重跑本脚本。"
    exit 1
fi

echo "=== 2/7 上传服务端代码 ==="
"${SSH[@]}" "mkdir -p '$REMOTE_DIR' '$DATA_DIR'"
scp -i "$KEY" -o StrictHostKeyChecking=no -q "$SRC" "$HOST:$REMOTE_DIR/inbox_server.py"
LOCAL_MD5="$(md5sum "$SRC" | cut -d' ' -f1)"
REMOTE_MD5="$("${SSH[@]}" "md5sum '$REMOTE_DIR/inbox_server.py' | cut -d' ' -f1")"
echo "    本地 md5: $LOCAL_MD5"
echo "    远端 md5: $REMOTE_MD5"
[ "$LOCAL_MD5" = "$REMOTE_MD5" ] || { echo "[FAIL] 上传后 md5 不一致"; exit 1; }

echo "=== 3/7 建服务用户 $SERVICE_USER + 收目录收权 ==="
"${SSH[@]}" "set -e
if ! id -u $SERVICE_USER >/dev/null 2>&1; then
    sudo useradd --system --no-create-home --shell /usr/sbin/nologin $SERVICE_USER
fi
sudo mkdir -p '$REMOTE_DIR' '$DATA_DIR'
sudo chown -R $SERVICE_USER:$SERVICE_USER '$DATA_DIR'
sudo chmod 755 '$DATA_DIR'
sudo find '$DATA_DIR' -maxdepth 1 -type f -name '*.log' -exec chmod 644 {} +
echo \"    用户: \$(id $SERVICE_USER)\"
echo \"    收目录: \$(stat -c '%U:%G %a' '$DATA_DIR')\"
"

echo "=== 4/7 安装 systemd 单元（User / EnvironmentFile / UMask）==="
"${SSH[@]}" "sudo tee /etc/systemd/system/$SERVICE.service >/dev/null" <<UNIT
[Unit]
Description=FSTDD experience inbox endpoint
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=fstdd-inbox
WorkingDirectory=$REMOTE_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$REMOTE_PY $REMOTE_DIR/inbox_server.py --host 0.0.0.0 --port $PORT --data-dir $DATA_DIR
Restart=always
RestartSec=5
UMask=0022
StandardOutput=append:$DATA_DIR/server.log
StandardError=append:$DATA_DIR/server.log

[Install]
WantedBy=multi-user.target
UNIT
echo "    已写入 /etc/systemd/system/$SERVICE.service"

echo "=== 5/7 停旧进程 + 启动服务（按端口 kill）==="
"${SSH[@]}" "set -e
OLD=\$(sudo lsof -t -i:$PORT 2>/dev/null || true)
if [ -n \"\$OLD\" ]; then echo \"    停止旧进程: \$OLD\"; sudo kill \$OLD; sleep 1; fi
sudo systemctl daemon-reload
sudo systemctl enable --now $SERVICE >/dev/null 2>&1
sleep 1
echo \"    服务状态: \$(systemctl is-active $SERVICE)\"
"

echo "=== 6/7 后置校验（逐条 PASS/FAIL，含负向断言；任一 FAIL 整体非 0 退出）==="
VERIFY_PAYLOAD="$(cat <<VERIFY
FAILED=0
pass() { echo "    [PASS] \$1"; }
fail() { echo "    [FAIL] \$1"; FAILED=1; }

# A. 属主与权限断言
OWNER=\$(stat -c '%U:%G' '$DATA_DIR')
if [ "\$OWNER" = "$SERVICE_USER:$SERVICE_USER" ]; then
    pass "属主=\$OWNER"
else
    fail "属主=\$OWNER（期望 $SERVICE_USER:$SERVICE_USER）"
fi
MODE=\$(stat -c '%a' '$DATA_DIR')
if [ "\$MODE" = "755" ]; then
    pass "收目录权限=\$MODE"
else
    fail "收目录权限=\$MODE（期望 755）"
fi

# B. 负向断言（关键）：ubuntu 身份写入必须被拒 —— 否则权限没真收口也会全绿
if touch '$DATA_DIR/.perm-probe' 2>/dev/null; then
    fail "负向断言失败：ubuntu 仍可写 $DATA_DIR（权限未收口）"
    sudo rm -f '$DATA_DIR/.perm-probe' 2>/dev/null || true
else
    pass "负向断言：ubuntu 写入被拒（Permission denied）"
fi

# C. 正向断言：API 带 token 仍可落盘
TOKEN=\$(sudo sed -n 's/^FSTDD_INBOX_TOKEN=//p' '$ENV_FILE' | head -1)
RESP=\$(curl -s -m 15 -H "X-FSTDD-Token: \$TOKEN" -H 'Content-Type: application/json' \\
    -d '{"experience_id":"EXP-LOCKDOWN-PROBE-1","content":"# probe"}' \\
    http://127.0.0.1:$PORT/api/share-experience || true)
case "\$RESP" in
    *'"accepted": 1'*) pass "API 正向落盘 accepted=1" ;;
    *) fail "API 未落盘: \$RESP" ;;
esac

# D. /health 断言（免鉴权）
HEALTH=\$(curl -s -m 15 http://127.0.0.1:$PORT/health || true)
case "\$HEALTH" in
    *'"ok": true'*) pass "/health ok（免鉴权）" ;;
    *) fail "/health 异常: \$HEALTH" ;;
esac

# 清理探测文件（不留垃圾）
sudo rm -f '$DATA_DIR/EXP-LOCKDOWN-PROBE-1.md' '$DATA_DIR/.perm-probe' 2>/dev/null || true

if [ "\$FAILED" -ne 0 ]; then
    echo "    [RESULT] FAIL —— 见上方逐条；整体非 0 退出"
    exit 1
fi
echo "    [RESULT] PASS —— 权限/负向/正向/health 四组断言全部通过"
VERIFY
)"
"${SSH[@]}" "bash -s" <<< "$VERIFY_PAYLOAD"

echo "=== 7/7 公网可达性 ==="
if curl -s --max-time 25 "http://$HOSTNAME_ONLY:$PORT/health"; then
    echo ""
    echo "[OK] 部署完成，公网 /health 可达"
else
    echo "[FAIL] 公网不可达 —— 检查云安全组与 ufw（sudo ufw allow $PORT/tcp）"
    exit 1
fi