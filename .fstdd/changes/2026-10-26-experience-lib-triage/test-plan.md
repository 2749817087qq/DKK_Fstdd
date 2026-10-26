# FSTDD v3.4.0 经验库诊断修复测试方案

> 版本：v3.4.0（增量修复）
> 创建日期：2026-10-26
> 对应 Phase 2 Spec：`.fstdd/changes/2026-10-26-experience-lib-triage/specs/experience-lib-triage/spec.md`
> Change: `2026-10-26-experience-lib-triage`
> Task Type: `code`

## 一、测试策略

### 1.1 测试金字塔

| 层级 | 用例数 | 比例 | 侧重点 |
|------|-------|------|--------|
| 单元 | 11 | 100% | 3 项修复的核心逻辑（fsync / edges 去重 / TC 定义点） |
| 集成 | 0 | 0% | 依赖 `_save_index`/`_save_graph` 的下游 CLI（本轮不改） |
| E2E | 0 | 0% | 门禁 `ci check-failures` 由框架自身覆盖 |

### 1.2 测试原则

- **TDD 优先**：先写测试，再改实现；测试红→绿循环
- **回归保护**：每项修复至少 1 个 regression 断言，防止未来回退
- **边界显式**：Windows 上目录 fsync 抛 PermissionError 是 OS 特性，不是 bug —— 断言文件 fsync 至少 1 次即可
- **不覆盖引用**：TC-ID 按**定义点**提取（形态 A 表格行），裸引用不算 planned

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|---------|-------|------|---------|
| `tests/test_experience_lib_fixes.py` | 11 | 单元 | EXP-0062 / EXP-0055 / EXP-0067 三项修复 |

## 二、详细测试案例

### 功能 A：EXP-2026-0062 关键写入点 fsync 原子落盘

对应 spec Requirement R3.1.1 / R3.1.2 / R3.1.3

#### 案例 A.1 — `_save_index` 落盘后必须 fsync 文件本体

| 字段 | 内容 |
|------|------|
| **ID** | TC-ELT-001 |
| **对应 Spec** | spec.md → Scenario: 关键写入点 fsync 保证断电一致性 |
| **优先级** | P0 |
| **预置条件** | GIVEN 一个空的 exp_dir（tmp_path） |
| **输入** | WHEN 调用 `_save_index(exp_dir, {"last_id": 1, "total": 0})` 且 mock `os.fsync` |
| **预期结果** | THEN `os.fsync` 至少被调用 1 次 AND 索引文件已生成 AND 内容 YAML 合法 |
| **当前状态** | ✅ 已覆盖 |

#### 案例 A.2 — `_save_index` 走 `os.replace` 原子替换，不留 `.tmp` 残留

| 字段 | 内容 |
|------|------|
| **ID** | TC-ELT-002 |
| **对应 Spec** | spec.md → Scenario: 原子替换不留临时文件 |
| **优先级** | P0 |
| **预置条件** | GIVEN tmp_path 已存在（首次写） |
| **输入** | WHEN 调用 `_save_index` 且 mock `os.replace` |
| **预期结果** | THEN `os.replace` 至少调用 1 次 AND `.tmp` 文件已清理 |
| **当前状态** | ✅ 已覆盖 |

#### 案例 A.3 — `_save_graph` 落盘前 fsync 文件本体

| 字段 | 内容 |
|------|------|
| **ID** | TC-ELT-003 |
| **对应 Spec** | spec.md → Scenario: KG 图谱 fsync 保证断电一致性 |
| **优先级** | P0 |
| **预置条件** | GIVEN tmp_path 与合法 graph dict |
| **输入** | WHEN 调用 `_save_graph(graph_path, graph)` 且 mock `os.fsync` |
| **预期结果** | THEN `os.fsync` 至少被调用 1 次 AND graph 文件已生成 |
| **当前状态** | ✅ 已覆盖 |

#### 案例 A.4 — `_atomic_write_text` helper 走 tmp+fsync+replace

| 字段 | 内容 |
|------|------|
| **ID** | TC-ELT-004 |
| **对应 Spec** | spec.md → Scenario: 新增 helper 被 experience 写入路径复用 |
| **优先级** | P1 |
| **预置条件** | GIVEN 目标文件的父目录不存在 |
| **输入** | WHEN 调用 `_atomic_write_text(target, content)` |
| **预期结果** | THEN 父目录已创建 AND 文件内容 == 输入 content |
| **当前状态** | ✅ 已覆盖 |

