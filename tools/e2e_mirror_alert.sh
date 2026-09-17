#!/usr/bin/env bash
# 端到端故障链路实测（Slice H / CP-002…CP-010）
#
# 为什么需要它
# ------------
# 钩子的告警逻辑已在 pytest 里用 stub 验证过，但那些验证**不触碰真实服务器**。
# 本脚本在真实服务器上跑完整链路：正常态 → 故障态 → 滞后态 → 恢复态 → 收敛态，
# 确认四层出口（回显 / 日志 / 故障标记 / 控制面）在同一时刻全部生效。
#
# 为什么不用「真断网」制造故障
# ----------------------------
# 纪律是「模拟失败后必须恢复现场」。若把 github remote 改成不可达地址再改回来，
# 恢复阶段就依赖 GitHub 真实可达 —— 而本项目 GitHub 走内置代理，时段性 502 是
# 已知现象。一旦恢复时恰好不可用，服务器就**留在故障态**，反而违反纪律。
#
# 因此故障态指向 http://127.0.0.1:9/...（端口 9 = discard，连接必被拒、快速失败），
# 恢复态指向服务器上一个临时裸库（本地路径，push 必成功）。两者都不依赖外网。
#
# 零污染设计
# ----------
# 钩子与巡检命令都支持经环境变量覆盖 目标 URL / 裸库路径 / 日志 / 故障标记 /
# 控制面地址（见 ADJ-001）。本脚本把日志与标记都指到 /tmp/fstdd-e2e/，
# **不碰生产的 mirror.log 与 mirror-failed.flag**；镜像目标一律用 FSTDD_MIRROR_URL
# 注入 —— 钩子与巡检命令都支持，因此**全程不改裸库的真实配置**（含 CP-006 三态）。
# 临时裸库也建在 /tmp/fstdd-e2e/ 下，不落在生产目录。
# 收尾由 trap 兜底：核验真实配置**确实未被改动**（这是「零污染」的证据，
# 而不是「发完还原命令就宣告成功」），并报告临时库位置。
#
# 「执行两次」的处理
# ------------------
# 本环境经 ssh 的命令会被执行两次。所有远端动作因此都写成幂等：
# 采集类只读、建库有存在性保护、写标记是覆盖式、钩子重复执行结果一致
# （断言均为「包含」式）。
#
# 用法
# ----
#   ./tools/e2e_mirror_alert.sh
#   FSTDD_SSH_ALIAS=my-hub ./tools/e2e_mirror_alert.sh
#
# 退出码：0 = 全部通过；1 = 有断言失败；2 = 前置条件不满足
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

ALIAS="${FSTDD_SSH_ALIAS:-fstdd-hub}"
BARE="${FSTDD_BARE_DIR:-/home/ubuntu/fstdd-git/stdd-repo.git}"
# 临时库一律建在 /tmp 下 —— **不得落在生产目录** /home/ubuntu/fstdd-git/，
# 否则跑一次验证就在生产目录留下垃圾库（实测踩到过）。
WORK="/tmp/fstdd-e2e"
FAKE="${FSTDD_E2E_FAKE:-$WORK/fake-mirror.git}"
FAKE_BEHIND="${FSTDD_E2E_FAKE_BEHIND:-$WORK/fake-behind.git}"
FAKE_REJECT="${FSTDD_E2E_FAKE_REJECT:-$WORK/fake-reject-branches.git}"
UNREACH="http://127.0.0.1:9/nope.git"
HUB="${FSTDD_HUB_URL:-http://127.0.0.1:8788}"
HUB_UNREACH="http://127.0.0.1:9/hub"

SSH=(ssh -o ConnectTimeout=15 -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$ALIAS")

PASS=0
FAIL=0
ok()  { echo "  [PASS] $*"; PASS=$((PASS + 1)); }
bad() { echo "  [FAIL] $*"; FAIL=$((FAIL + 1)); }

expect_eq() { # $1=期望 $2=实际 $3=描述
  if [ "$2" = "$1" ]; then ok "$3（=$2）"; else bad "$3：期望 $1，实际 $2"; fi
}

# 单次 ssh 往返执行 stdin 脚本；剥离 CR，便于 Windows 侧比对
rsh() { "${SSH[@]}" "bash -s" 2>&1 | tr -d '\r'; }

hook_exit() { # 从 run_hook 输出里取退出码（双发时取第一个）
  printf '%s' "$1" | grep -o 'HOOK_EXIT=[0-9]*' | head -1 | cut -d= -f2
}

# --------------------------------------------------------------------------- #
# 0. 前置检查
# --------------------------------------------------------------------------- #
echo "=== 0/9 前置检查 ==="
if ! command -v ssh >/dev/null 2>&1; then
  echo "[FAIL] 找不到 ssh"; exit 2
fi
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "$ALIAS" true >/dev/null 2>&1; then
  echo "[FAIL] ssh 别名 '$ALIAS' 不可达 —— 先执行 tools/deploy_server_bare_repo.sh"
  exit 2
fi
ok "ssh 别名 $ALIAS 可达"

ORIG_URL="$(rsh <<REMOTE | head -1
git -C '$BARE' remote get-url github 2>/dev/null || echo ''
REMOTE
)"
if [ -z "$ORIG_URL" ]; then
  echo "[FAIL] 裸库 $BARE 没有 github remote"
  exit 2
