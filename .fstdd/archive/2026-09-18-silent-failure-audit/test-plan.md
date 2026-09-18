# V2.9 测试方案与详细案例

> 版本：2.9
> 创建日期：2026-09-18
> 对应 Phase 2 Spec：`canonical/specs/code/except-audit.yaml`、`mutation-testing.yaml`、`silent-except-guard.yaml`

## 一、测试策略

### 1.1 测试金字塔

- 单元测试为主（变异测试、审计工具、豁免匹配），集成层一次（审计工具 × 真实豁免清单）
- E2E 层：审计工具在完整仓库上运行（负向验证制造临时清单外点位）

### 1.2 测试原则

- 验证脚本只读：审计类用例不得修改被观测状态；制造故障用 `try/finally` 恢复（EXP-20260917-A3）
- 变异测试双自证：注入必红 + 恢复必绿，内联在同一条用例（SC-012）
- 变异注入不得 mock 被检测函数本身（SC-013）

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|----------|--------|------|----------|
| `upstream/tests/test_guard_*.py`（既有） | — | 单元 | guard 正常路径（覆盖率有，断言有效性待变异测试证） |
| `upstream/tests/test_timestamp_ops.py` | 7 | 单元 | check_timestamps L1/L2 正常路径 |
| `upstream/tests/test_evidence_ops.py` | 5 | 单元 | validate / classify_evidence 正常路径 |

## 二、详细测试案例

### 功能 1：吞异常点位审计（`except-audit`）

对应 `except-audit.yaml` → REQ-001..REQ-003

#### 案例 1.1 — 审计清单 29 处全覆盖且七字段齐全

| 字段 | 内容 |
|------|------|
| **ID** | TC-AUD-001 |
| **对应 Spec** | except-audit/spec.md → Scenario: SC-001 |
| **优先级** | P0 |
| **预置条件** | `.fstdd/audit-exceptions.yaml` 已按审计结论写入 |
| **输入** | 读取清单并与 Gate 1 盘点清单（29 处）比对 |
| **预期结果** | 29 处 100% 有对应条目；每条含 file/line/anchor/category/reason/audited_at/audited_by；category ∈ {intentional, bug-fixed, narrowed}；reason ≥10 字 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.2 — 审计不改变检测语义（全量无回归）

| 字段 | 内容 |
|------|------|
| **ID** | TC-AUD-002 |
| **对应 Spec** | except-audit/spec.md → Scenario: SC-002 |
| **优先级** | P0 |
| **预置条件** | 审计与修复全部落地 |
| **输入** | `cd upstream && python -m pytest tests -q` |
| **预期结果** | 无回归（基线 692 passed / 694 collected；bug 类修复允许新增通过） |
| **当前状态** | ❌ 待执行 |

#### 案例 1.3 — bug 类点位修复走 TDD 且真跑路径

| 字段 | 内容 |
|------|------|
| **ID** | TC-AUD-003 |
| **对应 Spec** | except-audit/spec.md → Scenario: SC-003 |
| **优先级** | P0 |
| **预置条件** | 审计发现 bug 类点位 |
| **输入** | 修复过程检查 |
| **预期结果** | 每处先有失败测试暴露缺陷（RED→GREEN）；测试真实执行该代码路径；修复后 except 块有 logger.debug 留痕 |
| **当前状态** | ❌ 测试缺 |

### 功能 2：变异测试（`mutation-testing`）

对应 `mutation-testing.yaml` → REQ-010..REQ-011

#### 案例 2.1 — guard 僵尸检测：注入「last_modified 永不过期」缺陷必红

