# 时间基线 测试方案与详细案例

> 版本：v1.0（对应 change `2026-09-17-time-baseline`）
> 创建日期：2026-09-17
> 创建时刻：`2026-09-17T15:33:00+00:00`（UTC）
> 基线：HEAD `05bb9d2` | 测试基线：**641 收集用例 / 640 passed / 1 skipped**
> 对应 Phase 2 Spec：
> - `canonical/specs/code/time-baseline.yaml`（21 REQ 中的 REQ-001..004）
> - `canonical/specs/code/timestamp-normalization.yaml`（REQ-005..007）
> - `canonical/specs/code/evidence-provenance.yaml`（REQ-008..009）
> - `canonical/specs/code/clock-alignment.yaml`（REQ-010..012）
> - `canonical/specs/code/constitution.yaml`（REQ-013..015）
> - `canonical/specs/code/artifact-templates.yaml`（REQ-016..018）
> - `canonical/specs/code/canon-dual-track.yaml`（REQ-019..021）
> 合计 **21 REQ / 47 Scenario / 52 TC**

## 一、测试策略

### 1.1 测试金字塔

| 层次 | 占比 | 载体 | 覆盖对象 |
|---|---|---|---|
| 单元 | ~65% | `tests/test_baseline_ops.py`、`tests/test_time_format_ops.py`、`tests/commands/test_baseline.py` | 归一函数、三态判定、时间戳正则、豁免清单、幂等性 |
| 集成 | ~30% | 同上（真实调用 CLI 子进程 + 临时仓库夹具） | `fstdd baseline` 三动作、Gate 1 写基线、`canon verify`、`validate` 警告 |
| E2E | ~5% | 临时 git 仓库 + 干净克隆夹具 | 干净克隆 `canon verify` 2/2、跨行尾往返一致性 |

**侧重点**：本 change 的核心风险不在"逻辑复杂"，而在**"看起来生效其实没生效"**（EXP-20260917-A2/A4）与**"把测不准报成正常"**（三态判定）。因此测试策略的重心是：

1. **每个检查工具都要先证明它自己能失败** —— 三态判定、DC-HASH 校验、豁免清单自检，都必须有一个"构造必然失败场景"的用例。
2. **禁止以"源码里出现某字符串"作为判据** —— CLI 五处注册中有三处是字符串，grep 必然全绿而命令仍可能不可执行（EXP-20260915-B1）。一切验收走**真实调用**。
3. **变异测试** —— 对归一函数与三态判定注入已知缺陷，确认断言能捕获。

### 1.2 测试原则

1. **先写失败测试（RED），再最小实现（GREEN）** —— 每个 Slice 遵守 TDD，禁止先写代码后补测试。
2. **断言必须能捕获真实缺陷** —— 新写的断言密集测试须做变异测试（纯内存注入，零文件残留）。
3. **验证脚本只读** —— 巡检类用例不得修改被观测状态；如必须制造故障，用 `try/finally` 兜底恢复，绝不把"恢复现场"写成正常路径的最后一步（EXP-20260917-A3，high）。
4. **区分环境干扰与真实缺陷** —— 沙箱删除守卫、WSL 启动器、`Path("/tmp")` 解析等问题应**跳过**（skip）而非放宽断言。
5. **假信号驱动的批量修复之前，必须用第二手段复核** —— 曾因 `grep -c $'\r'` 的假信号差点重写 15 个本已正确的文件。
6. **`git status` 说 `M` ≠ 内容变了** —— 判定"有没有变"必须比对工作区字节与 HEAD blob，不能看状态字母。
7. **契约字符串改动前先 grep 全仓** —— 改 `MIRROR_TARGET` 之类的契约字符串时，测试断言会连带失配。
8. **远端操作必须幂等** —— 本机经 ssh 的命令会执行两次。

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|---|---|---|---|
| `upstream/tests/test_mirror_alert_ops.py` | 45 | 集成 | 镜像告警：钩子、巡检命令、故障标记、控制面上报 |
| `upstream/tests/test_inbox_endpoint.py` | 44 | 集成 | 经验端点协议（限流、批量、脱敏） |
| `upstream/tests/test_fstdd_matrix.py` | 40 | 矩阵 | 40 场景 CLI 行为矩阵 |
| `upstream/tests/commands/test_experience.py` | 33 | 单元 | 经验库增删改查 |
| `upstream/tests/test_cross_cutting_verification.py` | 24 | 跨切面 | 跨模块一致性 |
| `upstream/tests/test_silent_share.py` | 23 | 集成 | 静默回传 |
| `upstream/tests/test_inbox_pull.py` | 23 | 集成 | 待审核池拉取 |
| `upstream/tests/commands/test_gate.py` | 23 | 单元 | Gate 确认与审计字段 |
| `upstream/tests/commands/test_ci.py` | 23 | 单元 | CI 集成 |
| `upstream/tests/commands/test_guard.py` | 20 | 单元 | 项目级门禁 |
| `upstream/tests/test_migrate_to_d_drive.py` | 19 | 集成 | 路径迁移与工作区洁净度 |
| `upstream/tests/test_canonical_in_workspace.py` | 17 | 集成 | 工作区 canonical 双轨 |
| `upstream/tests/commands/test_phase.py` | 17 | 单元 | 阶段推进与 `record-slice` |
| `upstream/tests/commands/test_canon.py` | 9 | 单元 | `canon generate/verify` |
| `upstream/tests/commands/test_structure.py` | 9 | 单元 | 代码结构索引 |
| `upstream/tests/commands/test_validate.py` | 8 | 单元 | change 结构校验 |
| 其余 35 个测试文件 | — | — | 见 `upstream/tests/` |
| **合计（51 个文件）** | **641 收集 / 640 passed / 1 skipped** | — | 本 change 的回归基线 |

