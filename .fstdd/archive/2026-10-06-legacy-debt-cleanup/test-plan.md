# 测试方案与详细案例 — 遗留债务清理

> 版本：3.3.5（R 轴；本 change 不改版本号）
> 创建日期：2026-10-06
> 对应 Phase 2 Spec：`canonical/specs/code/test-suite-portability.yaml`、`release-tooling-accuracy.yaml`、
> `canonical-hash-integrity.yaml`、`repo-hygiene.yaml`；`canonical/specs/agent/2026-10-06-legacy-debt-cleanup.yaml`
> 观测基线：`observed_at=2026-10-06T21:28:59+08:00`、`observed_base_git_sha=4c6402e366eb3e4e75efafc3f50341b77b0f8fd4`

## 一、测试策略

### 1.1 测试金字塔

本 change 是**门禁自身**的修复，测试重心落在**静态审计**与**双环境实测**两端，而非传统单元测试：

- **静态审计（≈50%）**：AST 扫描（编码调用清单）、文本定向扫描（清单失真表述、`errors=` 取值）、`git ls-files` / `git status` 索引核对。这类断言**确定性最高**，且正是本次要建立的「机器可验证」契约。
- **集成/回归（≈40%）**：pytest 定向复跑（`test_multi_platform.py`、`test_finance_content.py`、`test_repo_home.py`）＋ 全量回归 ＋ 四自检脚本。
- **E2E（≈10%）**：双环境对照（权威 UTF-8 环境 vs 非 UTF-8 环境）跑同一份代码，验证「结果不依赖环境」这一核心目标。

### 1.2 测试原则

1. **断言可逆、不删测**：只做修正，不删除任何既有用例；修复前后用例集合必须逐条一致。
2. **失败可观测，不静默**：解码失败以 U+FFFD 呈现（`errors="replace"`），禁用 `errors="ignore"` 与 `except: pass`（EXP-2026-0014）。
3. **验证跑「坏掉的分支」**：编码修复必须**在非 UTF-8 环境下**验证（只跑权威环境等于没验），仓库卫生必须**同时**验索引与磁盘两点。
4. **以单一事实源为准**：版本断言读 `version.yaml`；canon 以 YAML 为源；不反向改源去迁就产物。
5. **执行留痕**：每条引用实测数据的证据须含 `observed_at`（带时区）与 `observed_base_git_sha`（TC-EPR-002）。

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|----------|--------|------|----------|
| `upstream/tests/`（全量） | 960 collected（实测；Phase 2 曾按旧口径记 851，已更正） | 单元/集成 | FSTDD 内核行为 |
| `tests/test_multi_platform.py` | 12（11 passed + 1 skipped） | 集成 | 多平台安装/入口脚本透传（**含本次 2 例预存失败**） |
| `tests/test_finance_content.py` | 17（L1_01..L1_17；Phase 2 曾误记 13，已更正） | 单元 | 金融内容一致性（**含 `test_L1_11` 预存失败**） |
| `tests/test_upstream_baseline.py` | 6 | 单元 | 上游基线快照锚定（`test_ubl_003` 断言 R 轴出现在文档） |
| `tests/test_install_smoke.py` | 5 | 集成 | L0 冒烟（**`test_L0_01` 含 tag 硬编码，见 TC-RTA-005**） |
| `tests/test_subprocess_encoding_policy.py` | 5 | 静态审计 | 编码调用清单（TC-TSP-001/004，**本次新增**） |
| `tests/test_canon_hash_integrity.py` | 3 | 集成 | canon 双轨一致性（TC-CHI-001..003，**本次新增**） |
| `tests/test_release_manifest_accuracy.py` | 8 | 静态审计 | 清单准确性与版本断言去硬编码（TC-RTA-001/003/005，**本次新增**） |
| `tests/test_repo_hygiene_scratch.py` | 8 | 集成 | `_scratch/` 索引/磁盘/gitignore 三态（TC-RH-001..004，**本次新增**） |
| `upstream/tests/test_repo_home.py::test_a6_no_stray_untracked_files` | 1 | 集成 | 工作树无游离 untracked（除 `.fstdd/changes/`） |
| `tools/verify_rename.py` | 8 TC | 自检 | 改名残留 |
| `tools/verify_eol.py` | 7 TC | 自检 | 行尾符治理 |
| `tools/verify_skill_standards.py` | 7 TC | 自检 | skill 元数据标准 |
| `tools/verify_workbuddy_skills.py` | — | 自检 | WorkBuddy skill 安装校验 |

