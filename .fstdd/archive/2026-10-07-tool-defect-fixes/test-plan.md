# 3.3.6+ 测试方案与详细案例 — 工具链契约保真（6 个既有缺陷修复）

> 版本：3.3.6（R 轴；本 change 不改版本号，升版在 DELIVER 按 semver 复核）
> 创建日期：2026-10-07
> 对应 Phase 2 Spec：`canonical/specs/code/dry-run-fidelity.yaml`、
> `experience-io-contract.yaml`、`proposal-extraction-fidelity.yaml`、
> `ci-check-accuracy.yaml`、`quarantine-opt-in-safety.yaml`；
> `canonical/specs/agent/2026-10-07-tool-defect-fixes.yaml`
> 观测基线：`observed_at=2026-10-06T17:25:33+00:00`、`observed_base_git_sha=0710d5462f973164f83f5096cdf739380e579fb8`

## 一、测试策略

### 1.1 测试金字塔

本 change 修的是**工具契约**，测试重心落在**CLI 实跑 + 正反双向样本**，而非传统单元测试：

- **CLI 实跑与字节级比对（≈45%）**：每个缺陷都以「真跑一次命令 + 比对落盘字节 / 退出码 / stdout」验证，
  不用「读代码觉得对了」代替（EXP-2026-0021：审计工具的漏检 = 假绿）。
- **正 / 反双向样本（≈30%）**：凡「放宽判据」类修复（SC-011/012、SC-003、SC-007），
  必须同时证明「违例能抓到」与「合法不误报」。只做单向 = 用不可信的工具去证明另一个可信。
- **既有测试面回归（≈20%）**：`test_ci` / `test_phase` / `test_experience` /
  `test_experience_v29` / `tools/test_verify_notices` 全量复跑，零回归是硬约束。
- **E2E（≈5%）**：全量 `pytest upstream/tests` + 根 `tests/` + 四自检脚本。

### 1.2 测试原则

1. **断言可逆、不删测**：只做修正，不删除任何既有用例。
2. **不抽检、要全量**：枚举类断言（6 个缺陷、5 个 `json.dumps` 调用点、41 份 test-plan）用**集合相等**，
   不用「非空 / 抽检几个」（KG-094：断言只覆盖少数几个字段 ⇒ 测试全绿而缺陷仍在）。
3. **审计器自带自检**：每个扫描 / 审计类测试必须含一条「我能不能抓到违例」的自检（EXP-2026-0021）。
4. **验证跑「坏掉的分支」**：判据放宽的修复必须构造**仍应判 FAIL** 的样本；
   默认行为变更的修复必须验证**默认路径**真的什么都没做。
5. **以单一事实源为准**：解析器与渲染器共用锚点常量；不做「两处各写一份」的约定（EXP-2026-0013 / KG-093）。
6. **执行留痕**：每条引用实测数据的证据须含 `observed_at`（带时区）与 `observed_base_git_sha`。

### 1.3 已有测试资产（回归面）

| 测试文件 | 行数 | 类型 | 覆盖范围 |
|----------|------|------|----------|
| `upstream/tests/commands/test_ci.py` | 516 | 集成 | `ci` 子命令（含 (d) 检查） |
| `upstream/tests/commands/test_phase.py` | 258 | 集成 | `phase advance` 相位推进 |
| `upstream/tests/commands/test_experience.py` | 930 | 集成 | 经验库 CRUD / 索引 / 过滤 |
| `upstream/tests/commands/test_experience_v29.py` | 352 | 集成 | 经验库 V2.9 语义 |
| `upstream/tests/commands/test_experience_glob_consistency.py` | — | 集成 | 经验库 glob 口径 |
| `upstream/tests/commands/test_experience_index_freshness.py` | — | 集成 | 索引新鲜度 |
| `tools/test_verify_notices.py` | 489 | 集成 | `verify_notices` 21 例（含隔离行为） |
| `upstream/tests/commands/test_canon.py` / `test_canon_coverage.py` | — | 集成 | `canon` 生成与覆盖 |
| `tools/verify_eol.py` | — | 自检 | 行尾治理（TC-EOL-003 直接锚定 SC-004） |

## 二、详细测试案例

### 功能 1：`--dry-run` 契约保真（capability `dry-run-fidelity`）

对应 spec：`dry-run-fidelity.yaml` → REQ-001（SC-001..003）

#### 案例 1.1 — dry-run 真的不落盘