fi
ok "已记录原 github URL：$ORIG_URL"

# 现场核验：本脚本**全程不应改动**裸库的真实 remote 配置（目标 URL 一律经
# FSTDD_MIRROR_URL 注入）。收尾时读回真实配置与开始时比对 —— 这是「零污染」的**证据**。
# 放在 trap 里，异常退出同样执行；核验失败计入 FAIL（是一条缺陷，不是环境问题）。
verify_untouched() {
  now="$(rsh <<REMOTE | head -1
git -C '$BARE' remote get-url github 2>/dev/null || echo ''
REMOTE
)"
  if [ "$now" = "$ORIG_URL" ]; then
    echo "  [OK] 裸库真实 remote 未被改动：$now"
  else
    echo "  [!!] 裸库真实 remote 被改动（当前=$now，期望=$ORIG_URL）"
    echo "       本脚本不应修改真实配置 —— 这是缺陷，不是环境问题。"
    echo "       处置：将 remote github 的 URL 改回 $ORIG_URL"
    FAIL=$((FAIL + 1))
  fi
}
cleanup() {
  rc=$?
  echo ""
  echo "=== 收尾：核验现场 ==="
  verify_untouched
  echo "  [..] 临时库保留在 $WORK/（/tmp 下，由系统回收；重跑会复用）"
  echo ""
  echo "=== 汇总：PASS=$PASS  FAIL=$FAIL ==="
  if [ "$FAIL" -gt 0 ]; then exit 1; fi
  exit "$rc"
}
trap cleanup EXIT INT TERM

# --------------------------------------------------------------------------- #
# 1. 远端准备：工作目录 + 假镜像库
# --------------------------------------------------------------------------- #
echo "=== 1/9 远端准备 ==="
PREP_OUT="$(rsh <<REMOTE
set -uo pipefail
export HOME=/home/ubuntu
mkdir -p '$WORK'
if [ ! -d '$FAKE' ] || [ "\$(git -C '$FAKE' rev-parse --is-bare-repository 2>/dev/null)" != "true" ]; then
  git init --bare --initial-branch=master '$FAKE' >/dev/null 2>&1
fi
git -C '$FAKE' config core.sharedRepository group 2>/dev/null || true

# fake-behind：用于「sha 不一致」判定（无故障标记也须判滞后）
if [ ! -d '$FAKE_BEHIND' ]; then
  git init --bare --initial-branch=master '$FAKE_BEHIND' >/dev/null 2>&1
fi

# ⚠️ 下面的嵌套 heredoc（<<'PRERE'）虽然加了引号（远端不展开），
#    但**外层 <<REMOTE 没加引号**，所以这里的 $ 仍会被**本机** shell 展开 ——
#    想让内容原样落盘，就必须对**外层**转义（\$ref）。
#
# fake-reject-branches：接收 tags 但**拒绝 branches**，用于制造
# 「branches 失败 / tags 成功」的混合态 —— 标识拆分的唯一目的就是让这种
# 状态不会被 `grep MIRROR-OK` 误读为整体成功，必须真实验证一次。
if [ ! -d '$FAKE_REJECT' ]; then
  git init --bare --initial-branch=master '$FAKE_REJECT' >/dev/null 2>&1
