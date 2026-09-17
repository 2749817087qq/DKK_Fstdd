# FSTDD 安装与运行问题清单（2026-09-16 工程实测）

环境：Windows / Git Bash / Python 3.13.14（隔离 venv）
操作：卸载旧 STDD → 安装 FSTDD → 工程测试（init / new / status / validate / experience）

---

## 已修复（本机已改，建议合入）

### P1 `install.sh` 的 `--py <path>` 参数解析失效
**现象**：`install.sh --yes --py /path/to/python` 报
`[1/4] Python: --py` → `line 57: --py: command not found`

**根因**：`for arg in "$@"` 的迭代列表在展开时已固定，循环体内 `shift` 不会让
下一次迭代跳过已消费的参数，于是 `PY="${1:-}"` 取到的是 `--py` 自身。

```bash
# 修复前
for arg in "$@"; do
  case "$arg" in
    --py) shift; PY="${1:-}" ;;   # ← 拿到的还是 "--py"
  esac
done

# 修复后：改用下标遍历
_args=("$@"); _i=0
while [[ $_i -lt ${#_args[@]} ]]; do
  case "${_args[$_i]}" in
    --py) _i=$((_i + 1)); PY="${_args[$_i]:-}" ;;
    --py=*) PY="${_args[$_i]#*=}" ;;
  esac
  _i=$((_i + 1))
done
```
注：`--py=/path` 形式原本正常，只有空格形式有问题。

### P2 `install.sh` 未把 `FSTDD_OUT` / `FSTDD_SRC` 传给 Python
**现象**：脚本头部注释声明支持 `FSTDD_OUT` 环境变量，最后也 echo
`skill 目录: ~/.workbuddy-ai/skills`，但 skill 实际写到了 `~/.workbuddy/skills`
（Python 脚本自己的默认值），装完在 WorkBuddy 里不生效。

**根因**：只有 `export` 才会传给子进程；脚本里只做了 `${FSTDD_OUT:-...}` 展开用于显示。

```bash
export FSTDD_OUT="$(_winpath "${FSTDD_OUT:-$HOME/.workbuddy-ai/skills}")"
export FSTDD_SRC="$(_winpath "${FSTDD_SRC:-$SCRIPT_DIR/upstream}")"
```

### P3 Git Bash 路径未转 Windows 形式 → 写到 `C:\c\Users\...`
**现象**：把 `FSTDD_OUT=/c/Users/Administrator/.workbuddy-ai/skills` 传给 Windows Python，
文件被写到 `C:\c\Users\Administrator\.workbuddy-ai\skills\`（盘符丢失，多出一层 `c\`）。

**根因**：Git Bash 的 `$HOME` 是 `/c/Users/xxx`，Windows Python 的 `Path()` 把
`/c/...` 当成根目录下的相对路径。

**修复**：传给 Python 前统一过 `cygpath -m`（脚本里已有 `_winpath()`，调用时漏用）。

### P4 安装结束 echo 的目录与实际写入目录不一致
脚本末尾写死 `~/.workbuddy-ai/skills`，实际按 Python 默认值走了 `~/.workbuddy/skills`，
误导排查。已改为 echo 真实变量 `$FSTDD_OUT`。

---

## 待修复（未改）

### P5 `tools/setup_git_credential.py` 的 token 路径算错
```python
REPO = Path(__file__).resolve().parent.parent        # = <仓库根>
TOKEN_FILE = REPO.parent / ".workbuddy-ai" / "tmp" / ".gh_token"
```
当仓库位于 `~/.workbuddy-ai/FSTDD` 时，`REPO.parent` 已是 `~/.workbuddy-ai`，
再拼一层得到 `~/.workbuddy-ai/.workbuddy-ai/tmp/.gh_token`（实际不存在）。
实际应为 `~/.workbuddy-ai/tmp/.gh_token`，建议直接 `Path.home() / ".workbuddy-ai" / "tmp" / ".gh_token"`（保留 `FSTDD_TOKEN` 环境变量覆盖）。

### P6 Guard 平台检测结果为 `Claude Code`，而非 WorkBuddy
`fstdd init` / `status` 输出 `Guard: ✅ 已激活 (Claude Code)`。
本机并未安装 Claude Code，显然是平台探测在 WorkBuddy 场景下没有命中，
回退到了第一顺位。会影响平台相关行为（slash 命令格式、hooks 安装位置等）。

### P7 `verify_workbuddy_skills.py` 只校验 6 个 skill，漏了 2 个
`EXPECTED` 列表只含 `fstdd-understand / spec / build / deliver / upgrade`（5 个）+ 入口？
实际生成 7 个：`fstdd`（入口）、`fstdd-fin`（金融增强层）**未纳入校验**。
`fstdd-fin` 有 266 行正文，属原创内容，建议一并纳入安全策略与路径适配校验。

### P8 change 名称不支持中文
`fstdd new 测试变更-速率限制` 直接报"无效的 change 名称"。
正则只允许 ASCII 字母数字开头。中文用户高频踩坑，建议：
- 要么放宽到 Unicode 字母（`str.isalpha()`），
- 要么在报错里给出"检测到非 ASCII 字符，建议改用 <拼音/英文> xxx"的提示。

### P9 `gate` 无参调用提示不友好
`fstdd gate` 输出 `Unknown subcommand: None. Use: approve`。
建议无参时直接打印帮助或当前 gate 状态。

---

## 环境事实（供文档校正）

| 项 | 实测结果 |
|---|---|
| 内核 `cli/dist/codebuddy.js` 中 `.workbuddy-ai` | 出现 **0** 次 |
| 同文件中 `.workbuddy/skills` | 出现 **3** 次 |
| `~/.workbuddy/skills` | 63 个在用的技能 |
| `~/.workbuddy-ai/skills` | WorkBuddy AI 桌面版同样加载（实测装在此处的 skill 出现在可用列表） |

结论：**两个目录都会被扫描**，不存在唯一正确答案。
建议 install 脚本默认 `.workbuddy-ai`，并在文档里说明另一处用 `FSTDD_OUT` 覆盖。

---

## 工程测试结果

| 用例 | 结果 |
|---|---|
| `fstdd init` | ✅ 通过，`.fstdd/` 骨架完整（agent_tests/archive/canonical/changes/config.d/experiences/memory/onboarding/platforms） |
| `fstdd new rate-limit` | ✅ 生成 `changes/2026-09-16-rate-limit`，含 design.md / test-plan.md / canonical YAML |
| `fstdd status` | ✅ 正常，Guard 激活（但平台显示为 Claude Code，见 P6） |
| `fstdd validate` | ✅ 正确报出 "缺少必需文件: proposal.md" |
| `fstdd experience list` | ✅ 经验库 0 条 |
| 外发禁用哨兵 | ✅ `FSTDD_LOCAL_POLICY_NO_UPLOAD_V1` 在 `fstdd-deliver` 中在位 |
| 安装路径 | ✅ 7 个 skill 全部落到 `C:\Users\Administrator\.workbuddy-ai\skills\` |
| CLI 路径固化 | ✅ skill 正文中的 `python bin/fstdd` 已替换为绝对路径 |

---

## 本机网络备注

`github.com` 直连 443 超时，必须走系统代理；测试期间代理返回 502
（`CONNECT tunnel failed, response 502`），导致无法 push。
`api.github.com` 经代理可返回 200。