**校验脚本（非 pytest，需单独运行）**

| 脚本 | 用途 | 当前状态 |
|---|---|---|
| `tools/verify_eol.py` | 行尾治理（`git ls-files --eol` 判 `i/lf w/crlf`） | 7/7 |
| `tools/verify_skill_standards.py` | skill 元数据标准 | 6/7（TC-SES-004 既存问题，与本 change 无关） |
| `tools/verify_workbuddy_skills.py` | WorkBuddy skill 加载位置校验 | 全 PASS |
| `tools/verify_rename.py` | 改名重构校验 | 8/8 |

## 二、详细测试案例

### 功能 1：时间基线契约（`time-baseline`）

对应 `time-baseline.yaml` → REQ-001..REQ-004

#### 案例 1.1 — 基线四项非空

| 字段 | 内容 |
|------|------|
| **ID** | TC-TB-001 |
| **对应 Spec** | `time-baseline/spec.md` → Scenario: SC-001 |
| **优先级** | P0 |
| **预置条件** | 临时仓库中已 `fstdd new` 一个 change，并已通过 Gate 1 |
| **输入** | 读取 `.fstdd/changes/<change>/.fstdd.yaml` |
| **预期结果** | 存在 `baseline` 块；`at` / `base_git_sha` / `node_id` / `clock_source` 四项非空；`at` 匹配 `([+-]\d{2}:\d{2}|Z)$` |
| **当前状态** | ❌ 测试缺（计划：`tests/commands/test_baseline.py`） |

#### 案例 1.2 — 基线建立幂等

| 字段 | 内容 |
|------|------|
| **ID** | TC-TB-002 |
| **对应 Spec** | `time-baseline/spec.md` → Scenario: SC-002 |
| **优先级** | P0 |
| **预置条件** | 基线已建立且四项非空 |
| **输入** | 再次执行 `fstdd baseline establish <change>`（不带 `--force`） |
| **预期结果** | 四项取值不变；退出码 0；输出含「已存在，未改写」 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.3 — 基线可被结构化读出

| 字段 | 内容 |
|------|------|
| **ID** | TC-TB-003 |
| **对应 Spec** | `time-baseline/spec.md` → Scenario: SC-003 |
| **优先级** | P0 |
| **预置条件** | 基线已建立 |
| **输入** | `fstdd baseline show <change> --format json` |
| **预期结果** | 输出可被 `json.loads` 解析；含 `base_git_sha`；四项均出现 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.4 — `base_git_sha` 与建立时 HEAD 一致

| 字段 | 内容 |
|------|------|
| **ID** | TC-TB-004 |
| **对应 Spec** | `time-baseline/spec.md` → Scenario: SC-004 |
| **优先级** | P0 |
| **预置条件** | 临时仓库 HEAD 为已知 `<sha>` |
| **输入** | 建立基线后读取 `base_git_sha` |
| **预期结果** | 等于 `git rev-parse HEAD`；短 sha 为完整 sha 的前缀 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.5 — 基线锚点可被 `git log` 定位

| 字段 | 内容 |
|------|------|
| **ID** | TC-TB-005 |
| **对应 Spec** | `time-baseline/spec.md` → Scenario: SC-005 |
| **优先级** | P1 |
| **预置条件** | 基线已建立 |
| **输入** | `git log -1 --format=%H <base_git_sha>` |
| **预期结果** | 返回非空且为 40 位 sha；该提交是建立时 HEAD 的祖先或自身 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.6 — 回填取 Gate 1 `confirmed_at`（不得取回填时刻）

| 字段 | 内容 |
|------|------|
| **ID** | TC-TB-006 |
| **对应 Spec** | `time-baseline/spec.md` → Scenario: SC-006 |
| **优先级** | P0 |
| **预置条件** | change 的 `phases.understand.confirmed_at` 为已知值且无 `baseline` 块 |
| **输入** | 执行回填 |
| **预期结果** | `baseline.at` 等于 `confirmed_at`（同一时刻的等价表示）；**不等于**回填动作发生时刻；重复回填结果不变 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.7 — `established_by` / `clock_source` 来源可辨

| 字段 | 内容 |
|------|------|
| **ID** | TC-TB-007 |
| **对应 Spec** | `time-baseline/spec.md` → Scenario: SC-007 |
| **优先级** | P1 |
| **预置条件** | 分别经 Gate 1 与回填两种途径建立基线 |
| **输入** | 读取 `established_by` 与 `clock_source` |
| **预期结果** | `established_by` ∈ {`gate1`,`cli`,`backfill`} 且两种途径取值不同；`clock_source` ∈ {`system`,`hub`,`manual`} |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.8 — 缺基线时 `validate` 仅告警不阻断

| 字段 | 内容 |
|------|------|
| **ID** | TC-TB-008 |
| **对应 Spec** | `time-baseline.spec.md` → Scenario: SC-008 |
| **优先级** | P0 |
| **预置条件** | 一个缺 `baseline` 块的 change |
| **输入** | `fstdd validate <change>` |
| **预期结果** | 输出报告基线缺失/不完整；**退出码与基线完整时相同**（warning 级，不使校验失败） |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.9 — `baseline show --check` 退出码可区分

