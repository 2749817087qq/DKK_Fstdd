#!/usr/bin/env bash
# STDD for WorkBuddy —— 一键安装
#
# 把「装依赖 → 安装 skill → 校验」串成一条命令，避免漏掉中间步骤。
#
# 用法：
#   ./install.sh                # 交互：缺依赖时询问是否安装
#   ./install.sh --yes          # 非交互：自动补装缺失依赖
#   ./install.sh --py /path/to/python
#   STDD_OUT=/custom/skills ./install.sh
#
# 环境变量：
#   STDD_SRC   上游代码目录（默认脚本同级 upstream/）
#   STDD_OUT   skill 输出目录（默认 ~/.workbuddy-ai/skills）
#   STDD_PY    指定 Python 解释器
set -euo pipefail

# Git for Windows 的 pwd 返回 /c/Users/... 形式，Windows Python 会把它解析成
# C:/c/Users/... 而报「No such file or directory」。需转为 C:/Users/... 。
_winpath() {
  if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else printf '%s' "$1"; fi
}
SCRIPT_DIR="$(_winpath "$(cd "$(dirname "$0")" && pwd)")"
PY="${STDD_PY:-}"
AUTO_YES=0

for arg in "$@"; do
  case "$arg" in
    --yes) AUTO_YES=1 ;;
    --py) shift; PY="${1:-}" ;;
    --py=*) PY="${arg#*=}" ;;
  esac
done

echo "=============================================="
echo " STDD for WorkBuddy —— 安装"
echo "=============================================="
echo

# ---------- 1. 定位 Python ----------
pick_python() {
  local cands=("$@")
  for c in "${cands[@]}"; do
    command -v "$c" >/dev/null 2>&1 && { printf '%s' "$c"; return 0; }
  done
  return 1
}

if [[ -z "$PY" ]]; then
  PY="$(pick_python python3 python py 2>/dev/null || true)"
fi
if [[ -z "$PY" ]]; then
  echo "[FAIL] 未找到 Python。请先安装 Python 3.10+，或用 --py 指定路径。"
  exit 1
fi
echo "[1/4] Python: $PY"
"$PY" --version || { echo "[FAIL] 该解释器无法执行"; exit 1; }

# 版本检查（需 >= 3.10）
"$PY" - <<'EOF' || { echo "[FAIL] 需要 Python 3.10 或以上"; exit 1; }
import sys
sys.exit(0 if sys.version_info >= (3, 10) else 1)
EOF

# ---------- 2. 依赖检查 ----------
echo "[2/4] 依赖检查: PyYAML / Jinja2"
if "$PY" -c "import yaml, jinja2" 2>/dev/null; then
  echo "      OK（已具备）"
else
  echo "      缺失，安装脚本会生成 skill，但 CLI 运行时会失败。"
  if [[ "$AUTO_YES" == "1" ]]; then
    REPLY="y"
  else
    read -r -p "      现在安装？(y/N) " REPLY </dev/tty 2>/dev/null || REPLY=""
  fi
  if [[ "$REPLY" =~ ^[Yy]$ ]]; then
    "$PY" -m pip install pyyaml jinja2 || {
      echo "[FAIL] 依赖安装失败。可手动执行: $PY -m pip install pyyaml jinja2"
      exit 1
    }
    echo "      已安装"
  else
    echo "      跳过依赖安装 —— CLI 将无法运行，仅生成 skill 文件"
  fi
fi

# ---------- 3. 安装 skill ----------
echo "[3/4] 生成 skill"
"$PY" "$SCRIPT_DIR/tools/install_workbuddy_skills.py" || {
  echo "[FAIL] 安装脚本执行失败"
  exit 1
}

# ---------- 4. 校验 ----------
echo "[4/4] 校验"
if "$PY" "$SCRIPT_DIR/tools/verify_workbuddy_skills.py"; then
  echo
  echo "=============================================="
  echo " 安装完成"
  echo "=============================================="
  echo " skill 目录: ${STDD_OUT:-$HOME/.workbuddy-ai/skills}"
  echo " 上游资源  : ${STDD_SRC:-$SCRIPT_DIR/upstream}"
  echo
  echo " 下一步：在 WorkBuddy 中重启或执行 /reload，然后运行 /stdd-understand"
  exit 0
else
  echo
  echo "[FAIL] 校验未通过 —— 请勿继续使用，先按上面的提示修复。"
  exit 1
fi
