# 2026-10-04-baseline-failures-zero 测试方案与详细案例

> 版本：v1（Gate 2 候选）
> 创建日期：2026-10-04
> 对应 Phase 2 Spec：
>   - `canonical/specs/code/2026-10-04-baseline-failures-zero.yaml`（REQ-001..004 / SC-001..008）
>   - `canonical/specs/agent/2026-10-04-baseline-failures-zero.yaml`（step 1..5）
> 说明：本方案的 Scenario→TC 映射以 Canonical YAML 为准；TC-ID 规则 `TC-<CAPABILITY>-<NNN>`，
> **BFZ** = `baseline-failures-zero`。

## 一、测试策略

### 1.1 测试金字塔

本变更为**基线治理**：不新增产品模块、不新增服务进程，只修复 4 组已存在的基线红灯
并为其固定回归保护。因此**不建 E2E 层**，全部落在单元 + 集成两层：

| 层次 | TC 数 | 占比 | 侧重点 |
|------|-------|------|--------|
| 单元测试 | 3 | 37% | 模板字节比较、豁免清单自检、分类/严重度一致性 —— 纯函数与只读文件比较 |
| 集成测试 | 5 | 63% | 实况扫描指纹集合、子进程退出码、全仓 naive 扫描只读性、全量回归与四自检脚本 |
| E2E | 0 | 0% | 不适用：本变更不引入外部进程边界 |

选择理由：本变更的风险不在新增逻辑，而在**「修一个红，别弄出另一个红」**——
模板双源、审计表与扫描器漂移、测试的环境耦合、检测器豁免失效，四者互为回归面。
必须以「实况扫描 / 真实子进程 / 全量套件」作为判据，而非阅读代码。

### 1.2 测试原则

- **修代码、不 skip**：6 项预存失败必须由实现修复转绿，不得通过 `skip` / `xfail` /
  删除用例掩盖（SC-008 显式断言「不产生新 skip」）。
- **零漂移而非近似**：审计表指纹集合必须与实况扫描**完全相等**（多重集合），
  行号仅允许 ±5 容差；「差不多」不算通过。
- **测试自隔离（hermetic）**：显式 publish 用例不得依赖运行环境是否具备 scp 目标的
  SSH 别名/凭证；结论在任意环境必须一致（SC-004）。
- **只读扫描**：naive 时间戳扫描前后文件哈希必须不变（SC-005），
  防止检测器自身产生写副作用。
- **豁免必须有理由且可定位**：每条豁免须可在源码定位，失效豁免数 = 0（SC-006）。
- **禁止静默吞错**：审计表本身即针对裸 `except` 的审计，测试亦不得以 `except: pass` 吞异常。

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|----------|--------|------|----------|
| `upstream/tests/test_constitution_ops.py` | 含 `test_tmpl_001_dual_source_templates_identical` | 集成 | 模板双源字节一致 |
| `upstream/tests/test_evidence_ops.py` | 含 `test_epr_003_templates_consistent_with_examples` | 集成 | 模板与示例一致 |
| `upstream/tests/test_except_audit.py` | 含 `test_aud_002/003/004/005` | 单元 + 集成 | 审计表指纹/分类/严重度/检测路径 |
| `upstream/tests/test_guard_silent_except.py` | 含 `test_grd_001_check_passes_on_current_repo` | 集成 | 审计哨兵在当前仓通过 |
| `upstream/tests/test_silent_share.py` | 含 `test_tc_cas_008b_explicit_publish_still_nonzero` | 集成 | 显式 `--publish` 失败非零 |
| `upstream/tests/test_timestamp_ops.py` | 含 `test_tsn_005/006/007` | 单元 + 集成 | 豁免自检 / 全仓 naive 清零 / 只读 |

已实测确认的测试前置条件：

| 前置条件 | 实测状态 |
|----------|----------|
| 解释器 | F 侧 default env python（3.13.14，含 PyYAML 6.0.3） |
| 观测基线 | `e7bfb45755f48387225a8ecb4da0a2dd38ec4603`（工作树除本变更外干净） |
| 实况 except 扫描 | 25 点（承接归档 19 点 + 新增 6 点） |
| naive 时间戳 | 观测时 13 条待清零（8 值层 + 2 真时间戳 + 3 标识符豁免） |
| 基线红灯 | 6 项（模板双源 / 审计表漂移 / publish 环境耦合 / naive 值层 + 源层） |

---

## 二、详细测试案例

TC-ID 规则：`TC-<CAPABILITY>-<NNN>`，**BFZ** = `baseline-failures-zero`（REQ-001..004）。

### 功能 1：模板双源一致（REQ-001 / TC-BFZ-001）

#### 案例 1.1 — 项目模板与镜像模板字节一致

| 字段 | 内容 |
|------|------|
| **ID** | TC-BFZ-001 |
| **对应 Spec** | baseline-failures-zero/spec.yaml → Scenario: SC-001 |
| **优先级** | P0 |
| **预置条件** | `.fstdd/templates/` 已含 finance 段，`upstream/.fstdd/templates/` 尚未同步 |
| **输入** | 逐文件比较两处 `templates` 目录的字节内容与文件集合 |
| **预期结果** | `canonical/proposal.yaml`、`canonical/spec.yaml`、`test-plan.md` 三文件字节相等，目录集合相等；不改模板语义内容 |
| **当前状态** | ✅ 已覆盖（`test_tmpl_001_dual_source_templates_identical` / `test_epr_003_templates_consistent_with_examples`） |