| 字段 | 内容 |
|------|------|
| **ID** | TC-TB-009 |
| **对应 Spec** | `time-baseline/spec.md` → Scenario: SC-009 |
| **优先级** | P0 |
| **预置条件** | 两个 change：一个基线完整、一个缺一项 |
| **输入** | 分别执行 `fstdd baseline show <change> --check` |
| **预期结果** | 完整 → 退出码 0；不完整 → 退出码非 0；输出无需人工解读即可判定 |
| **当前状态** | ❌ 测试缺 |

---

### 功能 2：统一时间戳规范（`timestamp-normalization`）

对应 `timestamp-normalization.yaml` → REQ-005..REQ-007

#### 案例 2.1 — CLI 新产出时间戳带时区

| 字段 | 内容 |
|------|------|
| **ID** | TC-TSN-001 |
| **对应 Spec** | `timestamp-normalization/spec.md` → Scenario: SC-010 |
| **优先级** | P0 |
| **预置条件** | 改造后的 CLI；临时仓库 |
| **输入** | 依次执行 `fstdd new` / `canon generate` / `gate approve`，读取各产物时间字段 |
| **预期结果** | 每个时间字段匹配 `([+-]\d{2}:\d{2}|Z)$`；无 naive 形态；值由单一来源函数产生（同一模块内只有一处时间获取实现） |
| **当前状态** | ❌ 测试缺（现状：`canon.py:144/300`、`gate.py:95/203`、`phase.py:96/170/175/194` 等仍为 naive） |

#### 案例 2.2 — CLI 与控制面时间可直接比较

| 字段 | 内容 |
|------|------|
| **ID** | TC-TSN-002 |
| **对应 Spec** | `timestamp-normalization/spec.md` → Scenario: SC-011 |
| **优先级** | P0 |
| **预置条件** | 控制面 `utc_now()`（`tools/fstdd_hub.py:99`）与 CLI 时间来源函数均可用 |
| **输入** | 分别取两者输出，做字符串比较与排序 |
| **预期结果** | 排序结果与真实时间先后一致；两者时区表示一致；无需解析换算 |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.3 — 日期字段不得含时刻

| 字段 | 内容 |
|------|------|
| **ID** | TC-TSN-003 |
| **对应 Spec** | `timestamp-normalization/spec.md` → Scenario: SC-012 |
| **优先级** | P1 |
| **预置条件** | 产物中含 `YYYY-MM-DD` 形式的日期字段 |
| **输入** | 运行时间戳规范检测 |
| **预期结果** | 纯日期字段通过；含时刻却无时区的形态被判定违规；`batch_id` 等标识符中的日期片段不被判定为时间戳字段 |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.4 — 检测器报出 naive 字段（值层）

| 字段 | 内容 |
|------|------|
| **ID** | TC-TSN-004 |
| **对应 Spec** | `timestamp-normalization/spec.md` → Scenario: SC-013 |
| **优先级** | P0 |
| **预置条件** | 临时仓库中植入一个 naive 时间戳字段值 |
| **输入** | 运行检测 |
| **预期结果** | 报出该字段及位置；判定基于**字段值**而非源码中是否出现某调用；输出含被检查字段总数（使「0 个违规」可被信任） |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.5 — 4 类豁免不误报

| 字段 | 内容 |
|------|------|
| **ID** | TC-TSN-005 |
| **对应 Spec** | `timestamp-normalization/spec.md` → Scenario: SC-014 |
| **优先级** | P0 |
| **预置条件** | 源码含 4 类非时间戳用途：单调钟（`experience.py:193-212`）、标识符/目录名（`batch.py:77-93`）、纯时间差计算（`status.py:106`）、渲染参数（`ci.py:131/158`） |
| **输入** | 运行检测 |
| **预期结果** | 4 类均**不**被报为违规；豁免以配置数据维护；每条附理由 |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.6 — 豁免清单自检

| 字段 | 内容 |
|------|------|
| **ID** | TC-TSN-006 |
| **对应 Spec** | `timestamp-normalization/spec.md` → Scenario: SC-015 |
| **优先级** | P1 |
| **预置条件** | 豁免清单已登记条目 |
| **输入** | 运行豁免清单自检；再人为植入一条无法定位的豁免 |
| **预期结果** | 正常清单全部可定位；植入的无效条目被报出 |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.7 — 全仓扫描 0 个 naive 时间戳

| 字段 | 内容 |
|------|------|
| **ID** | TC-TSN-007 |
| **对应 Spec** | `timestamp-normalization/spec.md` → Scenario: SC-016 |
| **优先级** | P0 |
| **预置条件** | 全部改动已落地 |
| **输入** | 执行全仓扫描（活跃 change 的 `.fstdd.yaml` / canonical YAML / Human View 头部 + 两处 templates） |
| **预期结果** | naive 计数为 0；扫描范围在输出中显式列出；只读（扫描前后文件哈希不变） |
| **当前状态** | ❌ 测试缺 |

---

### 功能 3：证据时效标注（`evidence-provenance`）

对应 `evidence-provenance.yaml` → REQ-008..REQ-009

#### 案例 3.1 — `why.evidence` 含观测时刻与 sha