## 二、详细测试案例

### 功能 1：测试套件环境健壮性（capability `test-suite-portability`）

对应 spec：`test-suite-portability.yaml` → REQ-001（SC-001..004）、REQ-002（SC-005）

#### 案例 1.1 — 编码调用清单归零

| 字段 | 内容 |
|------|------|
| **ID** | TC-TSP-001 |
| **对应 Spec** | test-suite-portability/spec.md → Scenario: SC-001 |
| **优先级** | P0 |
| **预置条件** | `upstream/tests/`、`tests/`、`tools/` 全部 `*.py` 可读 |
| **输入** | AST 扫描三目录，统计 `text=True`/`universal_newlines=True` 且无 `encoding=` 的 `subprocess` 调用数 |
| **预期结果** | 计数 == 0（修复前为 36 / 16 文件） |
| **当前状态** | ➕ 需新增（建议固化为回归断言脚本，防止日后回退） |

#### 案例 1.2 — 非 UTF-8 环境下多平台用例转绿

| 字段 | 内容 |
|------|------|
| **ID** | TC-TSP-002 |
| **对应 Spec** | test-suite-portability/spec.md → Scenario: SC-002 |
| **优先级** | P0 |
| **预置条件** | 不设 `PYTHONUTF8`，控制台保持 GBK/CP936 |
| **输入** | `pytest tests/test_multi_platform.py -q` |
| **预期结果** | `11 passed, 1 skipped`；输出无 `UnicodeDecodeError` |
| **当前状态** | ✅ 已有用例（`test_install_sh_passes_platform` / `test_install_ps1_passes_platform`），当前 FAILED |

#### 案例 1.3 — 权威环境全量回归

| 字段 | 内容 |
|------|------|
| **ID** | TC-TSP-003 |
| **对应 Spec** | test-suite-portability/spec.md → Scenario: SC-003 |
| **优先级** | P0 |
| **预置条件** | 权威门禁环境（控制台 UTF-8 + `PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8`） |
| **输入** | `pytest upstream/tests tests -q` |
| **预期结果** | `0 failed`；`passed >= 906`；`skipped <= 54` |
| **当前状态** | ✅ 已有全量套件（回归基线） |

#### 案例 1.4 — 解码策略审计（禁止静默丢弃）

| 字段 | 内容 |
|------|------|
| **ID** | TC-TSP-004 |
| **对应 Spec** | test-suite-portability/spec.md → Scenario: SC-004 |
| **优先级** | P0 |
| **预置条件** | 修复已完成 |
| **输入** | 扫描全部新增 `errors=` 取值；扫描新增 `except ...: pass` |
| **预期结果** | `errors=` 取值一律 `replace`/`surrogateescape`（无 `ignore`）；无新增静默吞异常 |
| **当前状态** | ➕ 需新增（对应 EXP-2026-0014 预防断言） |

#### 案例 1.5 — 用例集合不变

| 字段 | 内容 |
|------|------|
| **ID** | TC-TSP-005 |
| **对应 Spec** | test-suite-portability/spec.md → Scenario: SC-005 |
| **优先级** | P1 |
| **预置条件** | 已记录修复前 `pytest --collect-only -q` 清单 |
| **输入** | 修复后再次 `pytest --collect-only -q` 并逐条比对 |
| **预期结果** | 用例清单完全一致（无新增/删除/改名/新增 skip） |
| **当前状态** | ➕ 需新增（比对脚本） |

#### 案例 1.6 — PowerShell 生产者编码（build 阶段新发现）

| 字段 | 内容 |
|------|------|
| **ID** | TC-TSP-006 |
| **对应 Spec** | test-suite-portability/spec.md → Scenario: SC-006 |
| **优先级** | P0 |
| **预置条件** | 控制台代码页非 UTF-8（本机实测 CP936） |
| **输入** | `pytest upstream/tests/test_install_scripts.py` |
| **预期结果** | `3 passed`（修复前 `1 failed, 2 passed`） |
| **当前状态** | ➕ 需新增（`_force_utf8_output` 包装 + 既有 3 例） |
| **发现经过** | build 阶段全量 `upstream/tests` 复跑暴露：`test_install_ps1_explicit_python` 因 stdout 中文被解成 U+FFFD 而失败。根因实测 `[Console]::OutputEncoding = gb2312 / CP=936` —— **生产者**（PowerShell 5.1）按控制台代码页输出 GBK，而**消费者**声明 `encoding="utf-8"`。SC-001 的 AST 判据只查「是否声明 encoding」，**抓不到「声明值与生产者不符」这一类** |
| **⚠️ 反向教训** | 首版包装把参数名也加了引号（`'-Yes' '-Python'`）⇒ PowerShell 视为字符串字面量 ⇒ `param()` 位置绑定错位（实测 `$Platform` 被赋成 `-Python`）。已在 `_ps_arg()` 中固化「参数名原样、值才引用」 |