| 字段 | 内容 |
|------|------|
| **ID** | TC-DRY-001 |
| **对应 Spec** | dry-run-fidelity/spec.md → Scenario: SC-001 |
| **优先级** | P0 |
| **预置条件** | 存在一个在办 change；已记录其 `.fstdd.yaml` 的字节与 mtime |
| **输入** | `fstdd phase advance <change> --dry-run` |
| **预期结果** | 退出码 0；stdout 含 `from → to`；`.fstdd.yaml` 字节与 mtime **均不变** |
| **当前状态** | ❌ 修复前会真实落盘（实测把 `understand` 推到 `spec`） |

#### 案例 1.2 — 非 dry-run 路径零变化

| 字段 | 内容 |
|------|------|
| **ID** | TC-DRY-002 |
| **对应 Spec** | dry-run-fidelity/spec.md → Scenario: SC-002 |
| **优先级** | P0 |
| **预置条件** | dry-run 分支已加 |
| **输入** | `fstdd phase advance <change>`（不带 `--dry-run`） |
| **预期结果** | `.fstdd.yaml` 写入内容、退出码、stdout 关键行与修复前一致；`test_phase.py` 全绿 |
| **当前状态** | ✅ 既有用例（回归） |

#### 案例 1.3 — 契约扫描（正 / 反双向）

| 字段 | 内容 |
|------|------|
| **ID** | TC-DRY-003 |
| **对应 Spec** | dry-run-fidelity/spec.md → Scenario: SC-003 |
| **优先级** | P0 |
| **预置条件** | 可构造命令模块样本 |
| **输入** | 扫描 `upstream/fstdd/cli/commands/*.py`：凡含写操作者须出现 `dry_run` 处理 |
| **预期结果** | 当前仓库违规数 == 0；构造「未处理」样本判 FAIL、「已处理」样本判 PASS |
| **当前状态** | ➕ 需新增（防复发契约测试） |

#### 案例 1.4 — 扫描器自检（识别两种既有写法）

| 字段 | 内容 |
|------|------|
| **ID** | TC-DRY-004 |
| **对应 Spec** | dry-run-fidelity/spec.md → Scenario: SC-003（AND-1） |
| **优先级** | P0 |
| **预置条件** | 可构造最小样本源码 |
| **输入** | 对含 `getattr(args, "dry_run", False)` 与 `args.dry_run` 两种写法的样本分别扫描 |
| **预期结果** | 两者**均**被识别为「已处理」（不得只认一种） |
| **当前状态** | ➕ 需新增（EXP-2026-0021 的自检要求） |
| **⚠️ 教训来源** | 本 change 的 Phase 1 曾用 `args\.dry_run` 单范式正则得出「26 个命令全不尊重 dry-run」的**假阳性**；扫描器必须覆盖声明的全部写法 |

### 功能 2：经验库 I/O 契约（capability `experience-io-contract`）

对应 spec：`experience-io-contract.yaml` → REQ-001（SC-004..005）、REQ-002（SC-006..007）

#### 案例 2.1 — 索引落盘无 CRLF

| 字段 | 内容 |
|------|------|
| **ID** | TC-EIO-001 |
| **对应 Spec** | experience-io-contract/spec.md → Scenario: SC-004 |
| **优先级** | P0 |
| **预置条件** | `.fstdd/experiences/.experience-index.yaml` 存在 |
| **输入** | 执行 `fstdd experience verify <id>` 后读该文件字节 |
| **预期结果** | `b"\r\n" not in bytes`；且 `verify_eol` TC-EOL-003 通过 |
| **当前状态** | ❌ 修复前 CRLF=322 / LF=0 |

#### 案例 2.2 — 产出仍为多行

| 字段 | 内容 |
|------|------|
| **ID** | TC-EIO-002 |
| **对应 Spec** | experience-io-contract/spec.md → Scenario: SC-005 |
| **优先级** | P0 |
| **预置条件** | 已补 `newline=""` |
| **输入** | 写入后统计行数 |
| **预期结果** | 行数 > 1（不得因禁用翻译退化为单行） |
| **当前状态** | ➕ 需新增（防「修一个洞开一个洞」） |

#### 案例 2.3 — 无过滤 `--format json` 可解析

| 字段 | 内容 |
|------|------|
| **ID** | TC-EIO-003 |
| **对应 Spec** | experience-io-contract/spec.md → Scenario: SC-006 |
| **优先级** | P0 |
| **预置条件** | 库中存在 `exported_at` 为未加引号日期的条目（实测 74 条中 57 条） |
| **输入** | `fstdd experience list --format json`（**不加任何过滤**） |
| **预期结果** | 退出码 0；stdout 可被 `json.loads` 解析；无 `not JSON serializable` |
| **当前状态** | ❌ 修复前 EXIT=1（`TypeError: Object of type date is not JSON serializable`） |