| 字段 | 内容 |
|------|------|
| **ID** | TC-EPR-001 |
| **对应 Spec** | `evidence-provenance/spec.md` → Scenario: SC-017 |
| **优先级** | P0 |
| **预置条件** | canonical proposal 的 `why.evidence` 已填写 |
| **输入** | 检查该证据块 |
| **预期结果** | 含 `observed_at`（带时区）与 `observed_base_git_sha`，两者非空 |
| **当前状态** | ❌ 测试缺（现状：`why.evidence` 只写「只读巡检实测」，无观测时刻） |

#### 案例 3.2 — spec 与 test-report 的证据条目同样携带观测时刻

| 字段 | 内容 |
|------|------|
| **ID** | TC-EPR-002 |
| **对应 Spec** | `evidence-provenance/spec.md` → Scenario: SC-018 |
| **优先级** | P1 |
| **预置条件** | canonical spec 的 scenario `evidence` 与 test-report 证据条目已填写 |
| **输入** | 检查两处 |
| **预期结果** | 引用实测数据的 evidence 能定位到观测时刻；test-report 证据条目含 `observed_at` |
| **当前状态** | ❌ 测试缺 |

#### 案例 3.3 — 模板含观测时刻字段与示例

| 字段 | 内容 |
|------|------|
| **ID** | TC-EPR-003 |
| **对应 Spec** | `evidence-provenance/spec.md` → Scenario: SC-019 |
| **优先级** | P0 |
| **预置条件** | 两处模板已更新 |
| **输入** | 检查 proposal 模板与 spec 模板的证据字段 |
| **预期结果** | 含观测时刻与代码版本字段；含填写示例（非仅字段名）；两处模板一致 |
| **当前状态** | ❌ 测试缺 |

#### 案例 3.4 — 证据时效三态可判定

| 字段 | 内容 |
|------|------|
| **ID** | TC-EPR-004 |
| **对应 Spec** | `evidence-provenance/spec.md` → Scenario: SC-020 |
| **优先级** | P0 |
| **预置条件** | 一条证据带 `observed_at`，所属 change 有 `baseline.at` |
| **输入** | 执行时效判定 |
| **预期结果** | 能判定「在基线之后观测」或「早于基线」；结果可被程序读取；早于基线时明确标识 |
| **当前状态** | ❌ 测试缺 |

#### 案例 3.5 — 缺观测时刻时不得当作「未过期」

| 字段 | 内容 |
|------|------|
| **ID** | TC-EPR-005 |
| **对应 Spec** | `evidence-provenance/spec.md` → Scenario: SC-021 |
| **优先级** | P0 |
| **预置条件** | 证据缺少 `observed_at` |
| **输入** | 执行时效判定 |
| **预期结果** | 报告「无法判定时效」；**不**当作「未过期」；三态（未过期 / 早于基线 / 无法判定）可区分 |
| **当前状态** | ❌ 测试缺 |

---

### 功能 4：时钟对齐巡检（`clock-alignment`）

对应 `clock-alignment.yaml` → REQ-010..REQ-012

#### 案例 4.1 — 输出含 offset / rtt / err / jitter / 样本数

| 字段 | 内容 |
|------|------|
| **ID** | TC-CAL-001 |
| **对应 Spec** | `clock-alignment/spec.md` → Scenario: SC-022 |
| **优先级** | P0 |
| **预置条件** | 节点清单已配置；至少一个可达节点 |
| **输入** | `fstdd baseline check --format json` |
| **预期结果** | 每节点含 `offset` / `rtt` / `err` / `jitter` / 采样次数 / 有效样本数；JSON 可解析 |
| **当前状态** | ❌ 测试缺 |

#### 案例 4.2 — 采用最小 RTT 样本而非平均

| 字段 | 内容 |
|------|------|
| **ID** | TC-CAL-002 |
| **对应 Spec** | `clock-alignment/spec.md` → Scenario: SC-023 |
| **优先级** | P0 |
| **预置条件** | 注入构造的多次采样（RTT 差异显著、offset 各异） |
| **输入** | 计算最终偏移估计 |
| **预期结果** | 等于最小 RTT 那次样本的 offset；**不等于**算术平均；所选样本的 RTT 出现在输出中 |
| **当前状态** | ❌ 测试缺 |

#### 案例 4.3 — 可接受态 → 退出码 0

| 字段 | 内容 |
|------|------|
| **ID** | TC-CAL-003 |
| **对应 Spec** | `clock-alignment/spec.md` → Scenario: SC-024 |
| **优先级** | P0 |
| **预置条件** | 注入：抖动在阈值内、`abs(offset) <= TOLERANCE`、`err <= TOLERANCE` |
| **输入** | 执行巡检 |
| **预期结果** | 判定「可接受」；退出码 0 |
| **当前状态** | ❌ 测试缺 |

#### 案例 4.4 — 超限态 → 退出码 1

| 字段 | 内容 |
|------|------|
| **ID** | TC-CAL-004 |
| **对应 Spec** | `clock-alignment/spec.md` → Scenario: SC-025 |
| **优先级** | P0 |
| **预置条件** | 注入：抖动在阈值内、`err <= TOLERANCE`，但 `abs(offset) > TOLERANCE` |
| **输入** | 执行巡检 |
| **预期结果** | 判定「超限」；退出码 1；与「无法测量」的退出码不同 |
| **当前状态** | ❌ 测试缺 |

#### 案例 4.5 — 无法测量态 → 退出码 2