### 功能 2：发布清单与断言准确性（capability `release-tooling-accuracy`）

对应 spec：`release-tooling-accuracy.yaml` → REQ-001（SC-001）、REQ-002（SC-002..004）

#### 案例 2.1 — 发布清单失真表述清零

| 字段 | 内容 |
|------|------|
| **ID** | TC-RTA-001 |
| **对应 Spec** | release-tooling-accuracy/spec.md → Scenario: SC-001 |
| **优先级** | P1 |
| **预置条件** | `.fstdd/standards/release-and-docs.md` 可读 |
| **输入** | 定向扫描「仓库根没有 tests/」及等义表述 |
| **预期结果** | 命中数 == 0；全量测试命令覆盖两处 tests 目录 |
| **当前状态** | ➕ 需新增（定向扫描断言） |

#### 案例 2.2 — `test_L1_11` 在当前版本通过

| 字段 | 内容 |
|------|------|
| **ID** | TC-RTA-002 |
| **对应 Spec** | release-tooling-accuracy/spec.md → Scenario: SC-002 |
| **优先级** | P0 |
| **预置条件** | `.fstdd/version.yaml` 的 `fstdd_version` = `3.3.5` |
| **输入** | `pytest tests/test_finance_content.py::test_L1_11_version_yaml_fstdd_version` |
| **预期结果** | 通过 |
| **当前状态** | ✅ 已有用例，当前 FAILED（硬编码 `== "3.3.0"`） |

#### 案例 2.3 — 版本断言动态性

| 字段 | 内容 |
|------|------|
| **ID** | TC-RTA-003 |
| **对应 Spec** | release-tooling-accuracy/spec.md → Scenario: SC-003 |
| **优先级** | P1 |
| **预置条件** | 可临时构造 `version.yaml` 与 `project.yaml` 版本一致的样本 |
| **输入** | 用任意合法版本值（如 `9.9.9`）构造样本后执行 `test_L1_11` |
| **预期结果** | 通过；且两源不一致时失败并给出差异 |
| **当前状态** | ➕ 需新增（动态性验证） |

#### 案例 2.4 — 仓库根 tests 全量 0 failed

| 字段 | 内容 |
|------|------|
| **ID** | TC-RTA-004 |
| **对应 Spec** | release-tooling-accuracy/spec.md → Scenario: SC-004 |
| **优先级** | P2 |
| **预置条件** | 编码修复 + 版本断言修复均已完成 |
| **输入** | `pytest tests/ -q` |
| **预期结果** | `0 failed`；用例总数不减少 |
| **当前状态** | ✅ 已有（回归） |

#### 案例 2.5 — 发布 tag 断言去硬编码（build 阶段新发现）

| 字段 | 内容 |
|------|------|
| **ID** | TC-RTA-005 |
| **对应 Spec** | release-tooling-accuracy/spec.md → Scenario: SC-005 |
| **优先级** | P0 |
| **预置条件** | `tests/test_install_smoke.py` 可读；`.fstdd/version.yaml` 的 `fstdd_version` 可读 |
| **输入** | ① 扫描仓库根 `tests/*.py` 中形如 `fstdd-v<数字>` 的 tag 字面量；② 宿主隔离（monkeypatch `_run`）分别验证 tag 一致 / 不一致两个分支 |
| **预期结果** | ① 命中数 == 0；② tag 一致时通过、不一致时抛 `AssertionError` |
| **当前状态** | ➕ 需新增（`tests/test_release_manifest_accuracy.py`，5 个函数） |
| **发现经过** | build 阶段双环境对照时暴露：该用例第 39 行 `git fetch origin --tags` 失败即 `skip`，故断言路径**长期未被执行**；仅在 fetch 可达时才走到 `assert "fstdd-v3.1.1" in out` 并失败（实测 `HEAD tag = fstdd-v3.3.5`） |

### 功能 3：canonical 哈希一致性（capability `canonical-hash-integrity`）