### 功能 2：裸 except 审计表零漂移（REQ-002 / TC-BFZ-002..003）

#### 案例 2.1 — 审计活表指纹集合与实况扫描完全相等

| 字段 | 内容 |
|------|------|
| **ID** | TC-BFZ-002 |
| **对应 Spec** | baseline-failures-zero/spec.yaml → Scenario: SC-002 |
| **优先级** | P0 |
| **预置条件** | 实况扫描得 25 点；归档表 19 点且 guard.py 5 处行号位移超容差 |
| **输入** | 以活表路径执行指纹多重集合比较与行号容差校验 |
| **预期结果** | 活表 points 指纹多重集合与实况完全相等；每条行号偏差 ≤ 5；guard.py 刷新为 317/381/454/473/1265 |
| **当前状态** | ✅ 已覆盖（`test_aud_002_table_matches_live_scan`） |

#### 案例 2.2 — 分类合法性、理由覆盖与严重度/响应一致性

| 字段 | 内容 |
|------|------|
| **ID** | TC-BFZ-003 |
| **对应 Spec** | baseline-failures-zero/spec.yaml → Scenario: SC-003 |
| **优先级** | P1 |
| **预置条件** | 活表共 25 点，含 1 条 意外吞错（EA-019） |
| **输入** | 校验 classification 枚举、justification 非空、severity/response 一致性、detection_path |
| **预期结果** | 每点 classification ∈ {合理容错, 意外吞错, 收窄建议} 且 justification 非空；合理容错 → response=放行；意外吞错 → severity∈{p1,p2} 且 response≠放行；保留 ≥1 条「意外吞错 + detection_path=true」；不改源码 except 行为 |
| **当前状态** | ✅ 已覆盖（`test_aud_003_classification_and_justification` / `test_aud_004_severity_and_response_consistency` / `test_aud_005_detection_paths_flagged`） |

### 功能 3：显式 publish 失败语义自隔离（REQ-003 / TC-BFZ-004）

#### 案例 3.1 — 显式 `--publish` 失败仍返回非零且不依赖环境

| 字段 | 内容 |
|------|------|
| **ID** | TC-BFZ-004 |
| **对应 Spec** | baseline-failures-zero/spec.yaml → Scenario: SC-004 |
| **优先级** | P0 |
| **预置条件** | publish() 优先级 1 为 scp 通道，在具备 fstdd-hub 别名的环境可成功 |
| **输入** | 用例内 monkeypatch `publish_via_scp` 为失败并令 inbox 指向死端口后调用 `main()` |
| **预期结果** | `main()` 返回 1（显式命令失败→非零）；隔离只作用于测试，不改 publish() 生产三档降级逻辑；静默路径零阻塞语义不受影响 |
| **当前状态** | ✅ 已覆盖（`test_tc_cas_008b_explicit_publish_still_nonzero`） |

### 功能 4：全仓 naive 时间戳清零（REQ-004 / TC-BFZ-005..007）

#### 案例 4.1 — 值层零 naive 且扫描只读

| 字段 | 内容 |
|------|------|
| **ID** | TC-BFZ-005 |
| **对应 Spec** | baseline-failures-zero/spec.yaml → Scenario: SC-005 |
| **优先级** | P0 |
| **预置条件** | notices-authenticity-gate 的 8 处时间值缺时区后缀 |
| **输入** | 执行 `tools/check_timestamps.py --repo .` 全仓扫描 |
| **预期结果** | naive 计数为 0；扫描前后文件哈希不变（只读）；扫描范围显式列出且含 changes / canonical / templates |
| **当前状态** | ✅ 已覆盖（`test_tsn_007_full_scan_zero_naive_and_readonly`） |

#### 案例 4.2 — 豁免清单自检零失效且类别覆盖

| 字段 | 内容 |
|------|------|
| **ID** | TC-BFZ-006 |
| **对应 Spec** | baseline-failures-zero/spec.yaml → Scenario: SC-006 |
| **优先级** | P1 |
| **预置条件** | 新增 3 条 category=identifier 豁免（hub_client / share_experience / verify_notices） |
| **输入** | 执行豁免清单自检 `find_stale_exemptions` |
| **预期结果** | 失效豁免数为 0（每条豁免均可定位）；每条豁免附非空理由；豁免类别覆盖 pure_date/identifier/year_extract/comparison 四类 |
| **当前状态** | ✅ 已覆盖（`test_tsn_005_exemption_classes_clean` / `test_tsn_006_exemption_self_check`） |

#### 案例 4.3 — 真时间戳产出源层改为 aware