| 字段 | 内容 |
|------|------|
| **ID** | TC-CAL-005 |
| **对应 Spec** | `clock-alignment/spec.md` → Scenario: SC-026 |
| **优先级** | P0 |
| **预置条件** | 4 个注入场景各一：节点不可达 / 有效样本 < 3 / `jitter > JITTER_MAX` / `err > TOLERANCE` |
| **输入** | 分别执行巡检 |
| **预期结果** | 四种场景均判定「无法测量」；退出码 2；**不**报「可接受」；**不**报「超限」 |
| **当前状态** | ❌ 测试缺 |

#### 案例 4.6 — 误差上界超容差时不得报「可接受」

| 字段 | 内容 |
|------|------|
| **ID** | TC-CAL-006 |
| **对应 Spec** | `clock-alignment/spec.md` → Scenario: SC-027 |
| **优先级** | P0 |
| **预置条件** | 注入：`err > TOLERANCE` 但 `abs(offset) < TOLERANCE`（本 change 的真实情形：`err ≈ 2.7s`，`TOLERANCE = 2.0s`） |
| **输入** | 执行巡检 |
| **预期结果** | 判定**不是**「可接受」，而是「无法测量」；输出说明具体原因（不可达 / 样本不足 / 抖动 / 误差上界） |
| **当前状态** | ❌ 测试缺（**本 change 的真实实测预期就是此态**） |

#### 案例 4.7 — 巡检只读且幂等

| 字段 | 内容 |
|------|------|
| **ID** | TC-CAL-007 |
| **对应 Spec** | `clock-alignment/spec.md` → Scenario: SC-028 |
| **优先级** | P0 |
| **预置条件** | 可观测的节点状态（远端文件清单 + 本机文件哈希） |
| **输入** | 执行巡检一次、再执行一次 |
| **预期结果** | 执行前后各节点状态不变；远端无文件写入；本机被观测状态不变；两次结果结构相同 |
| **当前状态** | ❌ 测试缺 |

#### 案例 4.8 — 单点不可达不中止、不挂起

| 字段 | 内容 |
|------|------|
| **ID** | TC-CAL-008 |
| **对应 Spec** | `clock-alignment/spec.md` → Scenario: SC-029 |
| **优先级** | P0 |
| **预置条件** | 节点清单含 1 个不可达节点 + 1 个可达节点 |
| **输入** | 执行巡检（带超时约束） |
| **预期结果** | 可达节点仍完成巡检；不可达节点标记「无法测量」；命令不崩溃、不无限挂起；汇总列出未测节点 |
| **当前状态** | ❌ 测试缺 |

#### 案例 4.9 — 采样计数基于有效读数条数

| 字段 | 内容 |
|------|------|
| **ID** | TC-CAL-009 |
| **对应 Spec** | `clock-alignment/spec.md` → Scenario: SC-030 |
| **优先级** | P1 |
| **预置条件** | 桩：一次调用返回 2 条远端读数（模拟本机「命令执行两次」特性） |
| **输入** | 统计有效样本数并计算偏移 |
| **预期结果** | 计数等于收到的有效读数条数（非调用次数）；重复读数不产生系统性偏差 |
| **当前状态** | ❌ 测试缺 |

---

### 功能 5：宪法条款（`constitution`）

对应 `constitution.yaml` → REQ-013..REQ-015

#### 案例 5.1 — 宪法含编号连续的时间基线条款

| 字段 | 内容 |
|------|------|
| **ID** | TC-CONST-001 |
| **对应 Spec** | `constitution/spec.md` → Scenario: SC-031 |
| **优先级** | P0 |
| **预置条件** | 宪法已更新 |
| **输入** | 检索宪法中的时间基线条款 |
| **预期结果** | 存在 `### 7. 时间基线`（编号与既有 1–6 连续）；规定须建立基线、证据须带观测时刻；明确违规后果 |
| **当前状态** | ❌ 测试缺（现状：九个时间相关词零命中） |

#### 案例 5.2 — 至少 1 处 Gate 检查引用基线

| 字段 | 内容 |
|------|------|
| **ID** | TC-CONST-002 |
| **对应 Spec** | `constitution/spec.md` → Scenario: SC-032 |
| **优先级** | P0 |
| **预置条件** | 条款与检查项均已落地 |
| **输入** | 触发被引用的检查项（`fstdd validate` + skill Gate 前自检清单） |
| **预期结果** | 至少 1 处实际执行了基线检查（可被测试触发并观察到结果）；**不是**仅文字提及 |
| **当前状态** | ❌ 测试缺 |

#### 案例 5.3 — 宪法两份逐字节一致

| 字段 | 内容 |
|------|------|
| **ID** | TC-CONST-003 |
| **对应 Spec** | `constitution/spec.md` → Scenario: SC-033 |
| **优先级** | P0 |
| **预置条件** | 条款已写入两份 |
| **输入** | 比较 `FSTDD_CONSTITUTION.md` 与 `.fstdd/memory/FSTDD_CONSTITUTION.md` |
| **预期结果** | 逐字节一致；有测试断言覆盖；未出现只更新一份的情况 |
| **当前状态** | ❌ 测试缺 |

#### 案例 5.4 — 条款中的每项「必须」都有可执行检查

| 字段 | 内容 |
|------|------|
| **ID** | TC-CONST-004 |
| **对应 Spec** | `constitution/spec.md` → Scenario: SC-034 |
| **优先级** | P0 |
| **预置条件** | 条款已定稿 |
| **输入** | 逐条核对条款中的「必须」项与实现 |
| **预期结果** | 每项有对应且已实现的检查；无法实现的项已移除或降级；核对结果记入 test-report |
| **当前状态** | ❌ 测试缺 |

