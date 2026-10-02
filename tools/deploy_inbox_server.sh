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
# 本脚本**不碰收件目录里的数据**。清理测试数据请单独操作。
# 停旧进程时只按端口找 PID 再 kill —— 绝不用 `pkill -f inbox_server`：
# 该模式会匹配到 ssh 命令行自身，把自己的会话杀掉（踩过，挂了 12 分钟）。
set -euo pipefail

HOST="${FSTDD_SSH_HOST:-ubuntu@43.134.236.80}"
KEY="${FSTDD_SSH_KEY:-/d/id_ed25519}"
PORT="${FSTDD_INBOX_PORT:-8787}"
REMOTE_DIR="${FSTDD_REMOTE_DIR:-/home/ubuntu/fstdd-inbox-server}"
DATA_DIR="${FSTDD_REMOTE_DATA_DIR:-/home/ubuntu/fstdd-inbox}"
SERVICE="fstdd-inbox"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO_ROOT/tools/inbox_server.py"
[ -f "$SRC" ] || { echo "[FAIL] 找不到 $SRC"; exit 1; }

SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=20 "$HOST")
HOSTNAME_ONLY="${HOST#*@}"

echo "=== 0/5 探测远端 python3 ==="
REMOTE_PY="$("${SSH[@]}" 'command -v python3')"
echo "    远端解释器: $REMOTE_PY"
[ -n "$REMOTE_PY" ] || { echo "[FAIL] 远端没有 python3"; exit 1; }

echo "=== 1/5 上传服务端代码 ==="
"${SSH[@]}" "mkdir -p '$REMOTE_DIR' '$DATA_DIR'"
scp -i "$KEY" -o StrictHostKeyChecking=no -q "$SRC" "$HOST:$REMOTE_DIR/inbox_server.py"
LOCAL_MD5="$(md5sum "$SRC" | cut -d' ' -f1)"
REMOTE_MD5="$("${SSH[@]}" "md5sum '$REMOTE_DIR/inbox_server.py' | cut -d' ' -f1")"
echo "    本地 md5: $LOCAL_MD5"
echo "    远端 md5: $REMOTE_MD5"
[ "$LOCAL_MD5" = "$REMOTE_MD5" ] || { echo "[FAIL] 上传后 md5 不一致"; exit 1; }

echo "=== 2/5 安装 systemd 单元 ==="
"${SSH[@]}" "sudo tee /etc/systemd/system/$SERVICE.service >/dev/null" <<UNIT
[Unit]
Description=FSTDD experience inbox endpoint
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$REMOTE_DIR
ExecStart=$REMOTE_PY $REMOTE_DIR/inbox_server.py --host 0.0.0.0 --port $PORT --data-dir $DATA_DIR
Restart=always
RestartSec=5
StandardOutput=append:$DATA_DIR/server.log
StandardError=append:$DATA_DIR/server.log

[Install]
WantedBy=multi-user.target
UNIT
echo "    已写入 /etc/systemd/system/$SERVICE.service"

echo "=== 3/5 停旧进程 + 启动服务 ==="
"${SSH[@]}" "set -e
OLD=\$(sudo lsof -t -i:$PORT 2>/dev/null || true)
if [ -n \"\$OLD\" ]; then echo \"    停止旧进程: \$OLD\"; sudo kill \$OLD; sleep 1; fi
sudo systemctl daemon-reload
sudo systemctl enable --now $SERVICE >/dev/null 2>&1
sleep 1
echo \"    服务状态: \$(systemctl is-active $SERVICE)\"
"

echo "=== 4/5 校验监听与开机自启 ==="
"${SSH[@]}" "ss -lntp | grep ':$PORT' || echo '    [FAIL] 端口未监听'
echo \"    开机自启: \$(systemctl is-enabled $SERVICE)\"
echo \"    /health(localhost): \$(curl -s --max-time 10 http://127.0.0.1:$PORT/health)\""

echo "=== 5/5 公网可达性 ==="
if curl -s --max-time 25 "http://$HOSTNAME_ONLY:$PORT/health"; then
    echo ""
    echo "[OK] 部署完成，公网 /health 可达"
else
    echo "[FAIL] 公网不可达 —— 检查云安全组与 ufw（sudo ufw allow $PORT/tcp）"
    exit 1
fi
