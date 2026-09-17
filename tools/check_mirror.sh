#!/usr/bin/env bash
# 镜像状态巡检：一条命令回答「服务器裸库与 GitHub 是否收敛」。
#
# 为什么需要它
# ------------
# 在此之前，判断镜像是否滞后只能人工 ssh + tail mirror.log —— 既要求人记得去看，
# 也要求人读懂日志。本命令把这件事变成「有明确判定与退出码」的检查。
#
# 退出码约定（三者必须可区分，调用方可据此分支）
#   0  已收敛  ：裸库与 GitHub 同一 sha，且无故障标记
#   2  滞后    ：存在故障标记，或裸库与 GitHub sha 不同
#   3  无法测量：前置条件缺失（ssh 别名未配置）或远端不可达
#      —— 必须与「滞后」区分开。把工具故障误报为镜像故障，会让人去查一个
#         根本不存在的问题，比不报更糟。
#
# 判定顺序（有意为之，勿随意调整）
# ------------------------------
# **先判故障标记，再判可测性。** 标记是上一次失败留下的**确定事实**，
# 而「可测性」只说明当前测不了。若先判可测性，则「GitHub 不可达 + 已有标记」
# 会被降级成「无法测量」（3），把已知的失败项与发生时间从退出码里丢掉 ——
# 而那时恰恰最需要把故障说清楚。
#
# 覆盖范围（诚实声明）
# ------------------
# 本命令比对的是 **master 分支**的 sha 与故障标记状态。
# 钩子推送的是 `--all` + `--tags`，因此「非 master 分支或 tag 单独滞后」
# **不会**被判为滞后。master 是唯一流转分支、tags 极少变动，当前判定对运维足够；
# 完整 refs 比对记录为后续项。
#
# 只读保证
# --------
# 本命令**不写任何状态**：不推送、不写标记、不改日志、不碰裸库。
# 这一点很重要 —— 本环境经 ssh 的命令会被执行两次，任何副作用都会双发。
# 采集用的远端脚本只用 git rev-parse / git ls-remote / timeout / cut / sed / echo。
#
# 用法
# ----
#   ./tools/check_mirror.sh
#   FSTDD_SSH_ALIAS=my-hub ./tools/check_mirror.sh
#
# 可覆盖的环境变量
# ----------------
#   FSTDD_SSH_ALIAS    默认 fstdd-hub
#   FSTDD_SSH_CONFIG   默认 $HOME/.ssh/config
#   FSTDD_BARE_DIR     默认 /home/ubuntu/fstdd-git/stdd-repo.git
#   FSTDD_MIRROR_FLAG  默认 /home/ubuntu/fstdd-git/mirror-failed.flag
#   FSTDD_MIRROR_URL   镜像目标：remote 名（默认 github）或任意 URL / 本地路径。
#                      仅供自动化验证 —— **直传**给 git 作为目标参数，
#                      从而**不必改动裸库的真实配置**。
#
# 依赖：bash、git、ssh（及 coreutils 的 echo/sed/grep/head/cut/timeout）。
# **不依赖 jq** —— 本命令要在 3 台机器上的 6 个 agent 上直接可用，
# 不能要求任何人先装工具。
set -uo pipefail

ALIAS="${FSTDD_SSH_ALIAS:-fstdd-hub}"
SSH_CONFIG="${FSTDD_SSH_CONFIG:-$HOME/.ssh/config}"
BARE="${FSTDD_BARE_DIR:-/home/ubuntu/fstdd-git/stdd-repo.git}"
FLAG="${FSTDD_MIRROR_FLAG:-/home/ubuntu/fstdd-git/mirror-failed.flag}"
# 默认空 = 镜像目标用 remote 名 `github`。仅自动化验证时非空。
MIRROR_URL="${FSTDD_MIRROR_URL:-}"

EXIT_CONVERGED=0
EXIT_LAGGING=2
EXIT_UNMEASURABLE=3

say() { printf '%s\n' "$*"; }

# ---- 前置条件：ssh 与别名必须就位 ----
if ! command -v ssh >/dev/null 2>&1; then
  say "[UNMEASURABLE] 找不到 ssh 命令"
  exit "$EXIT_UNMEASURABLE"
fi