#### 案例 5.5 — 宪法与 skill 流程描述一致

| 字段 | 内容 |
|------|------|
| **ID** | TC-CONST-005 |
| **对应 Spec** | `constitution/spec.md` → Scenario: SC-035 |
| **优先级** | P1 |
| **预置条件** | 宪法条款与 skill 均已更新 |
| **输入** | 检查 `fstdd-spec` / `fstdd-build` 的 Gate 前自检清单 |
| **预期结果** | 清单与宪法条款一致；无「宪法要求、skill 未提」或反向冲突的组合 |
| **当前状态** | ❌ 测试缺 |

---

### 功能 6：产物模板与 CLI（`artifact-templates`）

对应 `artifact-templates.yaml` → REQ-016..REQ-018

#### 案例 6.1 — 两处模板内容一致

| 字段 | 内容 |
|------|------|
| **ID** | TC-TMPL-001 |
| **对应 Spec** | `artifact-templates/spec.md` → Scenario: SC-036 |
| **优先级** | P0 |
| **预置条件** | 7 个相关模板均已更新 |
| **输入** | 逐文件比较 `upstream/.fstdd/templates/**` 与 `.fstdd/templates/**` |
| **预期结果** | 两处内容一致；有测试断言覆盖；未出现只更新一处 |
| **当前状态** | ❌ 测试缺 |

#### 案例 6.2 — 新 change 默认携带基线字段

| 字段 | 内容 |
|------|------|
| **ID** | TC-TMPL-002 |
| **对应 Spec** | `artifact-templates/spec.md` → Scenario: SC-037 |
| **优先级** | P0 |
| **预置条件** | 模板已更新 |
| **输入** | `fstdd new` 创建新 change，检查模板产物 |
| **预期结果** | 产物含基线字段与观测时刻字段占位；含填写示例或注释；既有解析不失败 |
| **当前状态** | ❌ 测试缺 |

#### 案例 6.3 — CLI 命令五处注册齐全

| 字段 | 内容 |
|------|------|
| **ID** | TC-TMPL-003 |
| **对应 Spec** | `artifact-templates/spec.md` → Scenario: SC-038 |
| **优先级** | P0 |
| **预置条件** | `baseline` 命令已实现 |
| **输入** | 检查 `upstream/fstdd/cli/__init__.py` 与命令模块 |
| **预期结果** | 五处同时到位：`COMMAND_GROUPS` / `_CMD_HELP` / `subparsers.add_parser` / 命令分发表 / 命令模块文件；分发表路径可导入 |
| **当前状态** | ❌ 测试缺 |

#### 案例 6.4 — 命令可被真实执行（禁止 grep 判据）

| 字段 | 内容 |
|------|------|
| **ID** | TC-TMPL-004 |
| **对应 Spec** | `artifact-templates/spec.md` → Scenario: SC-039 |
| **优先级** | P0 |
| **预置条件** | 命令已注册 |
| **输入** | 子进程执行 `fstdd baseline --help`；再真实调用 `establish` / `show` / `check` 各一次 |
| **预期结果** | `--help` 被识别并输出帮助；三个动作各返回预期结果；验收**不**以「源码中出现某字符串」为判据 |
| **当前状态** | ❌ 测试缺 |

#### 案例 6.5 — 另一节点可直接执行

| 字段 | 内容 |
|------|------|
| **ID** | TC-TMPL-005 |
| **对应 Spec** | `artifact-templates/spec.md` → Scenario: SC-040 |
| **优先级** | P0 |
| **预置条件** | 干净克隆（模拟另一节点） |
| **输入** | 直接执行新增命令 |
| **预期结果** | 无需额外安装步骤即可执行；依赖限于标准库与 PyYAML；缺配置时给出明确提示而非静默失败 |
| **当前状态** | ❌ 测试缺 |

#### 案例 6.6 — 节点与阈值可配置

| 字段 | 内容 |
|------|------|
| **ID** | TC-TMPL-006 |
| **对应 Spec** | `artifact-templates/spec.md` → Scenario: SC-041 |
| **优先级** | P1 |
| **预置条件** | `.fstdd/config.d/nodes.yaml` 与 `.fstdd/config.d/baseline.yaml` 存在 |
| **输入** | 修改节点清单与阈值，重跑命令 |
| **预期结果** | 行为随之改变，无需改代码；配置缺失时使用有文档的默认值或给出明确提示 |
| **当前状态** | ❌ 测试缺 |

---

### 功能 7：canon 双轨校验（`canon-dual-track`）

对应 `canon-dual-track.yaml` → REQ-019..REQ-021

#### 案例 7.1 — 归一函数与 `verify_eol.py` 同口径

| 字段 | 内容 |
|------|------|
| **ID** | TC-CANON-001 |
| **对应 Spec** | `canon-dual-track/spec.md` → Scenario: SC-042 |
| **优先级** | P0 |
| **预置条件** | 同一份 YAML 的 CRLF 与 LF 两种表示 |
| **输入** | 分别计算 DC-HASH |
| **预期结果** | 两个哈希相同；归一函数与 `tools/verify_eol.py` 的 `normalize()` 同口径；归一不改变 YAML 语义 |
| **当前状态** | ❌ 测试缺 |

#### 案例 7.2 — CRLF 工作区生成 → LF 工作区校验通过