对应 spec：`canonical-hash-integrity.yaml` → REQ-001（SC-001..002）、REQ-002（SC-003）

#### 案例 3.1 — inbox-api-only-write 哈希补齐

| 字段 | 内容 |
|------|------|
| **ID** | TC-CHI-001 |
| **对应 Spec** | canonical-hash-integrity/spec.md → Scenario: SC-001 |
| **优先级** | P0 |
| **预置条件** | 归档 `proposal.md` 的 `source_hash` 已同步为 `29c0012fe4d0b612` |
| **输入** | `fstdd canon verify 2026-09-18-inbox-api-only-write` |
| **预期结果** | `2/2 通过` |
| **当前状态** | ❌ 当前 1/2（DC-HASH 不一致） |

#### 案例 3.2 — 全仓 proposal 零欠账

| 字段 | 内容 |
|------|------|
| **ID** | TC-CHI-002 |
| **对应 Spec** | canonical-hash-integrity/spec.md → Scenario: SC-002 |
| **优先级** | P1 |
| **预置条件** | 根 `canonical/proposals/` 全部条目可读 |
| **输入** | 逐条 `fstdd canon verify <change>` |
| **预期结果** | 全部 `2/2`（无 1/2 条目） |
| **当前状态** | ➕ 需新增（批量核对） |

#### 案例 3.3 — 本 change 双轨一致 + 索引零缺失

| 字段 | 内容 |
|------|------|
| **ID** | TC-CHI-003 |
| **对应 Spec** | canonical-hash-integrity/spec.md → Scenario: SC-003 |
| **优先级** | P1 |
| **预置条件** | 4 个 capability spec 已登记进 `.canon-index.yaml` |
| **输入** | `fstdd canon verify 2026-10-06-legacy-debt-cleanup` + 索引文件存在性核对 |
| **预期结果** | `2/2 通过`；索引登记文件零缺失 |
| **当前状态** | ✅ 已有（本 change 自校验） |

### 功能 4：仓库卫生（capability `repo-hygiene`）

对应 spec：`repo-hygiene.yaml` → REQ-001（SC-001..004）

#### 案例 4.1 — `_scratch/` 退出索引

| 字段 | 内容 |
|------|------|
| **ID** | TC-RH-001 |
| **对应 Spec** | repo-hygiene/spec.md → Scenario: SC-001 |
| **优先级** | P0 |
| **预置条件** | 已执行 `git rm -r --cached _scratch/` |
| **输入** | `git ls-files _scratch/` |
| **预期结果** | 输出为空（修复前 27 条目） |
| **当前状态** | ❌ 当前 27 条目被跟踪 |

#### 案例 4.2 — 磁盘实体零损失

| 字段 | 内容 |
|------|------|
| **ID** | TC-RH-002 |
| **对应 Spec** | repo-hygiene/spec.md → Scenario: SC-002 |
| **优先级** | P0 |
| **预置条件** | 已落盘修复前 27 条索引实体快照（`audit/scratch-inventory.txt`，含 25 个文件 md5） |
| **输入** | 逐条核对 27 条索引实体对应的磁盘实体存在性；断言 25 个普通文件非空 |
| **预期结果** | 27 条实体全在（25 普通文件 + 2 个 gitlink 目录）；无 0 字节退化 |
| **当前状态** | ➕ 需新增（破坏性防护断言） |
| **⚠️ 事实更正** | Phase 2 原假设「`_scratch/stdd-dev/stdd-repo/skills/fstdd-fin/SKILL.md` 是备份源」**不成立** —— 实测 2 个 gitlink 目录均为**空目录**（子模块从未 init）。见 ADJ-006 |

#### 案例 4.3 — gitignore 生效且不产生游离 untracked

| 字段 | 内容 |
|------|------|
| **ID** | TC-RH-003 |
| **对应 Spec** | repo-hygiene/spec.md → Scenario: SC-003 |
| **优先级** | P0 |
| **预置条件** | `.gitignore` 已含 `_scratch/` |
| **输入** | `grep _scratch .gitignore` + `git status --porcelain` + `pytest upstream/tests/test_repo_home.py::test_a6_no_stray_untracked_files` |
| **预期结果** | gitignore 含规则；status 无 `_scratch/` 条目；test_a6 通过 |
| **当前状态** | ✅ 已有 `test_a6`（回归） |

#### 案例 4.4 — 三条件同时成立

