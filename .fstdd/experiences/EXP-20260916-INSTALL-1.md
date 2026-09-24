<!-- fstdd-inbox
experience_id: EXP-20260916-INSTALL-1
author: (anonymous)
received_at: 2026-09-18T02:08:00.740092+00:00
remote_addr: 27.8.11.15
-->

---
experience_id: EXP-20260916-INSTALL-1
category: tooling
severity: high
occurrences: 1
exported_at: 2026-09-18
sanitized: true
---
## 现象

FSTDD 安装脚本默认把全局 skill 输出到 `~/.workbuddy-ai/skills`，装完后当前 WorkBuddy 会话的 skill 列表里**看不到**（等于白装）。

## 根因

**skills 加载目录是「实例 home 相对路径」，不是某个写死的固定目录。**

WorkBuddy 会读取 `["agents","commands","skills","hooks","output-styles","bin", …]` 这一组目录名，
拼接在**该实例自己的 home 基址**之下；因此：

- home 为 `~/.workbuddy` 的实例 → 只扫 `~/.workbuddy/skills`
- home 为 `~/.workbuddy-ai` 的实例 → 只扫 `~/.workbuddy-ai/skills`

本机存在**两套并行的 WorkBuddy 实例 home**（均已实证）：

| 实例 home | 标志 | 其 skills 目录 |
|---|---|---|
| `~/.workbuddy` | `app/`（Crashpad、app-config.json、electron-log-preload.js） | `~/.workbuddy/skills` |
| `~/.workbuddy-ai` | `app/`、`logs/`、`local_storage/`、`file-history/` | `~/.workbuddy-ai/skills` |

**「装了不生效」的真实原因是装到了另一个实例的 home 下，不是应用只认某一个固定目录。**

### 证据（2026-09-16 实证）

- **目录名是拼装的**：在应用 `cli/dist/codebuddy.js` 中，`skills` 与 `agents/commands/hooks/...` 同属一组
  相对目录名被遍历；该文件中 `.workbuddy-ai` 字面量出现 **0 次**（绝对路径并未写死）。
- **本实例静态扫描**：应用资源 `*.js` 中 `.workbuddy/skills` 出现 6 次、`.workbuddy-ai/skills` 出现 0 次。
- **本实例运行态**：当前会话可用技能列表中，`fstdd-*` 等技能的位置均为
  `<PATH><skill>\SKILL.md`，**无一条来自 `.workbuddy-ai`**。
- **反证侧**：仅存在于 `~/.workbuddy-ai/skills/` 的 `install-github-skill`、`stdd-hardening`，
  在**本实例**会话列表中不出现 —— 它们归另一实例加载。
  （此条为按 home 隔离机制作出的归属推断，依据是目录结构与上表；另一实例的运行态未在本机直接抓取。）

### 已废弃的旧结论（勿采信）

本条目旧版曾断言：应用**只**加载 `~/.workbuddy/skills`，另一目录不参与加载，两者互不相通。
—— **该表述过强，已废弃。** 它对**某一个实例**成立，但**不能**推广为"全机唯一正确目录"。
正确结论见上表：**每个实例各扫各的 home**。请勿引用旧版措辞。

## 处理

1. **安装前先确认目标实例的 home**（谁要用，就装进谁的 `skills/`）。
2. 需要跨实例共用时，**两处都装**；或按使用者指定目录装，另一处用 `FSTDD_OUT` 覆盖。
   安装脚本 `OUT` 默认值已改为 `~/.workbuddy/skills`（`install_workbuddy_skills.py`）。
3. **复验三步**（缺一不可）：
   - 文件在位：`<home>/skills/<skill>/SKILL.md` 存在
   - 脚本校验：`verify_workbuddy_skills.py` 回显 `[PASS]`
   - **运行态确认：重启该实例后，技能出现在会话可用技能列表中**（前两步过、第三步不过 = 装错了 home）

## 性质

多实例 home 隔离的坑：**"装了不生效"优先怀疑"装到别的实例 home 了"，而不是"应用只认某个固定目录"。**
判断依据要落在**运行态可见性**上——静态 grep 只能证明某实例会不会读该路径，不能证明全局唯一。

> 附注：旧版经验提到「应用运行中可能把 skill 重新归置到内部目录，导致文件消失」，
> 该现象本次未复现，且可用上述 home 隔离机制解释（文件属另一个实例），保留观察但不再作为结论。