| 字段 | 内容 |
|------|------|
| **ID** | TC-MUT-001 |
| **对应 Spec** | mutation-testing/spec.md → Scenario: SC-010 |
| **优先级** | P0 |
| **预置条件** | 构造一个 last_modified 距今 > _ZOMBIE_DAYS 的 change 目录 |
| **输入** | 真实调用 `_is_zombie()`；再 monkeypatch 注入「`_dt.now` 恒返回固定过去时刻」的变异 |
| **预期结果** | 正常调用判 True（检测会响）；变异注入后若无红 → 测试失败；finally 恢复后复测判 True（恢复绿） |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.2 — guard 卡壳检测：注入「Build 完成时间被吞」缺陷必红

| 字段 | 内容 |
|------|------|
| **ID** | TC-MUT-002 |
| **对应 Spec** | mutation-testing/spec.md → Scenario: SC-010 |
| **优先级** | P0 |
| **预置条件** | 构造 build 完成 >24h 且 deliver 未完成的 change 状态 |
| **输入** | 调用卡壳检测函数，捕获 warnings |
| **预期结果** | 注入「now - build_time 比较恒为 0」的变异后，若无 ⚠ 警告 → 测试失败；恢复后警告复现 |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.3 — check_timestamps L1 值层：注入 naive 产出必红

| 字段 | 内容 |
|------|------|
| **ID** | TC-MUT-003 |
| **对应 Spec** | mutation-testing/spec.md → Scenario: SC-010 |
| **优先级** | P0 |
| **预置条件** | 临时构造含 naive 时间戳的活跃 change YAML |
| **输入** | 运行 L1 值层检测 |
| **预期结果** | 检出违规（必红）；try/finally 删除临时 change 后全仓复扫恢复 0 违规（恢复绿） |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.4 — check_timestamps L2 源层：注入豁免清单失效条目必红

| 字段 | 内容 |
|------|------|
| **ID** | TC-MUT-004 |
| **对应 Spec** | mutation-testing/spec.md → Scenario: SC-010 |
| **优先级** | P0 |
| **预置条件** | 豁免清单中临时追加一条指向不存在位置的条目 |
| **输入** | 运行 L2 自检（find_stale_exemptions） |
| **预期结果** | 报出失效条目（必红）；finally 移除后自检通过（恢复绿） |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.5 — validate 基线警告：缺失基线 change 触发警告

| 字段 | 内容 |
|------|------|
| **ID** | TC-MUT-005 |
| **对应 Spec** | mutation-testing/spec.md → Scenario: SC-010 |
| **优先级** | P0 |
| **预置条件** | 临时 change 目录无 baseline 块 |
| **输入** | 调用 validate |
| **预期结果** | 输出含「基线: 未建立」警告；注入「baseline 读取恒为空 dict」的变异后若无警告 → 失败 |
| **当前状态** | ❌ 测试缺（TC-CONST-002 已有正向覆盖，本条加变异自证） |

#### 案例 2.6 — 变异测试双自证且内联

| 字段 | 内容 |
|------|------|
| **ID** | TC-MUT-006 |
| **对应 Spec** | mutation-testing/spec.md → Scenario: SC-012 |
| **优先级** | P1 |
| **预置条件** | 上述每个变异测试 |
| **输入** | 审查用例结构 |
| **预期结果** | 每个用例内含「注入后断言红」与「恢复后断言绿」两段，且在同一条用例内 |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.7 — 注入不 mock 被检测函数本身

| 字段 | 内容 |
|------|------|
| **ID** | TC-MUT-007 |
| **对应 Spec** | mutation-testing/spec.md → Scenario: SC-013 |
| **优先级** | P0 |
| **预置条件** | 上述每个变异测试 |
| **输入** | 审查注入手段 |
| **预期结果** | 被检测函数（_is_zombie / check 主函数等）为真实调用；mock 仅作用于其依赖或输入数据 |
| **当前状态** | ❌ 测试缺 |

### 功能 3：防回潮工具（`silent-except-guard`）

对应 `silent-except-guard.yaml` → REQ-020..REQ-022

#### 案例 3.1 — 枚举口径与盘点一致、只读、清单外非零退出