### 功能 B：EXP-2026-0055 知识图谱 edges 幂等去重

对应 spec Requirement R3.2.1 / R3.2.2 / R3.2.3

#### 案例 B.1 — 相同 (A,B) 边保留 last_synced_at 最新的一条

| 字段 | 内容 |
|------|------|
| **ID** | TC-ELT-005 |
| **对应 Spec** | spec.md → Scenario: 同向重复边去重 |
| **优先级** | P0 |
| **预置条件** | GIVEN 3 条 KG-001→KG-002 边，last_synced_at 不同 |
| **输入** | WHEN 调用 `_dedupe_edges(edges)` |
| **预期结果** | THEN 结果长度 == 1 AND last_synced_at 是最新的（2026-10-25） |
| **当前状态** | ✅ 已覆盖 |

#### 案例 B.2 — (A,B) 与 (B,A) 视为同一条边（无向）

| 字段 | 内容 |
|------|------|
| **ID** | TC-ELT-006 |
| **对应 Spec** | spec.md → Scenario: 无向边去重 |
| **优先级** | P0 |
| **预置条件** | GIVEN 2 条反向边：KG-001→KG-002 与 KG-002→KG-001 |
| **输入** | WHEN 调用 `_dedupe_edges(edges)` |
| **预期结果** | THEN 结果长度 == 1 AND last_synced_at 取最新一条 |
| **当前状态** | ✅ 已覆盖 |

#### 案例 B.3 — 自环与空 from/to 边被丢弃

| 字段 | 内容 |
|------|------|
| **ID** | TC-ELT-007 |
| **对应 Spec** | spec.md → Scenario: 非法边（自环/空端点）被过滤 |
| **优先级** | P1 |
| **预置条件** | GIVEN 4 条边：自环、空 from、空 to、合法 |
| **输入** | WHEN 调用 `_dedupe_edges(edges)` |
| **预期结果** | THEN 结果长度 == 1 AND 保留的是合法边 |
| **当前状态** | ✅ 已覆盖 |

#### 案例 B.4 — `_save_graph` 落盘前统一去重 edges

| 字段 | 内容 |
|------|------|
| **ID** | TC-ELT-008 |
| **对应 Spec** | spec.md → Scenario: 去重作为落盘前的收口动作 |
| **优先级** | P0 |
| **预置条件** | GIVEN graph 含 3 条重复边（2 条 KG-001↔KG-002 不同向） |
| **输入** | WHEN 调用 `_save_graph` 后重新加载 |
| **预期结果** | THEN 落盘后 edges 长度 == 1 |
| **当前状态** | ✅ 已覆盖 |

### 功能 C：EXP-2026-0067 ci check-failures 的 TC planned 只按定义点提取

对应 spec Requirement R3.3.1 / R3.3.2 / R3.3.3

#### 案例 C.1 — 形态 A 表格行为最高优先级，裸引用不计入

| 字段 | 内容 |
|------|------|
| **ID** | TC-ELT-009 |
| **对应 Spec** | spec.md → Scenario: 定义点提取优先级 |
| **优先级** | P0 |
| **预置条件** | GIVEN 一段 markdown：形态 A 表格定义 TC-FIX-001/002 + 一处引用 TC-OTHER-999 |
| **输入** | WHEN 调用 `_tcid_definition_points(content)` |
| **预期结果** | THEN 返回集合 == {TC-FIX-001, TC-FIX-002} AND 不含 TC-OTHER-999 |
| **当前状态** | ✅ 已覆盖 |

#### 案例 C.2 — 无标准表格定义时返回空列表（由调用方 fallback）

| 字段 | 内容 |
|------|------|
| **ID** | TC-ELT-010 |
| **对应 Spec** | spec.md → Scenario: 裸文本列表不被视为定义点 |
| **优先级** | P1 |
| **预置条件** | GIVEN 一段 markdown：裸列表 `- TC-OLD-001: ...` |
| **输入** | WHEN 调用 `_tcid_definition_points(content)` |
| **预期结果** | THEN 返回空列表（定义点 API 只识别表格式） |
| **当前状态** | ✅ 已覆盖 |