| 字段 | 内容 |
|------|------|
| **ID** | TC-RH-004 |
| **对应 Spec** | repo-hygiene/spec.md → Scenario: SC-004 |
| **优先级** | P1 |
| **预置条件** | capability 改动完成 |
| **输入** | 联合执行 `git ls-files _scratch/` + gitignore 检查 + 磁盘清点 |
| **预期结果** | 三条件同时成立；无非 `_scratch/` 文件被误删 |
| **当前状态** | ➕ 需新增（联合断言） |

## 三、测试执行矩阵

| 功能模块 | 单元测试 | 集成测试 | E2E | 状态 |
|----------|---------|----------|-----|------|
| test-suite-portability | AST 静态扫描（TC-TSP-001/004） | 非 UTF-8 复跑（TC-TSP-002） | 双环境对照（TC-TSP-003） | 🔴 2 例预存失败 |
| release-tooling-accuracy | 定向文本扫描（TC-RTA-001/003） | 根 tests 复跑（TC-RTA-002/004） | — | 🔴 `test_L1_11` 失败 |
| canonical-hash-integrity | canon verify 单条（TC-CHI-001/003） | 批量 verify（TC-CHI-002） | — | 🔴 1/2 欠账 |
| repo-hygiene | git 索引/磁盘核对（TC-RH-001/002/004） | test_a6 回归（TC-RH-003） | — | 🔴 27 条目误入库 |

## 四、回归风险矩阵

| 风险区域 | 本次改动 | 已有回归保护 | 风险等级 |
|----------|---------|-------------|---------|
| 测试套件解码行为 | 16 文件 36 处补 `encoding=` | 全量 pytest 906 用例 + TC-TSP-005 用例集合比对 | 🟡 |
| 根 tests 版本断言 | `test_L1_11` 改动态 | `test_ubl_003`（R 轴锚定）+ TC-RTA-003 | 🟡 |
| 发布清单文档 | 单行纠错 | 无自动断言 → TC-RTA-001 需新增 | 🟡 |
| canonical 双轨 | 归档 MD 指纹同步 | `canon verify` + TC-CHI-002 | 🟢 |
| 仓库索引 | `_scratch/` 取消跟踪 | `test_a6` + TC-RH-002 磁盘清点 | 🔴（破坏性防护必需） |
| 四自检脚本 | 改动面含 `tools/` | `verify_eol` TC-EOL-005 前缀白名单 | 🟢 |

## 五、建议补充顺序

1. **第一优先（P0，部署前必补）**：TC-TSP-001、TC-TSP-002、TC-TSP-003、TC-TSP-004、TC-TSP-006、TC-RTA-002、TC-RTA-005、TC-CHI-001、TC-RH-001、TC-RH-002、TC-RH-003
2. **第二优先（P1，随后尽快补）**：TC-TSP-005、TC-RTA-001、TC-RTA-003、TC-CHI-002、TC-CHI-003、TC-RH-004
3. **第三优先（P2，回归即可）**：TC-RTA-004

## 六、证据记录