#### 案例 2.4 — 全部 `json.dumps` 调用点已归一

| 字段 | 内容 |
|------|------|
| **ID** | TC-EIO-004 |
| **对应 Spec** | experience-io-contract/spec.md → Scenario: SC-007 |
| **优先级** | P1 |
| **预置条件** | 可 AST 扫描 `experience.py` |
| **输入** | 枚举该模块全部 `json.dumps` 调用点，检查是否传入可序列化归一 |
| **预期结果** | 「未传归一的调用点」**集合为空**（集合相等，非抽检；修复前有 5 处） |
| **当前状态** | ➕ 需新增 |

#### 案例 2.5 — 既有可序列化输出逐字节不变

| 字段 | 内容 |
|------|------|
| **ID** | TC-EIO-005 |
| **对应 Spec** | experience-io-contract/spec.md → Scenario: SC-007（AND-1） |
| **优先级** | P1 |
| **预置条件** | 已记录修复前 `--language python --format json` 的输出 |
| **输入** | 同一命令复跑，比对文本 |
| **预期结果** | 逐字节一致（归一仅在无法原生序列化时生效） |
| **当前状态** | ➕ 需新增（防 `default=` 改变既有输出） |

### 功能 3：渲染器 / 解析器锚点契约（capability `proposal-extraction-fidelity`）

对应 spec：`proposal-extraction-fidelity.yaml` → REQ-001（SC-008）、REQ-002（SC-009..010）

#### 案例 3.1 — 渲染器输出解析器期望的 h2

| 字段 | 内容 |
|------|------|
| **ID** | TC-PXF-001 |
| **对应 Spec** | proposal-extraction-fidelity/spec.md → Scenario: SC-008 |
| **优先级** | P0 |
| **预置条件** | `canon.py` 渲染器已改 |
| **输入** | `fstdd canon generate <change>` 后检查 proposal.md 的 h2 集合 |
| **预期结果** | 含 `## Capabilities` 与 `## Impact`；`## What Changes` 段不含 capability 条目 |
| **当前状态** | ❌ 修复前 h2 仅 `Why` / `What Changes` / `Success Criteria`；`canon.py` 中 `Impact` **0 命中** |

#### 案例 3.2 — `extract-proposal` 返回非空且无泄漏

| 字段 | 内容 |
|------|------|
| **ID** | TC-PXF-002 |
| **对应 Spec** | proposal-extraction-fidelity/spec.md → Scenario: SC-009 |
| **优先级** | P0 |
| **预置条件** | 某 change 确有 modified capability 与 impact |
| **输入** | `fstdd extract-proposal <change>` |
| **预期结果** | `capabilities.modified` 非空、`impact` 非空；`what_changes` 不含 `**<capability>**：` 条目 |
| **当前状态** | ❌ 修复前 capabilities 恒空 + 5 条 capability 泄漏进 what_changes |

#### 案例 3.3 — 历史 h3 形态向后兼容且两形态结果一致

| 字段 | 内容 |
|------|------|
| **ID** | TC-PXF-003 |
| **对应 Spec** | proposal-extraction-fidelity/spec.md → Scenario: SC-010 |
| **优先级** | P1 |
| **预置条件** | `.fstdd/archive/` 下 41 份历史 proposal.md（h3 形态） |
| **输入** | 对历史 change 执行 `extract-proposal`；再对同一 change 的 h2 形态执行 |
| **预期结果** | 历史形态不报错且 capabilities 非空；两种形态解析结果**一致** |
| **当前状态** | ➕ 需新增（防渲染器改造破坏历史） |

### 功能 4：`ci` TC-ID 判据（capability `ci-check-accuracy`）

对应 spec：`ci-check-accuracy.yaml` → REQ-001（SC-011..012）

#### 案例 4.1 — 41 份既有 test-plan 零误判

| 字段 | 内容 |
|------|------|
| **ID** | TC-CCA-001 |
| **对应 Spec** | ci-check-accuracy/spec.md → Scenario: SC-011 |
| **优先级** | P0 |
| **预置条件** | `.fstdd/` 下 41 份 test-plan |
| **输入** | 逐份执行 (d) 检查 |
| **预期结果** | 报「重复 TC-ID」的份数 == **0**（修复前 25 份，60%） |
| **当前状态** | ❌ 修复前 25 份误判 |

