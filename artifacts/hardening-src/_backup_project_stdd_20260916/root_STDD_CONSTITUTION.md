# STDD 流程强制契约 / Process Constitution

> V3.0.1 | 本项目启用 STDD 流程管控。以下规则**不可协商、不可跳过**。
> V3.0.1 | This project enforces STDD process control. The following rules are **non-negotiable**.

## ⚠️ 核心规则 / Core Rules

### 1. 所有代码修改必须通过 STDD Change
- 新功能 / 重构 / Bug 修复 → 先 `/stdd-understand <描述>`
- **不得在没有 active change 的情况下直接编辑代码**
- Guard 会自动拦截未经授权的 Write/Edit 操作

### 2. 每个 Change 必须走完完整的 4 Phase（V3.0.5）
- Phase 1 Understand → Phase 2 Spec → Phase 3 Build → Phase 4 Deliver
- **Phase 3 (Build) 不可跳过 — 即使所有测试通过**（Build = 切片规划 + TDD 实现 + 质量验证合并）
- Build 包含：per-slice 证据链 + 失败模式检查 + test-report.md

### 3. 三道 Gate 必须用户明确确认
- Gate 1: 用户确认 proposal（范围与边界）
- Gate 2: 用户确认 design + specs（技术方案）
- Gate 3: 用户确认 test-report（质量验收）
- **不得自行判断"用户可能已经同意了"**

### 4. Agent 操作也受 STDD 管理
- 多系统协调 / 数据处理 / 部署迁移等 Agent 任务 → 同样需要走 STDD Change
- Agent 操作完成后必须执行 CP 检查点验证（agent verify）

### 5. TDD 严格执行
- RED（先写失败测试）→ GREEN（最小实现）→ REFACTOR（重构优化）
- **不得"先写代码后补测试"**
- 每个 Slice 必须通过 per-slice 验证才能进入下一个 Slice

### 6. 经验闭环（V3.0.1 修订：经验外发默认禁用）
- Build 阶段发现的失败模式**仅在本地**记录到 `.stdd/experiences/`
- ⛔ **Phase 4 (Deliver) 的"经验上传到社区"默认禁用** —— 属**数据外发**
  - 外发目标为**第三方外部仓库**：`github.com/leonai42/stdd-experiences` / `gitee.com/leonai42/stdd-experiences`
  - **仅当用户在当次对话中显式要求**时才可执行；执行前须逐条列出待上传 EXP-ID 供用户确认
  - 未获显式授权时**跳过** Step 2.8 / Step 2.9，输出 `⏭️ 经验上传已禁用（默认）`
- 每次 Phase 3 (Build) 开始前加载**本地**经验库预防已知错误

### 7. ⛔ 升级后必须重新施加"经验外发禁用"补丁（不可跳过）
- **触发时机**：每次执行 STDD 升级（`stdd upgrade` / `stdd-upgrade` 技能）**之后**，立即执行本条。
- **原因**：`stdd upgrade` 会用上游版本覆盖 `.stdd/skills/deliver.md`，**静默抹掉** Step 2.8 的禁用声明。
- **重施目标**：`.stdd/skills/deliver.md` → `### Step 2.8`，按 **附录 A** 的文本重贴禁用声明。
- **校验命令**（必须回显 `OK: 防线在位`）：
  ```bash
  grep -q "⛔ 默认禁用" .stdd/skills/deliver.md && echo "OK: 防线在位" \
    || echo "⚠️ 防线已被覆盖，请按 STDD_CONSTITUTION.md 第 7 条重新施加"
  ```
- **未通过校验前，禁止进入/执行任何 Deliver 阶段**。

## 📎 附录 A：Step 2.8 禁用声明（重施用文本）
> 升级覆盖后，把下面这段整体贴回 `.stdd/skills/deliver.md` 的 `### Step 2.8` 标题下方：

```
> **⛔ 默认禁用 · 本步骤属数据外发，未经用户显式授权一律跳过。**
> 本步骤会把项目沉淀的经验上传到 STDD 外部社区仓库（第三方）：
> github.com/leonai42/stdd-experiences / gitee.com/leonai42/stdd-experiences。
> - 默认不执行；仅当用户在当次对话中显式要求时才可执行。
> - 执行前须逐条列出待上传的 EXP-ID 与来源 change，交由用户确认。
> - 未获显式授权时跳过，输出：⏭️ 经验上传已禁用（默认），跳过 Step 2.8
> - 本文件由 stdd upgrade 覆盖 —— 升级后须按 STDD_CONSTITUTION.md 第 7 条重新施加。
```

## 🔧 常用命令

| 命令 | 用途 |
|------|------|
| `/stdd-understand <需求>` | 启动新 Change（Phase 1） |
| `/stdd-spec` | 进入规格设计（Phase 2） |
| `/stdd-continue` | 继续执行当前 Change |
| `stdd status` | 查看当前 Change 状态 + Guard 状态 |
| `stdd guard status` | 查看 Guard 运行状态 |
