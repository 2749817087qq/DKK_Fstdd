<!-- fstdd-inbox
experience_id: EXP-20260917-INSTALL-4
author: anonymous
received_at: 2026-09-25T13:10:04.551176+00:00
remote_addr: 172.18.0.8
node_id: FSTDD001
-->

---
exported_at: 2026-09-25
sanitized: true
---
<!-- fstdd-inbox
experience_id: EXP-20260917-INSTALL-4
author: (anonymous)
received_at: 2026-09-18T02:08:00.741423+00:00
remote_addr: <IP>
-->

---
experience_id: EXP-20260917-INSTALL-4
category: tooling
severity: high
occurrences: 1
title: install.sh 注释与 Python 默认值不一致，且未 export 导致装到错误目录
exported_at: 2026-09-18
sanitized: true
lifecycle_state: deposited
---
## 现象

FSTDD 安装后，skill 出现在**与安装脚本注释所声称的目录不同的地方**
（注释说 `$HOME/.workbuddy-ai/skills`，实际落在 `$HOME/.workbuddy/skills`），
在当前 WorkBuddy 会话的可用技能列表里看不到，表现为"装了但不生效"。

## 根因

**三处不一致叠加**：

1. **注释与实现各写各的**
   - `install.sh` 头部注释：`FSTDD_OUT   skill 输出目录（默认 $HOME/.workbuddy-ai/skills）`
   - `tools/install_workbuddy_skills.py`：`OUT = Path(<DOMAIN>("FSTDD_OUT", <DOMAIN>() / ".workbuddy" / "skills"))`

2. **install.sh 未 `export FSTDD_OUT`**：只有 export 才会传给子进程的 Python，
   否则 Python 用自己那份默认值，注释写什么都没用。

3. 结果：实际生效的是 Python 侧的 `.workbuddy`，与注释相反。

补充背景：WorkBuddy 的 skill 加载目录 = **实例自己的 home + `skills/`**（按 home 拼装的相对路径，
不是写死目录）。本机并存两个实例 home（`$HOME/.workbuddy` 与 `$HOME/.workbuddy-ai`），**各扫各的**，
所以装到"另一个实例"的目录，当前会话就是看不到——不是没生效，是实例不同。

## 处理

在 install.sh 里做单一真源：

```bash
export FSTDD_OUT="$(_winpath "${FSTDD_OUT:-$HOME/.workbuddy-ai/skills}")"
export FSTDD_SRC="$(_winpath "${FSTDD_SRC:-$SCRIPT_DIR/upstream}")"
```

要点：
- 必须 `export`，别让 Python 退回自己的默认值；
- 必须过 `cygpath -m`（`_winpath`）—— Git Bash 的 `/c/<用户目录>/...` 传给 Windows Python
  会被解析成 `\c<用户目录>\...`（盘符丢失，实测写到 `<PATH><用户目录>\...`）；
- 默认值与注释必须一致，二选一，别两头写。