fi
mkdir -p '$FAKE_REJECT/hooks'
cat > '$FAKE_REJECT/hooks/pre-receive' <<'PRERE'
#!/bin/sh
# e2e 专用：拒绝 branches，放行 tags。仅存在于 /tmp 下的临时库。
while read -r _old _new ref; do
  case "\$ref" in
    refs/heads/*) echo "e2e: branches rejected by design"; exit 1 ;;
  esac
done
exit 0
PRERE
chmod +x '$FAKE_REJECT/hooks/pre-receive' 2>/dev/null || true
echo "prep_ok"
REMOTE
)"
if printf '%s' "$PREP_OUT" | grep -q "prep_ok"; then
  ok "远端工作目录与假镜像库就绪（$FAKE）"
else
  bad "远端准备失败：$PREP_OUT"
fi

# 执行钩子：经环境变量注入 URL / 日志 / 标记 / 控制面，不改裸库配置
run_hook() { # $1=url $2=hub_url
  rsh <<REMOTE
set -uo pipefail
export HOME=/home/ubuntu
mkdir -p '$WORK'
export FSTDD_BARE_DIR='$BARE'
export FSTDD_MIRROR_LOG='$WORK/mirror.log'
export FSTDD_MIRROR_FLAG='$WORK/mirror-failed.flag'
export FSTDD_HUB_URL='$2'
export FSTDD_HUB_NODE_ID='fstdd-hub-infra'
# 镜像目标直传（钩子内部把它作为 git push 的目标参数）——
# **不用** GIT_CONFIG_KEY_0=remote.github.url：那是追加 push URL，
# 真实 GitHub 仍留在推送目标里，等于本脚本会真的推线上（详见 ADJ-010）。
export FSTDD_MIRROR_URL='$1'
bash '$BARE/hooks/post-receive' </dev/null
echo "HOOK_EXIT=\$?"
REMOTE
}

read_flag() {
  rsh <<REMOTE
if [ -f '$WORK/mirror-failed.flag' ]; then
  echo "flag=present"
  sed 's/^/flagbody_/' '$WORK/mirror-failed.flag'
else
  echo "flag=absent"
fi
REMOTE
}

# --------------------------------------------------------------------------- #
# 2. CP-002 正常态：镜像成功 → 推送方可见 MIRROR-OK，且内容同样落日志
# --------------------------------------------------------------------------- #
echo "=== 2/9 CP-002 正常态：回显 + 落日志 ==="
OUT_NORMAL="$(run_hook "$FAKE" "$HUB")"
printf '%s' "$OUT_NORMAL" | grep -q "\[MIRROR-OK\]" \
  && ok "推送方输出含 [MIRROR-OK]（整体成功标识）" || bad "推送方输出未见 [MIRROR-OK]"
printf '%s' "$OUT_NORMAL" | grep -q "\[MIRROR-STEP\] branches mirrored" \
  && ok "推送方输出含 [MIRROR-STEP] branches mirrored（逐项进度）" \
  || bad "推送方输出缺 branches 逐项进度"
printf '%s' "$OUT_NORMAL" | grep -q "\[MIRROR-STEP\] tags mirrored" \
  && ok "推送方输出含 [MIRROR-STEP] tags mirrored（逐项进度）" \
  || bad "推送方输出缺 tags 逐项进度"
printf '%s' "$OUT_NORMAL" | grep -q "mirror complete: branches + tags up to date" \
  && ok "输出含收敛总结行" || bad "输出缺收敛总结行"
LOG_TAIL="$(rsh <<REMOTE
tail -12 '$WORK/mirror.log' 2>/dev/null || echo '(无日志)'
REMOTE
)"
printf '%s' "$LOG_TAIL" | grep -q "\[MIRROR-OK\]" \
  && ok "同一内容已落 mirror.log（回显与落盘一致）" || bad "mirror.log 未见 MIRROR-OK"
expect_eq "0" "$(hook_exit "$OUT_NORMAL")" "正常态钩子退出码"

# --------------------------------------------------------------------------- #
# 3. CP-003 故障态：结构化告警块 + 失败项点名 + 不可误读为成功
# --------------------------------------------------------------------------- #
echo "=== 3/9 CP-003 故障态：结构化告警块 ==="
OUT_FAIL="$(run_hook "$UNREACH" "$HUB")"
while IFS= read -r probe; do
  [ -n "$probe" ] || continue
  printf '%s' "$OUT_FAIL" | grep -qE "$probe" \
    && ok "告警块含：$probe" || bad "告警块缺：$probe"
done <<'PROBES'
\[MIRROR-FAILED\] branches push failed
\[MIRROR-FAILED\] tags push failed
真值源.*已更新
GitHub 镜像.*未同步
对外通道滞后
失败项.*branches tags
PROBES
if printf '%s' "$OUT_FAIL" | grep -q "\[MIRROR-OK\]"; then
  bad "故障态输出混入了成功标识 [MIRROR-OK]（可能被误读为成功）"
else
  ok "故障态输出无成功标识（不会被误读为成功）"
fi
expect_eq "0" "$(hook_exit "$OUT_FAIL")" "故障态钩子退出码（镜像失败不得改变退出码）"

# 混合态（CP-003 边界，也是标识拆分存在的唯一理由）：
# branches 失败、tags 成功时，输出必须**同时**具备
#   · tags 的逐项成功标识 [MIRROR-STEP]（tags 确实同步了，不该被抹掉）
#   · 不含 [MIRROR-OK]（整体并未成功 —— 若此处出现，`grep MIRROR-OK` 就会误判）
rsh <<REMOTE >/dev/null 2>&1
rm -f '$WORK/mirror-failed.flag'
REMOTE
OUT_MIX="$(run_hook "$FAKE_REJECT" "$HUB")"
printf '%s' "$OUT_MIX" | grep -q "\[MIRROR-STEP\] tags mirrored" \
  && ok "混合态：tags 逐项成功标识保留" || bad "混合态：tags 逐项成功标识丢失"
printf '%s' "$OUT_MIX" | grep -q "\[MIRROR-FAILED\] branches push failed" \
  && ok "混合态：branches 失败被点名" || bad "混合态：branches 失败未被点名"
if printf '%s' "$OUT_MIX" | grep -q "\[MIRROR-OK\]"; then
  bad "混合态出现了 [MIRROR-OK] —— 整体失败会被误读为成功"
else
  ok "混合态无 [MIRROR-OK]（不会被误读为整体成功）"
fi
expect_eq "0" "$(hook_exit "$OUT_MIX")" "混合态钩子退出码"

# --------------------------------------------------------------------------- #
# 4. CP-004 故障标记：存在且可结构化解析
# --------------------------------------------------------------------------- #
echo "=== 4/9 CP-004 故障标记 ==="
FLAG_OUT="$(read_flag)"
printf '%s' "$FLAG_OUT" | grep -q "^flag=present" \
  && ok "mirror-failed.flag 已写入" || bad "mirror-failed.flag 未写入"
for key in failed_at failed_items failed_detail bare_head; do
  printf '%s' "$FLAG_OUT" | grep -q "flagbody_${key}=" \
    && ok "标记含可解析键：$key" || bad "标记缺键：$key"
done

# --------------------------------------------------------------------------- #
# 5. CP-008 控制面：故障态下可检索到 notice
# --------------------------------------------------------------------------- #
echo "=== 5/9 CP-008 控制面 notice ==="
# /messages 是**收件箱**语义：`WHERE acked_at IS NULL AND (to_node_id=? OR to_node_id IS NULL)`。
# 钩子上报的 notice 不带 to_node_id（广播），因此必须带 node_id 参数才能查到 ——
# 不带参数会返回 `{"error": "node_id query parameter is required"}`，而不是空列表。
HUB_CODE="$(rsh <<REMOTE
curl -s --max-time 5 -o /dev/null -w '%{http_code}' '$HUB/nodes' 2>/dev/null || echo 000
REMOTE
)"
HUB_CODE="$(printf '%s' "$HUB_CODE" | head -1 | tr -d '[:space:]')"
if [ "$HUB_CODE" = "200" ]; then
  MSG_OUT="$(rsh <<REMOTE
curl -s --max-time 8 '$HUB/messages?node_id=fstdd-hub-infra' 2>/dev/null || echo '(控制面不可达)'
REMOTE
)"
  printf '%s' "$MSG_OUT" | grep -q '"kind": "notice"' \
    && ok "控制面可检索到 kind=notice 的消息" || bad "控制面未见 notice 消息"
  printf '%s' "$MSG_OUT" | grep -q "镜像未完成" \
    && ok "notice body 说明镜像未完成" || bad "notice body 未说明镜像未完成"
  printf '%s' "$MSG_OUT" | grep -q "失败项=branches tags" \
    && ok "notice body 含失败项明细" || bad "notice body 缺失败项明细"
  printf '%s' "$MSG_OUT" | grep -qE "时间=20[0-9]{2}-" \
    && ok "notice body 含发生时间" || bad "notice body 缺发生时间"
else
  echo "  [SKIP] 控制面 $HUB 不可达（HTTP $HUB_CODE）—— 降级路径由步骤 6 单独覆盖"
fi

# --------------------------------------------------------------------------- #
# 6. CP-009 降级：控制面不可达时，回显与标记仍生效、退出码仍为 0
# --------------------------------------------------------------------------- #
echo "=== 6/9 CP-009 控制面不可达时的降级 ==="
rsh <<REMOTE >/dev/null 2>&1
rm -f '$WORK/mirror-failed.flag'
REMOTE
OUT_DEG="$(run_hook "$UNREACH" "$HUB_UNREACH")"
printf '%s' "$OUT_DEG" | grep -q "\[MIRROR-FAILED\]" \
  && ok "控制面不可达时，回显仍然生效" || bad "控制面不可达时回显失效（不该）"
FLAG_DEG="$(read_flag)"
printf '%s' "$FLAG_DEG" | grep -q "^flag=present" \
  && ok "控制面不可达时，故障标记仍然写入" || bad "控制面不可达时故障标记未写入（不该）"
expect_eq "0" "$(hook_exit "$OUT_DEG")" "控制面不可达时钩子退出码"

# --------------------------------------------------------------------------- #
# 7. CP-006 巡检三态：3 无法测量 / 2 滞后 / 0 已收敛
#    这一段必须真实改 remote URL（巡检读的是真实配置），由 trap 兜底还原。
# --------------------------------------------------------------------------- #
echo "=== 7/9 CP-006 巡检判定 ==="
# 目标 URL 一律经 FSTDD_MIRROR_URL 注入（check_mirror.sh 直传该目标给 git），
# **全程不改裸库真实配置** —— 见头部零污染设计。
export FSTDD_BARE_DIR="$BARE"
export FSTDD_MIRROR_FLAG="$WORK/mirror-failed.flag"

# 7a. 无法测量：**无故障标记** + 目标不可达（判定必须与「滞后」可区分）
rsh <<REMOTE >/dev/null 2>&1
rm -f '$WORK/mirror-failed.flag'
REMOTE
CHECK_3="$(FSTDD_MIRROR_URL="$UNREACH" bash tools/check_mirror.sh 2>&1)"; RC_3=$?
expect_eq "3" "$RC_3" "巡检退出码（无标记 + 目标不可达 = 无法测量）"
printf '%s' "$CHECK_3" | grep -q "无法测量" \
  && ok "输出明确标注「无法测量」" || bad "输出未标注「无法测量」"

# 7b. 标记优先：**有故障标记 + 目标不可达**仍须判为滞后（2），而不是无法测量（3）。
#     这是判定顺序的直接证据：标记是上一次失败留下的确定事实，
#     不能因为此刻测不了就把它降级成「无法测量」—— 那会把已知的失败项
#     与发生时间从退出码里丢掉，而那时恰恰最需要把故障说清楚。
rsh <<REMOTE >/dev/null 2>&1
printf 'failed_at=2026-01-01T00:00:00+00:00\nfailed_items=branches\nfailed_detail=branches=rc1;\nbare_head=unknown\n' > '$WORK/mirror-failed.flag'
REMOTE
SEEDED="$(read_flag)"
printf '%s' "$SEEDED" | grep -q "^flag=present" \
  && ok "前置条件：故障标记已种下" || bad "前置条件不成立：故障标记未种下"
CHECK_2A="$(FSTDD_MIRROR_URL="$UNREACH" bash tools/check_mirror.sh 2>&1)"; RC_2A=$?
expect_eq "2" "$RC_2A" "巡检退出码（有标记 + 目标不可达 = 滞后，标记优先于可测性）"
printf '%s' "$CHECK_2A" | grep -q "故障标记" \
  && ok "输出点名故障标记" || bad "输出未点名故障标记"

# 7c. sha 不一致：**无故障标记** + 目标可达但落后一个提交
rsh <<REMOTE >/dev/null 2>&1
export HOME=/home/ubuntu
git -C '$BARE' push '$FAKE_BEHIND' refs/heads/master:refs/heads/master --quiet 2>/dev/null || true
prev="\$(git -C '$BARE' rev-parse master~1 2>/dev/null || true)"
if [ -n "\$prev" ]; then
  git -C '$FAKE_BEHIND' update-ref refs/heads/master "\$prev" 2>/dev/null || true
fi
rm -f '$WORK/mirror-failed.flag'
REMOTE
CHECK_2B="$(FSTDD_MIRROR_URL="$FAKE_BEHIND" bash tools/check_mirror.sh 2>&1)"; RC_2B=$?
expect_eq "2" "$RC_2B" "巡检退出码（无标记 + sha 不一致 = 滞后）"
printf '%s' "$CHECK_2B" | grep -q "sha 不一致" \
  && ok "输出点明 sha 不一致" || bad "输出未点明 sha 不一致"

# --------------------------------------------------------------------------- #
# 8. CP-005 恢复：还原镜像目标后再次推送，标记自动清除
# --------------------------------------------------------------------------- #
echo "=== 8/9 CP-005 恢复态：标记自动清除 ==="
# 先显式种下故障标记，并**断言前置条件成立**。
# 否则「标记被自动清除」会因为标记本来就不存在而**恒真** —— 看着绿，其实没验证。
rsh <<REMOTE >/dev/null 2>&1
printf 'failed_at=2026-01-01T00:00:00+00:00\nfailed_items=branches tags\nfailed_detail=branches=rc1;tags=rc1;\nbare_head=deadbeef\n' > '$WORK/mirror-failed.flag'
REMOTE
SEED="$(read_flag)"
printf '%s' "$SEED" | grep -q "^flag=present" \
  && ok "前置条件：故障标记已种下（否则清除断言恒真）" \
  || bad "前置条件不成立：故障标记未种下，清除断言将恒真"
OUT_RECOVER="$(run_hook "$FAKE" "$HUB")"
printf '%s' "$OUT_RECOVER" | grep -q "\[MIRROR-OK\]" \
  && ok "恢复后推送输出回到 [MIRROR-OK]" || bad "恢复后推送未见 [MIRROR-OK]"
FLAG_AFTER="$(read_flag)"
printf '%s' "$FLAG_AFTER" | grep -q "^flag=absent" \
  && ok "故障标记被自动清除（无需人工介入）" || bad "故障标记未被自动清除"
printf '%s' "$OUT_RECOVER" | grep -q "人工清理" \
  && bad "输出把清理描述为人工动作（应为自动）" || ok "输出未把清理描述为人工动作"

CHECK_0="$(bash tools/check_mirror.sh 2>&1)"; RC_0=$?
expect_eq "0" "$RC_0" "巡检退出码（已收敛）"

# --------------------------------------------------------------------------- #
# 9. CP-007 节点注册幂等 + CP-010 静态审查
# --------------------------------------------------------------------------- #
echo "=== 9/9 CP-007 节点注册幂等 / CP-010 静态审查 ==="
REG_BODY='{"node_id":"fstdd-hub-infra","machine_name":"fstdd-hub","platform":"linux","os":"ubuntu","capabilities":["mirror-monitor"],"ssh_fingerprint":"server"}'
for _ in 1 2; do
  rsh <<REMOTE >/dev/null 2>&1
curl -s --max-time 8 -X POST '$HUB/nodes/register' -H 'Content-Type: application/json' -d '$REG_BODY' 2>/dev/null || true
REMOTE
done
NODES_OUT="$(rsh <<REMOTE
curl -s --max-time 8 '$HUB/nodes' 2>/dev/null || echo '(控制面不可达)'
REMOTE
)"
INFRA_CNT="$(printf '%s' "$NODES_OUT" | grep -o 'fstdd-hub-infra' | wc -l | tr -d ' ')"
TOTAL_CNT="$(printf '%s' "$NODES_OUT" | grep -o '"node_id"' | wc -l | tr -d ' ')"
if [ "$INFRA_CNT" -ge 1 ]; then
  ok "GET /nodes 中出现基础设施节点 fstdd-hub-infra（共 $TOTAL_CNT 条记录）"
else
  echo "  [SKIP] 控制面 /nodes 未返回基础设施节点（控制面可能未运行）"
fi
if [ "$INFRA_CNT" -le 1 ]; then
  ok "重复注册未产生重复记录（幂等）"
else
  bad "重复注册产生了 $INFRA_CNT 条记录（非幂等）"
fi

# 静态审查：钩子源码（剔除注释）不得含强制推送
# 强制形式覆盖：--force / --force-with-lease / --mirror / -f（前后非词字符）
# 以及 `+refspec`（不带 --force 的强制更新写法，同样会覆盖远端提交）。
HOOK_FORCE="$(rsh <<REMOTE
grep -v '^[[:space:]]*#' '$BARE/hooks/post-receive' \
  | grep -cE 'push.*(--force|--mirror|[[:space:]]-f([[:space:]]|\$)|[[:space:]]\+[^[:space:]]+)'
REMOTE
)"
expect_eq "0" "$(printf '%s' "$HOOK_FORCE" | head -1 | tr -d '[:space:]')" "钩子源码不含强制推送选项"

echo ""
echo "全部端到端断言执行完毕。"