| 证据 | observed_at（带时区） | observed_base_git_sha | 来源 |
|---|---|---|---|
| AST 扫描：subprocess 108 / text-mode 87 / 带 encoding 51 / 缺 36（16 文件） | 2026-10-06T21:28:59+08:00 | 4c6402e366eb3e4e75efafc3f50341b77b0f8fd4 | 本机 AST 脚本（会话内） |
| `pytest tests/test_multi_platform.py` → 2 failed（`UnicodeDecodeError` 0xce） | 2026-10-06T21:28:59+08:00 | 4c6402e366eb3e4e75efafc3f50341b77b0f8fd4 | pytest 输出 |
| `pytest tests/test_finance_content.py::test_L1_11` → 1 failed | 2026-10-06T21:28:59+08:00 | 4c6402e366eb3e4e75efafc3f50341b77b0f8fd4 | pytest 输出 |
| `canon verify 2026-09-18-inbox-api-only-write` → 1/2（YAML 29c0012fe4d0b612 vs MD 16fa0e448d063e2a） | 2026-10-06T21:28:59+08:00 | 4c6402e366eb3e4e75efafc3f50341b77b0f8fd4 | CLI 输出 |
| `git ls-files _scratch/` → 27 条目（25×100644 + 2×160000）；`du -sh` = 20M | 2026-10-06T21:28:59+08:00 | 4c6402e366eb3e4e75efafc3f50341b77b0f8fd4 | git 输出 |
| `.fstdd/standards/release-and-docs.md:29` 失真表述原文 | 2026-10-06T21:28:59+08:00 | 4c6402e366eb3e4e75efafc3f50341b77b0f8fd4 | 文件读取 |
| 权威环境全量 906 passed / 54 skipped / 0 failed | 2026-10-06（D哥 全量执行轮） | 4c6402e366eb3e4e75efafc3f50341b77b0f8fd4 | pytest 输出 |
| `pytest tests/` 权威 UTF-8 → `1 failed, 74 passed, 3 skipped, 1 deselected`；非 UTF-8(gbk) → **逐字一致** | 2026-10-06T22:34Z | 4c6402e366eb3e4e75efafc3f50341b77b0f8fd4 | 双环境对照（Slice 1 B3.4） |
| `pytest tests/test_install_smoke.py::test_L0_01` → `AssertionError: HEAD tag = fstdd-v3.3.5, expected fstdd-v3.1.1`（TC-RTA-005 来源） | 2026-10-06T22:32Z | 4c6402e366eb3e4e75efafc3f50341b77b0f8fd4 | pytest 输出（双环境对照副产物） |
| 根 `tests/*.py` 硬编码发布 tag 字面量 → 5 处（全在 `test_install_smoke.py`）→ 修复后 0 处 | 2026-10-06T22:39Z | 4c6402e366eb3e4e75efafc3f50341b77b0f8fd4 | `grep -rnE 'fstdd-v[0-9]' tests/*.py` |
| `git rm -r --cached _scratch/` 后：索引 27→0、磁盘顶层实体 12→12、27 条索引实体磁盘缺失 0 | 2026-10-06T14:41Z | 4c6402e366eb3e4e75efafc3f50341b77b0f8fd4 | git ls-files / find / 清单逐条核对 |
| `git ls-files --others --ignored --exclude-standard _scratch/` = 25（gitignore 生效）；`--exclude-standard` 游离项 = 仅本 change 自身 25 个文件 | 2026-10-06T14:43Z | 4c6402e366eb3e4e75efafc3f50341b77b0f8fd4 | git 输出 |
| 2 个 gitlink 磁盘目录实为**空目录**（`_scratch/stdd-dev/stdd-repo/`、`_scratch/upstream-cli-sync/`） | 2026-10-06T14:38Z | 4c6402e366eb3e4e75efafc3f50341b77b0f8fd4 | `ls -la`（ADJ-006 依据） |
| 根 `tests/` 权威环境全量 `83 passed, 4 skipped` / **0 failed** | 2026-10-06T14:40Z | 4c6402e366eb3e4e75efafc3f50341b77b0f8fd4 | pytest 输出（TC-RTA-004） |
| 全量 `upstream/tests` = `2 failed, 953 passed, 5 skipped`（11m39s）—— 2 failed 中 `test_a6` 属提交前预期、`test_install_ps1_explicit_python` 属预存缺陷 | 2026-10-06T15:00Z | 4c6402e366eb3e4e75efafc3f50341b77b0f8fd4 | pytest 输出（ADJ-007 依据） |
| `[Console]::OutputEncoding = gb2312 / CP=936`（活动代码页 936）⇒ PowerShell 重定向输出 GBK | 2026-10-06T15:05Z | 4c6402e366eb3e4e75efafc3f50341b77b0f8fd4 | PowerShell 实测 |
| `pytest upstream/tests/test_install_scripts.py` 修复前 `1 failed, 2 passed` → 修复后 **3 passed**（同在 CP936 控制台） | 2026-10-06T15:12Z | 4c6402e366eb3e4e75efafc3f50341b77b0f8fd4 | pytest 输出（TC-TSP-006） |
| 24 个被改文件**零纯行尾变更**（`git diff --ignore-cr-at-eol` 与普通 diff 逐文件相等） | 2026-10-06T14:56Z | 4c6402e366eb3e4e75efafc3f50341b77b0f8fd4 | git 输出 |
| 根 `tests/` 双环境终态：A `92 passed, 3 skipped` / B `92 passed, 3 skipped`（**逐字一致**） | 2026-10-06T14:48Z | 4c6402e366eb3e4e75efafc3f50341b77b0f8fd4 | pytest 输出 |

- `observed_at` 是**信息采集时刻**，不是文档生成时刻。
- 缺 `observed_at` 的证据时效判为「无法判定」（undetermined），**不等同未过期**。
