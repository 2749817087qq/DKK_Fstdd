#!/usr/bin/env bash
# FSTDD for WorkBuddy —— 一键安装
#
# 把「装依赖 → 安装 skill → 校验」串成一条命令，避免漏掉中间步骤。
#
# 用法：
#   ./install.sh                # 交互：缺依赖时询问是否安装
#   ./install.sh --yes          # 非交互：自动补装缺失依赖
#   ./install.sh --py /path/to/python
#   FSTDD_OUT=/custom/skills ./install.sh
#
# 环境变量：
#   FSTDD_SRC   上游代码目录（默认脚本同级 upstream/）
#   FSTDD_OUT   skill 输出目录（默认 ~/.workbuddy-ai/skills）
#   FSTDD_PY    指定 Python 解释器
set -euo pipefail

# Git for Windows 的 pwd 返回 /c/Users/... 形式，Windows Python 会把它解析成
# C:/c/Users/... 而报「No such file or directory」。需转为 C:/Users/... 。
_winpath() {
  if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else printf '%s' "$1"; fi
}
SCRIPT_DIR="$(_winpath "$(cd "$(dirname "$0")" && pwd)")"
PY="${FSTDD_PY:-}"
AUTO_YES=0

# 参数解析：`--py` 的取值须按**当前位置**读取。原实现用 `for arg in "$@"` 配 `shift`，
# 当 `--py` 不是首个参数时（如 `--yes --py /x/python`）会 shift 掉错误元素，
# 令 `${1}` 指向 `--py` 自身，PY 被赋成字面量 `--py` —— 随后即报
# 「未找到可用的 Python 3.10+」，而机器里其实有可用解释器。
while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes) AUTO_YES=1 ;;
    --py) PY="${2:-}" ;;
    --py=*) PY="${1#*=}" ;;
  esac
  shift
done

echo "=============================================="
echo " FSTDD for WorkBuddy —— 安装"
echo "=============================================="
echo

# ---------- 1. 定位 Python ----------
# 候选择优：**真跑一次**才采纳。Windows（含 Git Bash）上 `python3` / `python` 常指向
# Microsoft Store 的「应用执行别名」桩 —— `command -v` 找得到，一执行却退出 9009（无输出）。
# 原实现「存在即用」会误选该桩并报「该解释器无法执行」，而机器里其实有可用解释器
# （如 WorkBuddy 自带的 ~/.workbuddy-ai/binaries/python/envs/*）。本修复与 install.ps1 对齐。
test_python() {
  local p="$1"
  [[ -n "$p" ]] || return 1
  local v
  v="$("$p" -c 'import sys; print(1 if sys.version_info >= (3,10) else 0)' 2>/dev/null)" || return 1
  [[ "$v" == "1" ]]
}

if [[ -z "$PY" ]]; then
  cands=()
  for c in python3 python py; do
    if command -v "$c" >/dev/null 2>&1; then cands+=("$(command -v "$c")"); fi
  done
  # 安装目标就是 WorkBuddy：其自带环境的解释器通常已具备 PyYAML / Jinja2
  for e in "$HOME"/.workbuddy-ai/binaries/python/envs/*/Scripts/python.exe; do
    [[ -e "$e" ]] && cands+=("$e")
  done
  for cand in "${cands[@]:-}"; do
    if test_python "$cand"; then PY="$cand"; break; fi
  done
fi
if ! test_python "$PY"; then
  echo "[FAIL] 未找到可用的 Python 3.10+。请先安装 Python，或用 --py 指定路径。"
  exit 1
fi
echo "[1/4] Python: $PY"
"$PY" --version

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
  echo " skill 目录: ${FSTDD_OUT:-$HOME/.workbuddy-ai/skills}"
  echo " 上游资源  : ${FSTDD_SRC:-$SCRIPT_DIR/upstream}"
  echo
  echo " 下一步：在 WorkBuddy 中重启或执行 /reload，然后运行 /fstdd-understand"
  exit 0
else
  echo
  echo "[FAIL] 校验未通过 —— 请勿继续使用，先按上面的提示修复。"
  exit 1
fi