#### 案例 4.2 — 真冲突仍判 FAIL（反向）

| 字段 | 内容 |
|------|------|
| **ID** | TC-CCA-002 |
| **对应 Spec** | ci-check-accuracy/spec.md → Scenario: SC-012 |
| **优先级** | P0 |
| **预置条件** | 可构造 test-plan 样本 |
| **输入** | 样本 A：同一 ID 出现在 **2 个定义点**；样本 B：同一 ID **1 个定义点 + 多处引用** |
| **预期结果** | A 判 FAIL 并列出该 ID；B 判 PASS |
| **当前状态** | ➕ 需新增（EXP-2026-0021：判据放宽必须有反向断言） |

### 功能 5：隔离 opt-in（capability `quarantine-opt-in-safety`）

对应 spec：`quarantine-opt-in-safety.yaml` → REQ-001（SC-013..015）

#### 案例 5.1 — 默认零变化

| 字段 | 内容 |
|------|------|
| **ID** | TC-QIS-001 |
| **对应 Spec** | quarantine-opt-in-safety/spec.md → Scenario: SC-013 |
| **优先级** | P0 |
| **预置条件** | 目录含凭证形状命中的文件；已记录运行前文件清单与内容 |
| **输入** | `python tools/verify_notices.py <dir>`（**不传** `--quarantine`） |
| **预期结果** | 文件清单与内容逐字节不变；`tools/_quarantine/` 无新增 |
| **当前状态** | ❌ 修复前会 `shutil.move` 走命中文件（EXP-2026-0015 二次命中） |

#### 案例 5.2 — `--quarantine` 才移动且记录脱敏

| 字段 | 内容 |
|------|------|
| **ID** | TC-QIS-002 |
| **对应 Spec** | quarantine-opt-in-safety/spec.md → Scenario: SC-014 |
| **优先级** | P0 |
| **预置条件** | 同上 |
| **输入** | `python tools/verify_notices.py <dir> --quarantine` |
| **预期结果** | 命中文件被移入 `tools/_quarantine/`；隔离记录仅含文件名 / md5 前 12 位 / 规则名 / 时间 |
| **当前状态** | ✅ 既有行为（`tools/test_verify_notices.py` 已覆盖，须保持全绿） |

#### 案例 5.3 — 可观测性不因「不破坏」而丢失

| 字段 | 内容 |
|------|------|
| **ID** | TC-QIS-003 |
| **对应 Spec** | quarantine-opt-in-safety/spec.md → Scenario: SC-015 |
| **优先级** | P0 |
| **预置条件** | 默认模式 + 存在命中项 |
| **输入** | `python tools/verify_notices.py <dir> --json` |
| **预期结果** | 顶层含 5 键（新增 `would_quarantine`）；既有 4 键语义不变；默认模式下 `quarantined == []`；存在命中时退出码非 0 |
| **当前状态** | ➕ 需新增（KG-095：第二层防线不可观测） |

## 三、测试执行矩阵

| 能力 | 静态审计 | CLI 实跑 | 反向样本 | 既有回归 | 高风险点 |
|------|---------|---------|---------|---------|---------|
| dry-run-fidelity | 契约扫描（写操作 ↔ dry_run） | phase 双路径实跑 | 未实现样本须 FAIL | test_phase 258 行 | 🔴 dry-run 判定放错位置 |
| experience-io-contract | AST 枚举 json.dumps 调用点 | verify / list 实跑 | 多行断言；既有输出逐字节比对 | test_experience 930 行 | 🟡 `newline` 副作用 |
| proposal-extraction-fidelity | h2/h3 锚点一致性 | canon generate + extract-proposal | 历史 h3 兼容 | test_canon | 🟡 结构变更影响下游 |
| ci-check-accuracy | 定义点解析 | 41 份 test-plan 批量 | 两个定义点须 FAIL | test_ci 516 行 | 🟡 放宽过度 ⇒ 假阴性 |
| quarantine-opt-in-safety | — | 默认 / `--quarantine` 双路径 | 默认零变化 | test_verify_notices 489 行 | 🔴 凭证防线默认行为变更 |

## 四、回归风险矩阵