| 字段 | 内容 |
|------|------|
| **ID** | TC-BFZ-007 |
| **对应 Spec** | baseline-failures-zero/spec.yaml → Scenario: SC-007 |
| **优先级** | P0 |
| **预置条件** | tools/heartbeat.py 与 tools/fstdd003_daily_share.py 产出的时间戳原为 naive |
| **输入** | 扫描这两个文件的 L2 源层 |
| **预期结果** | 其代码行不再被判为 naive 产出（含 timezone 感知标记）；保留原墙钟显示语义（本地时区 aware），不改变日志读取习惯 |
| **当前状态** | ✅ 已覆盖（`test_tsn_007_full_scan_zero_naive_and_readonly` 覆盖源层计数归零） |

### 功能 5：全量回归与发布门禁（REQ-004 / TC-BFZ-008）

#### 案例 5.1 — 全量 pytest 0 failed 且四自检脚本全绿

| 字段 | 内容 |
|------|------|
| **ID** | TC-BFZ-008 |
| **对应 Spec** | baseline-failures-zero/spec.yaml → Scenario: SC-008 |
| **优先级** | P0 |
| **预置条件** | 4 组修复全部落地 |
| **输入** | 执行全量 `pytest upstream/tests -q` 与 verify_rename / verify_eol / verify_skill_standards / verify_workbuddy_skills |
| **预期结果** | pytest 0 failed；四个自检脚本全绿；基线失败数由 6 降为 0；不产生新的 skip 以掩盖失败 |
| **当前状态** | ✅ 已覆盖（全量套件 + `test_grd_001_check_passes_on_current_repo`；自检脚本由发布规程 §三 门禁保证） |

---

## 三、测试执行矩阵

| 功能模块 | 单元测试 | 集成测试 | E2E | 状态 |
|----------|---------|----------|-----|------|
| 模板双源（REQ-001） | — | `test_tmpl_001` / `test_epr_003` | — | 🟢 |
| 审计表（REQ-002） | `test_aud_003/004/005` | `test_aud_002` / `test_grd_001` | — | 🟢 |
| 显式 publish（REQ-003） | — | `test_tc_cas_008b` | — | 🟢 |
| naive 时间戳（REQ-004） | `test_tsn_005/006` | `test_tsn_007` | — | 🟢 |
| 全量门禁（REQ-004） | — | 全量 pytest + 四自检脚本 | — | 🟢 |

## 四、回归风险矩阵

| 风险区域 | V3.3.1 改动 | 已有回归保护 | 风险等级 |
|----------|-------------|-------------|---------|
| `.fstdd/templates/**` ↔ `upstream/.fstdd/templates/**` | 镜像补齐 3 文件 | `test_tmpl_001` / `test_epr_003` | 🟢 |
| `changes/*/audit/except-points.yaml` 优先于 `archive/*` | 新建活表 25 点 | `test_aud_002/003/004/005` / `test_grd_001` | 🟡 |
| `tools/publish` 三档降级 | 仅测试隔离，不改生产逻辑 | `test_tc_cas_008b` + 静默路径用例 | 🟢 |
| `tools/check_timestamps.py` 豁免清单 | +3 identifier 豁免 | `test_tsn_005/006` | 🟢 |
| `tools/heartbeat.py` / `tools/fstdd003_daily_share.py` | 时间戳改 aware | `test_tsn_007` + 日志读取 | 🟡 |
| `changes/*/.fstdd.yaml` 基线块 | 测试副作用回写 | 跑完 `git checkout --` 还原 | 🟡 |

## 五、建议补充顺序

1. **第一优先**（部署前必补）：TC-BFZ-001、TC-BFZ-002、TC-BFZ-004、TC-BFZ-005、TC-BFZ-007、TC-BFZ-008
2. **第二优先**（部署后尽快补）：TC-BFZ-003、TC-BFZ-006
3. **第三优先**（后续补）：无

## 六、证据记录

> 每条引用实测数据的证据必须可定位**观测时刻**与**代码版本**（TC-EPR-002）。

| 证据 | observed_at（带时区） | observed_base_git_sha | 来源 |
|---|---|---|---|
| 实况 except 扫描 25 点 | 2026-10-04T00:20:00+00:00 | e7bfb45755f48387225a8ecb4da0a2dd38ec4603 | `tools/audit_silent_except.py --check` 输出 |
| 基线失败 6 项清单 | 2026-10-04T00:20:00+00:00 | e7bfb45755f48387225a8ecb4da0a2dd38ec4603 | `pytest upstream/tests -q` 输出 |
| naive 时间戳 13 条待清零 | 2026-10-04T00:20:00+00:00 | e7bfb45755f48387225a8ecb4da0a2dd38ec4603 | `tools/check_timestamps.py --repo .` 输出 |
| 模板双源差异方向（src 为超集，3 文件） | 2026-10-04T00:20:00+00:00 | e7bfb45755f48387225a8ecb4da0a2dd38ec4603 | 逐文件字节比较脚本输出 |

- `observed_at` 是**信息采集时刻**，不是文档生成时刻（generated_at 与此无关）。
- 缺 `observed_at` 的证据时效判为「无法判定」（undetermined），**不等同未过期**。

## 七、金融 10 维测试覆盖

> 本变更非金融项目（FINANCIAL_PROJECT ≠ YES），按模板规定跳过此章节。