| 字段 | 内容 |
|------|------|
| **ID** | TC-CANON-002 |
| **对应 Spec** | `canon-dual-track/spec.md` → Scenario: SC-043 |
| **优先级** | P0 |
| **预置条件** | 在 CRLF 工作区写入 canonical YAML 并记录 DC-HASH |
| **输入** | 在 LF 工作区执行 `canon verify` |
| **预期结果** | 校验通过；不报告 DC-HASH 失配；不依赖工作区行尾状态 |
| **当前状态** | ❌ 测试缺 |

#### 案例 7.3 — 干净克隆 `canon verify` 2/2

| 字段 | 内容 |
|------|------|
| **ID** | TC-CANON-003 |
| **对应 Spec** | `canon-dual-track/spec.md` → Scenario: SC-044 |
| **优先级** | P0 |
| **预置条件** | 一个干净克隆（全部文件 LF），非生成机器 |
| **输入** | 执行 `canon verify` |
| **预期结果** | 2/2 通过（DC-HASH 源哈希一致 + DC-FIELD 字段引用完整）；无需先执行任何归一命令 |
| **当前状态** | ❌ 测试缺（现状：归档 change 实测「记录 `87af3c03…`，LF blob 实为 `c041bff1…`」→ 必红） |

#### 案例 7.4 — 一次性重生成只改 `source_hash` 一行

| 字段 | 内容 |
|------|------|
| **ID** | TC-CANON-004 |
| **对应 Spec** | `canon-dual-track/spec.md` → Scenario: SC-045 |
| **优先级** | P0 |
| **预置条件** | 存量活跃 change 的 Human View 记录旧算法哈希 |
| **输入** | 执行一次性重生成 |
| **预期结果** | 仅 `source_hash` 一行变化（正文零改动）；重生成后 `canon verify` 通过；归档 change 未被回溯修改 |
| **当前状态** | ❌ 测试缺 |

#### 案例 7.5 — 校验不得退化为恒真（负向验证）

| 字段 | 内容 |
|------|------|
| **ID** | TC-CANON-005 |
| **对应 Spec** | `canon-dual-track/spec.md` → Scenario: SC-046 |
| **优先级** | P0 |
| **预置条件** | 修改 canonical YAML 但不重新生成 Human View |
| **输入** | 执行 `canon verify` |
| **预期结果** | 报告 DC-HASH 失配；以非 0 退出码结束；有对应测试覆盖（含变异测试） |
| **当前状态** | ❌ 测试缺 |

#### 案例 7.6 — 归一函数变异测试

| 字段 | 内容 |
|------|------|
| **ID** | TC-CANON-006 |
| **对应 Spec** | `canon-dual-track/spec.md` → Scenario: SC-047 |
| **优先级** | P0 |
| **预置条件** | 纯内存注入缺陷：归一函数只处理 `\r\n` 而忽略孤立 `\r` |
| **输入** | 运行归一相关测试 |
| **预期结果** | 至少 1 个测试失败（证明断言有效）；注入无文件残留；恢复后复验通过 |
| **当前状态** | ❌ 测试缺 |

---

### 功能 8：跨切面与回归（`cross-cutting`）

#### 案例 8.1 — 全量工程测试套件保持绿

| 字段 | 内容 |
|------|------|
| **ID** | TC-XCUT-001 |
| **对应 Spec** | proposal `success_criteria` 第 7 条 |
| **优先级** | P0 |
| **预置条件** | 全部改动已落地 |
| **输入** | `cd upstream && C:/Python311/python.exe -m pytest tests -q` |
| **预期结果** | 无 failed；收集数 ≥ 641；无回归 |
| **当前状态** | ❌ 待执行（基线：641 收集 / 640 passed / 1 skipped） |

#### 案例 8.2 — 仓库无凭证

| 字段 | 内容 |
|------|------|
| **ID** | TC-XCUT-002 |
| **对应 Spec** | proposal `success_criteria` 第 8 条 |
| **优先级** | P0 |
| **预置条件** | 改动已提交 |
| **输入** | 以既有凭证扫描规则检查（`ghp_` / `github_pat_` / `sk-` / `AKIA` / 私钥头） |
| **预期结果** | 命中数为 0 |
| **当前状态** | ❌ 待执行 |

#### 案例 8.3 — 行尾治理校验通过

| 字段 | 内容 |
|------|------|
| **ID** | TC-XCUT-003 |
| **对应 Spec** | 项目约定（`verify_eol.py`） |
| **优先级** | P0 |
| **预置条件** | change 目录与改动文件已归一为 LF |
| **输入** | `tools/verify_eol.py` |
| **预期结果** | 全部通过（基线 7/7）；无 `i/lf w/crlf` 混合态 |
| **当前状态** | ❌ 待执行 |

#### 案例 8.4 — 新增测试数 > 0

| 字段 | 内容 |
|------|------|
| **ID** | TC-XCUT-004 |
| **对应 Spec** | 长程模式强制约束（「每个切片必须有新增测试」） |
| **优先级** | P0 |
| **预置条件** | BUILD 阶段完成 |
| **输入** | 统计新增 `def test_` 数量 |
| **预期结果** | > 0，且 ≥ 52（本 test-plan 的 TC 总数） |
| **当前状态** | ❌ 待执行 |

#### 案例 8.5 — skill 标准校验