| 改动区域 | 直接影响 | 回归验证 | 风险 |
|---------|---------|---------|------|
| `phase.py::cmd_phase` | 相位推进 | test_phase 全量 + dry-run 字节断言 | 🟡 |
| `experience.py::_save_index` | 索引落盘 | test_experience / test_experience_v29 + EOL 自检 | 🟡 |
| `experience.py` json 输出 | `--format json/yaml/table` | 三格式输出比对 | 🟡 |
| `canon.py` 渲染器 | **所有新建** proposal.md 结构 | canon verify + extract-proposal | 🔴 |
| `extract_proposal.py` | Phase 1/2 的结构化提取 | 新 change + 41 份历史 | 🟡 |
| `ci.py::check_tcid_unique` | 门禁 (d) 项 | 41 份 test-plan + 构造样本 | 🟡 |
| `tools/verify_notices.py` | 凭证隔离默认行为 | test_verify_notices 全量 | 🔴 |
| 全仓 | — | 全量 pytest upstream/tests + 根 tests + 四自检 | 🟡 |

## 五、建议补充顺序

> ⚠️ 2026-10-07 勘误：本节初稿的 P0/P1 清单与「二、详细测试案例」各案例的 `**优先级**` 字段不一致
> （初稿 11/6，案例表实为 **14/3**）。已按案例表（单一事实源）重列 —— 初稿把
> TC-DRY-002 / TC-EIO-002 / TC-QIS-002 误降为 P1。

1. **第一优先（P0，部署前必补，14 项）**：TC-DRY-001、TC-DRY-002、TC-DRY-003、TC-DRY-004、
   TC-EIO-001、TC-EIO-002、TC-EIO-003、TC-PXF-001、TC-PXF-002、
   TC-CCA-001、TC-CCA-002、TC-QIS-001、TC-QIS-002、TC-QIS-003
2. **第二优先（P1，随后尽快补，3 项）**：TC-EIO-004、TC-EIO-005、TC-PXF-003
3. **第三优先（P2，回归即可）**：全量 pytest 与四自检脚本

## 六、证据记录

| 证据 | observed_at（带时区） | observed_base_git_sha | 来源 |
|---|---|---|---|
| `grep -c dry_run upstream/fstdd/cli/commands/*.py` → phase.py **0**（唯一）；ci 16 / upgrade 6 / init 4 / 其余各 2 | 2026-10-06T17:25:33+00:00 | 0710d5462f973164f83f5096cdf739380e579fb8 | 本机 grep（会话内） |
| 64 个既有 dry-run 断言（test_archive/new/rollback/abort/ci/phase）**全绿** | 2026-10-06T17:4x+00:00 | 0710d54… | pytest 输出 |
| `.experience-index.yaml` CRLF=322 / LF=0；`git` 报 `warning: CRLF will be replaced by LF` | 2026-10-06T17:25:33+00:00 | 0710d54… | 字节统计 |
| `fstdd extract-proposal 2026-10-07-tool-defect-fixes` → `capabilities: {new: [], modified: []}` + 5 条 capability 泄漏进 what_changes | 2026-10-06T17:5x+00:00 | 0710d54… | CLI 输出 |
| 归档 proposal.md h2 仅 `Why`/`What Changes`/`Success Criteria`；`canon.py` 中 `Impact` **0 命中** | 2026-10-06T17:25:33+00:00 | 0710d54… | 文件读取 / grep |
| 41 份 test-plan 中 **25 份（60%）** 含重复 TC-ID 被判 FAIL | 2026-10-06T17:25:33+00:00 | 0710d54… | 本机脚本 |
| `fstdd experience list --format json`（无过滤）→ **EXIT=1**，`TypeError: Object of type date is not JSON serializable` | 2026-10-06T18:0x+00:00 | 0710d54… | CLI 输出 |
| 74 条经验中 **57 条**的 `exported_at` 被 `yaml.safe_load` 解析为 `datetime.date` | 2026-10-06T18:0x+00:00 | 0710d54… | 本机脚本 |
| `verify_notices.py:220` `shutil.move` 在主流程无条件执行；CLI 仅 `directory`/`--json`/`--strict` | 2026-10-06T17:25:33+00:00 | 0710d54… | 源码读取 |
| **缺陷 2 活体复现**：Phase 2 期间执行 `experience` 命令后，索引文件由 HEAD 的 LF 再次变成 **CRLF=322 / LF=0**（已 `git checkout` 还原，保持工作树只含本 change） | 2026-10-06T18:2x+00:00 | 0710d54… | 字节统计 + `git diff` 的 CRLF 告警 |

- `observed_at` 是**信息采集时刻**，不是文档生成时刻。
- 缺 `observed_at` 的证据时效判为「无法判定」（undetermined），**不等同未过期**。