| 字段 | 内容 |
|------|------|
| **ID** | TC-GRD-001 |
| **对应 Spec** | silent-except-guard/spec.md → Scenario: SC-020 |
| **优先级** | P0 |
| **预置条件** | 豁免清单就位 |
| **输入** | `python tools/audit_silent_except.py`；运行前后对被扫描文件做哈希快照 |
| **预期结果** | 输出全部点位与匹配结果；哈希不变（只读）；构造清单外点位时退出码非零 |
| **当前状态** | ❌ 测试缺 |

#### 案例 3.2 — 行号漂移容忍（锚点匹配）

| 字段 | 内容 |
|------|------|
| **ID** | TC-GRD-002 |
| **对应 Spec** | silent-except-guard/spec.md → Scenario: SC-021 |
| **优先级** | P0 |
| **预置条件** | 某豁免条目行号与现状差 ≤5 行，函数锚点一致 |
| **输入** | 运行审计 |
| **预期结果** | 该点位判「已豁免」，不报为清单外 |
| **当前状态** | ❌ 测试缺 |

#### 案例 3.3 — 清单条目字段缺失/理由过短被报出

| 字段 | 内容 |
|------|------|
| **ID** | TC-GRD-003 |
| **对应 Spec** | silent-except-guard/spec.md → Scenario: SC-021 |
| **优先级** | P0 |
| **预置条件** | 临时在清单中加一条缺 reason / reason 仅 3 字的条目 |
| **输入** | 运行审计 |
| **预期结果** | 报出该条目无效（非零退出）；finally 还原清单后通过 |
| **当前状态** | ❌ 测试缺 |

#### 案例 3.4 — 工具自身异常明确报错（区别于发现清单外）

| 字段 | 内容 |
|------|------|
| **ID** | TC-GRD-004 |
| **对应 Spec** | silent-except-guard/spec.md → Scenario: SC-022 |
| **优先级** | P0 |
| **预置条件** | 临时把豁免清单改成非法 YAML |
| **输入** | 运行审计 |
| **预期结果** | 明确的解析错误信息 + 非零退出（区别于「清单外点位」的正常报告路径）；finally 还原 |
| **当前状态** | ❌ 测试缺 |

#### 案例 3.5 — 自证：当前仓库零误报 + 负向验证

| 字段 | 内容 |
|------|------|
| **ID** | TC-GRD-005 |
| **对应 Spec** | silent-except-guard/spec.md → Scenario: SC-023 |
| **优先级** | P0 |
| **预置条件** | 本 change 完成后仓库 |
| **输入** | 运行审计；再临时写一个含吞 except 的 .py 到 tools/ |
| **预期结果** | 前者退出 0 且无字段警告；后者被报出且非零退出；finally 删除临时文件 |
| **当前状态** | ❌ 测试缺 |

#### 案例 3.6 — 检测语义文件的裸 pass 单独标级

| 字段 | 内容 |
|------|------|
| **ID** | TC-GRD-006 |
| **对应 Spec** | silent-except-guard/spec.md → Scenario: SC-024 |
| **优先级** | P1 |
| **预置条件** | 清单中一处 intentional 且无 logger 留痕的检测语义文件条目 |
| **输入** | 运行审计 |
| **预期结果** | 该点位带 intentional-no-trace 标记且出现在报告 summary |
| **当前状态** | ❌ 测试缺 |

## 三、测试执行矩阵

| 功能模块 | 单元 | 集成 | E2E | 状态 |
|----------|------|------|-----|------|
| 审计清单（AUD-001..003） | ✅ 清单完整性 | ✅ 全量无回归 | — | 🟡 待实现 |
| 变异测试（MUT-001..007） | ✅ 五路径双自证 | ✅ 注入恢复 | — | 🟡 待实现 |
| 防回潮工具（GRD-001..006） | ✅ 匹配/字段/容错 | ✅ 真实仓库自证 | ✅ 负向验证 | 🟡 待实现 |

共 16 TC。