| 字段 | 内容 |
|------|------|
| **ID** | TC-XCUT-005 |
| **对应 Spec** | 项目约定（`verify_skill_standards.py`） |
| **优先级** | P1 |
| **预置条件** | skill 已更新 |
| **输入** | `tools/verify_skill_standards.py` |
| **预期结果** | 不劣于基线（6/7；TC-SES-004 为既存问题，与本 change 无关） |
| **当前状态** | ❌ 待执行 |

## 三、测试执行矩阵

| 功能模块 | 单元测试 | 集成测试 | E2E | 状态 |
|----------|---------|----------|-----|------|
| 时间基线契约（TB-001..009） | ✅ 幂等/字段校验 | ✅ CLI 三动作 + 临时仓库 | — | 🟡 待实现 |
| 时间戳规范（TSN-001..007） | ✅ 正则/豁免清单 | ✅ 全仓扫描 | — | 🟡 待实现 |
| 证据时效（EPR-001..005） | ✅ 时效判定三态 | ✅ 模板字段 | — | 🟡 待实现 |
| 时钟巡检（CAL-001..009） | ✅ 三态判定/最小 RTT | ✅ 桩化采样 + 真实 ssh | ✅ 真实节点巡检 | 🟡 待实现 |
| 宪法条款（CONST-001..005） | ✅ 条款存在性 | ✅ 两份一致 + 检查项触发 | — | 🟡 待实现 |
| 模板与 CLI（TMPL-001..006） | ✅ 五处注册 | ✅ 两处模板一致 + 真实执行 | ✅ 干净克隆执行 | 🟡 待实现 |
| canon 双轨（CANON-001..006） | ✅ 归一/变异 | ✅ verify 正负向 | ✅ 干净克隆 2/2 | 🟡 待实现 |
| 跨切面（XCUT-001..005） | — | ✅ 全量套件 | ✅ EOL/凭证/skill | 🟡 待执行 |

## 四、回归风险矩阵

| 风险区域 | 本 change 改动 | 已有回归保护 | 风险等级 |
|----------|-------------|-------------|---------|
| `canon verify` 双轨校验 | DC-HASH 改用归一后内容哈希 | `tests/commands/test_canon.py`（9）+ `test_canonical_in_workspace.py`（17） | 🔴 高 |
| CLI 命令分发表 | 新增 `baseline` 命令（五处注册） | `tests/test_fstdd_matrix.py`（40）+ `test_patch1_coverage.py`（11） | 🔴 高 |
| 时间戳产出点（~25 处 / 15 文件） | naive → 带时区 UTC | `test_gate.py`（23）+ `test_phase.py`（17）+ `test_experience*.py`（50） | 🟡 中 |
| Gate 审计字段 | Gate 1 同事务写 `baseline` 块 | `tests/commands/test_gate.py`（23） | 🟡 中 |
| `fstdd validate` | 新增基线检查（warning 级） | `tests/commands/test_validate.py`（8）+ `test_fstdd_matrix.py`（40） | 🟡 中 |
| 模板双源 | 7 个模板 × 2 处 | `test_install_source.py`（14）+ `test_constitution_contract.py`（6） | 🟡 中 |
| 宪法两份 | 新增 `### 7.` 条款 | `test_constitution_migration.py`（10）+ `test_constitution_contract.py`（6） | 🟢 低 |
| 归档 change | 不回溯（明确排除） | `test_migrate_to_d_drive.py`（19） | 🟢 低 |
| 行尾治理 | 新增文件须为 LF | `tools/verify_eol.py`（7/7） | 🟢 低 |
| 经验回传 / 端点 | 无改动 | `test_inbox_endpoint.py`（44）+ `test_inbox_pull.py`（23） | 🟢 低 |

## 五、建议补充顺序

### 1. 第一优先（部署前必补，P0）

**核心契约与最高风险项，必须先写失败测试再实现：**

- `TC-CANON-001..006`（DC-HASH 归一与干净克隆，🔴 高风险的根因）
- `TC-TMPL-003..005`（CLI 五处注册与真实执行，🔴 高风险 + EXP-B1）
- `TC-CAL-003..008`（三态判定，本 change 的核心价值）
- `TC-TB-001..004`、`TC-TB-006`、`TC-TB-008..009`（基线契约与 Gate 引用）
- `TC-TSN-001`、`TC-TSN-004..005`、`TC-TSN-007`（时间戳规范与检测器防误报）
- `TC-EPR-001`、`TC-EPR-004..005`（证据时效）
- `TC-CONST-001..004`（宪法条款与一致性）
- `TC-TMPL-001..002`（模板双源）
- `TC-XCUT-001..004`（全量回归、凭证、EOL、新增测试数）

### 2. 第二优先（部署后尽快补，P1）

- `TC-CAL-009`（采样计数与"执行两次"特性）
- `TC-TSN-003`、`TC-TSN-006`（日期字段、豁免清单自检）
- `TC-TB-005`、`TC-TB-007`（锚点可定位、来源可辨）
- `TC-EPR-002..003`（spec/test-report 证据、模板示例）
- `TC-CONST-005`（宪法与 skill 一致）
- `TC-TMPL-006`（配置化）
- `TC-XCUT-005`（skill 标准）

### 3. 第三优先（后续补，P2）

- 巡检命令在真实三节点环境上的端到端验证（依赖另 2 台机器可达，当前不可达）
- 跨机时间排序的端到端验证（需 ≥2 个节点同时产出带时区时间戳）
- 时间基线的长期漂移观测（需时间积累，非本 change 可完成）