HOST_RE="^Host[[:space:]]+${ALIAS}([[:space:]]|\$)"
if [ ! -f "$SSH_CONFIG" ] || ! grep -qE "$HOST_RE" "$SSH_CONFIG"; then
  say "[UNMEASURABLE] ssh 别名 '$ALIAS' 未在 $SSH_CONFIG 中配置"
  say "                先执行 tools/deploy_server_bare_repo.sh 完成部署与别名配置"
  exit "$EXIT_UNMEASURABLE"
fi

# ---- 采集端状态（单次 ssh 往返，只读） ----
remote="$(
  ssh -o ConnectTimeout=10 -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
    "$ALIAS" "BARE='$BARE' FLAG='$FLAG' MIRROR_URL='$MIRROR_URL' bash -s" <<'REMOTE' 2>&1
# 镜像目标：默认 remote 名 `github`，可被 FSTDD_MIRROR_URL 覆盖为 URL / 本地路径。
# 这样验证「滞后 / 收敛」时**不必改动裸库的真实配置** ——
# 否则验证窗口内若有真实 agent 推送，钩子会把提交镜像到错误目标。
#
# ⚠️ 这里**有意直传目标**，而不是用 GIT_CONFIG_KEY_0=remote.github.url 去「覆盖」：
#    remote.<name>.url 是**多值**键 —— 第一个值用于 fetch，全部值用于 push。
#    环境注入只会往列表末尾**追加**一项，于是注入会「看起来生效」：
#    `git config --get remote.github.url` 返回注入值，但 `git ls-remote`
#    用的始终是**第一个** URL。实测（服务器 git 2.43.0）：注入
#    http://127.0.0.1:9/nope.git（discard 端口，连接必被拒）之后，
#    ls-remote 依旧返回真实 GitHub 的 sha —— 「无法测量 / 滞后」两条判定
#    因此永远测不出来。直传目标则完全绕过 remote 配置解析。
TARGET="${MIRROR_URL:-github}"
echo "bare=$(git -C "$BARE" rev-parse HEAD 2>/dev/null || echo unknown)"
echo "github=$(timeout 30 git -C "$BARE" ls-remote "$TARGET" refs/heads/master 2>/dev/null | cut -f1)"
if [ -f "$FLAG" ]; then
  echo "flag=present"
  sed 's/^/flagbody_/' "$FLAG"
else
  echo "flag=absent"
fi
REMOTE
)"
ssh_rc=$?

bare_sha="$(printf '%s\n' "$remote" | sed -n 's/^bare=//p' | head -1)"
github_sha="$(printf '%s\n' "$remote" | sed -n 's/^github=//p' | head -1)"
flag_state="$(printf '%s\n' "$remote" | sed -n 's/^flag=//p' | head -1)"

say "镜像状态巡检"
say "  裸库 sha   : ${bare_sha:-<未知>}"
say "  GitHub sha : ${github_sha:-<未知>}"
say "  故障标记   : ${flag_state:-<未知>}"

# ---- 判定 ----
# 顺序有意为之：**先判故障标记**。标记是上一次失败留下的确定事实，
# 而「可测性」只说明当前测不了。反过来的话，「GitHub 不可达 + 已有标记」
# 会被降级成 3（无法测量），把已知的失败项与时间从退出码里丢掉。
if [ "$flag_state" = "present" ]; then
  say "  判定       : 滞后（存在故障标记 —— 上一次镜像未完成）"
  printf '%s\n' "$remote" | sed -n 's/^flagbody_/    标记: /p'
  exit "$EXIT_LAGGING"
fi

if [ "$ssh_rc" -ne 0 ] || [ -z "$bare_sha" ] || [ "$bare_sha" = "unknown" ] || [ -z "$github_sha" ]; then
  say "  判定       : 无法测量（远端不可达或信息不完整）"
  printf '%s\n' "$remote" | sed 's/^/    | /' >&2
  exit "$EXIT_UNMEASURABLE"
fi

if [ "$bare_sha" != "$github_sha" ]; then
  say "  判定       : 滞后（裸库与 GitHub sha 不一致）"
  exit "$EXIT_LAGGING"
fi

say "  判定       : 已收敛"
exit "$EXIT_CONVERGED"