#### 案例 C.3 — `check_tc_implementation_coverage` 不把引用 TC 算入 planned

| 字段 | 内容 |
|------|------|
| **ID** | TC-ELT-011 |
| **对应 Spec** | spec.md → Scenario: TC planned 只按定义点提取，引用不算 |
| **优先级** | P0 |
| **预置条件** | GIVEN test-plan.md 含 2 个定义（TC-LOCAL-001/002）+ 2 个引用（TC-EXTERNAL-555/556）；tests/ 含 TC-LOCAL-001 实现 |
| **输入** | WHEN 调用 `check_tc_implementation_coverage` |
| **预期结果** | THEN 消息中提到 TC-LOCAL-002 缺失 AND 不含 TC-EXTERNAL |
| **当前状态** | ✅ 已覆盖 |

## 三、测试执行矩阵

| 功能模块 | 单元测试 | 集成测试 | E2E | 状态 |
|----------|---------|---------|-----|------|
| EXP-0062 fsync（`_save_index` / `_save_graph` / `_atomic_write_text`） | 4 用例 | - | - | 🟢 |
| EXP-0055 edges 去重（`_dedupe_edges` / `_save_graph`） | 4 用例 | - | - | 🟢 |
| EXP-0067 TC 定义点提取（`_tcid_definition_points` / `check_tc_implementation_coverage`） | 3 用例 | - | - | 🟢 |

## 四、回归风险矩阵

| 风险区域 | V3.4.0 改动 | 已有回归保护 | 风险等级 |
|---------|------------|-------------|---------|
| `_save_index`（EXP-0062） | 加 fsync + `_fsync_after_write` | TC-ELT-001/002 | 🟢 |
| `_save_graph`（EXP-0062 + EXP-0055） | 加 fsync + 去重 | TC-ELT-003/008 | 🟢 |
| `_atomic_write_text`（新增 helper） | 新函数 | TC-ELT-004 | 🟢 |
| `_dedupe_edges`（新增 helper） | 新函数 | TC-ELT-005/006/007 | 🟢 |
| `check_tc_implementation_coverage`（EXP-0067） | planned 按定义点提取 | TC-ELT-009/010/011 | 🟢 |
| 未处理（后续迭代） | EXP-0018 缺锁 / EXP-0044 yaml.dump 破坏注释 / EXP-0045 相关 | 见 DELIVER 后续建议 | 🟡 |

## 五、建议补充顺序

1. **第一优先（部署前必补）**：无 —— 本轮 3 项修复 P0 全部覆盖
2. **第二优先（部署后尽快补）**：EXP-0044 保守合并写回的经验库更新（`experience.py:897`）
3. **第三优先（后续补）**：EXP-0018 phase advance 加 `_index_lock`；EXP-0067 范围蔓延 / 锚定检查 SKIP 修复

## 六、证据记录

> 每条引用实测数据的证据必须可定位**观测时刻**与**代码版本**（TC-EPR-002）。

| 证据 | observed_at | observed_base_git_sha | 来源 |
|------|-------------|----------------------|------|
| 11/11 TDD 测试通过 | 2026-10-26T13:52:00+08:00 | 2096839 | `pytest tests/test_experience_lib_fixes.py -v` → 11 passed |
| ci check-failures 门禁 0 error | 2026-10-26T13:52:30+08:00 | 2096839 | `python -m fstdd ci check-failures 2026-10-26-experience-lib-triage` → 4 PASS / 1 WARN / 5 SKIP / 0 FAIL |
| Windows os.open(dir, O_RDONLY) 抛 PermissionError | 2026-10-26T13:50:00+08:00 | 2096839 | 手动 python -c 探针；目录 fsync 静默降级已在测试注释中说明 |

- `observed_at` 是**信息采集时刻**，不是文档生成时刻（generated_at 与此无关）。
- 缺 `observed_at` 的证据时效判为「无法判定」（undetermined），**不等同未过期**。

## 七、金融 10 维测试覆盖

> FINANCIAL_PROJECT=NO（本 change 不涉及金融业务逻辑）—— 章节跳过。
