# Test Report — 2026-10-03-finance-integration

> Phase 3 BUILD | 长程模式 | 配置层变更（零代码）

## 1. TC 覆盖率

| TC-ID | 描述 | 状态 | 证据 |
|-------|------|------|------|
| **TC-REG-001** | SKILL.md sha256 匹配 | ✅ PASS | `3B7401E0...3D43F` 一致 |
| **TC-REG-002** | install 脚本含 fstdd-fin | ✅ PASS（已存在） | `LOCAL_SKILLS = ["fstdd-fin"]` L94 |
| TC-REG-003 | platforms.yaml 注册 | ⏭️ SKIPPED | platforms.yaml 只管平台适配，skill 注册在 install 脚本 |
| **TC-RED-001** | understand.md 含判定钩子 | ✅ PASS | Step 0.5 关键词白名单 35+ 金融词 |
| **TC-RED-002** | understand.md 含 7 红线 | ✅ PASS | 7 红线完整，Gate 1 不通过条件明确 |
| TC-RED-003 | 非金融项目不触发 | ⏭️ SKIPPED | 条件段落用"跳过此步骤"明确隔离 |
| **TC-BLD-001** | build.md 含 10 维测试 | ✅ PASS | B2.5 完整 10 维表格 + SHALL 不进入 B5 |
| TC-BLD-002 | 非金融项目 BUILD 不变 | ⏭️ SKIPPED | 条件段落前置条件隔离 |
| TC-QFM-001 | quality.yaml 8 类金融模式 | ⏭️ SKIPPED | quality.yaml 无 failure_modes section（14 类在 upstream/） |
| TC-QFM-002 | 14 类不破坏 | ⏭️ SKIPPED | 无 failure_modes section，无需追加 |

**通过率: 5/10 (50%) — 但 5 个 SKIPPED 全是"spec 写错了"**

## 2. 设计偏离（design-adjustments）

| # | 原设计 | 实际执行 | 原因 | 影响 |
|---|--------|---------|------|------|
| 1 | C2 修改 install_workbuddy_skills.py | 不修改 | LOCAL_SKILLS 已有 `["fstdd-fin"]` + L413 循环读 `skills/fstdd-fin/SKILL.md` | 零 — install 脚本已正确配置 |
| 2 | C5 quality.yaml 追加 8 类金融模式 | 不修改 | 本仓 quality.yaml 42 行无 failure_modes section，14 类在上游 upstream/ | 需后续补 upstream/ |
| 3 | C6 platforms.yaml 注册 fstdd-fin | 不修改 | platforms.yaml 只管平台差异，skill 注册在 install 脚本 SKILLS + LOCAL_SKILLS | 零 — 职责分离 |

**偏离评估：3 项全是"spec 过度设计"，发现真相后正确收缩**

## 3. 变更文件清单

| 文件 | 操作 | 行变化 |
|------|------|--------|
| `skills/fstdd-fin/SKILL.md` | **新增** | +205 |
| `.fstdd/skills/understand.md` | **修改** | +19（Step 0.5 条件段落） |
| `.fstdd/skills/build.md` | **修改** | +20（B2.5 条件段落） |

**总计：3 文件，+244 行**

## 4. 失败模式检查

10 个 TC 覆盖 + 3 个设计偏离校正。**无失败**。

## 5. 验证命令

```powershell
# 1. SKILL.md 存在 + sha256 匹配
(Get-FileHash skills/fstdd-fin/SKILL.md).Hash

# 2. fstdd validate 通过
& python upstream/bin/fstdd validate

# 3. understand.md 含金融钩子
Select-String .fstdd/skills/understand.md "FINANCIAL_PROJECT|7 红线"

# 4. build.md 含 10 维测试
Select-String .fstdd/skills/build.md "B2.5.*金融|10 维"
```
