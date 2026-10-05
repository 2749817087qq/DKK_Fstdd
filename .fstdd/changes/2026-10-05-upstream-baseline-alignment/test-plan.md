# v3.3.5（在办）测试方案与详细案例

> 版本：3.3.5（在办；对应 change `2026-10-05-upstream-baseline-alignment`）
> 创建日期：2026-10-05
> 对应 Phase 2 Spec：
> - `canonical/specs/code/version-nomenclature.yaml`（REQ-001..003 / SC-001..010）
> - `canonical/specs/code/upstream-baseline-alignment.yaml`（REQ-001..003 / SC-001..006）
> - `canonical/specs/agent/2026-10-05-upstream-baseline-alignment.yaml`（验证规格）
> task_type：documentation ｜ mode：standard ｜ FINANCIAL_PROJECT：NO（跳过金融 10 维）

## 一、测试策略

### 1.1 测试金字塔

本变更为**文档 + 一个适配脚本的版本字段去硬编码**，无新增业务逻辑，因此测试侧重**静态一致性
断言**与**门禁脚本回归**，而非单元测试：

| 层次 | 占比 | 覆盖 |
|------|------|------|
| 静态一致性断言（定向扫描 / 字段核对） | 主体 | 活体声明面版本轴自洽、快照证据在位、单一事实源 |
| 集成（脚本实跑） | 次之 | `install_workbuddy_skills.py` + `verify_workbuddy_skills.py` 端到端 |
| 全量回归（E2E） | 闸门 | `pytest upstream/tests` 0 failed + 四自检脚本 |

### 1.2 测试原则

- **断言可执行、可复现**：每条 TC 给出**可复现命令**与其期望退出码/输出，不以「人眼阅读文档」判定。
- **双向断言**：既断言正确轴存在（如 `stdd_version: "3.1.0"`），也断言错误串不存在
  （活体声明面无「内核 = 3.0.5」），单向会漏残留。
- **范围显式**：扫描范围显式排除 `upstream/` 上游自有文档与历史/临时区 —— 漏排除会误报，
  过排除会掩盖真实残留。
- **不改判据**：既有门禁脚本（`verify_rename` 等）本次**不改其判定语义**，只回归验证其仍绿。

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|----------|--------|------|----------|
| `tools/verify_rename.py` | 8 TC | 静态 + 集成 | 改名残留（含隔离安装、CLI 冒烟、数据目录迁移） |
| `tools/verify_eol.py` | 7 TC | 静态 | 行尾符治理（含 TC-EOL-005 工作树干净度） |
| `tools/verify_skill_standards.py` | 7 TC | 静态 | skill frontmatter 标准（只认 `version` 字段） |
| `tools/verify_workbuddy_skills.py` | 校验器（含 CLI 冒烟） | 集成 | 生成戳版本、哨兵、路径适配、影子副本 |
| `upstream/tests/` | 906 passed / 54 skipped | 单元 + 集成 + E2E | 全仓回归基线（改动前后须零 failed） |
| `upstream/tests/commands/test_install.py` | 含 TC-PSI-002 | 单元 | 上游 `fstdd install` 的 `stdd_version` 派生口径（佐证本变更方向） |
| `upstream/tests/test_fstdd_matrix.py` / `test_cross_cutting_verification.py` / `test_install_source.py` | 多例 | 单元 | 直接加载/读取 `tools/install_workbuddy_skills.py`，本变更须不破坏 |

## 二、详细测试案例

### 功能 1：版本口径三轴（capability `version-nomenclature`）

对应 `version-nomenclature/spec.md` → REQ-001..003。

#### 案例 1.1 — NOTICE §1 无自相矛盾的版本声明

| 字段 | 内容 |
|------|------|
| **ID** | TC-VNOM-001 |
| **对应 Spec** | version-nomenclature → SC-001 |
| **优先级** | P0 |
| **预置条件** | NOTICE.md 已按轴修正（E 轴标明「上游最新发布」，内核注记写 K=3.1.0） |
| **输入** | 读取 `NOTICE.md` §1 全文 |
| **预期结果** | §1 内不存在把本仓 vendored 内核版本写作 3.0.5 的表述；E 轴数字显式标注为上游最新发布且附基线快照链接；任两处版本声明互不矛盾 |
| **当前状态** | ❌ 测试缺（现状 `:33` 为 3.0.5 且称「上游版本号」） |

#### 案例 1.2 — README 头部两轴并列

| 字段 | 内容 |
|------|------|
| **ID** | TC-VNOM-002 |
| **对应 Spec** | version-nomenclature → SC-002 |
| **优先级** | P0 |
| **预置条件** | README.md 徽章区已改 |
| **输入** | 读取 `README.md` 第 3–13 行 |
| **预期结果** | 同时出现 E 轴徽章（标注为上游发布语义，含 v3.0.5）与 K 轴徽章（含 3.1.0）；引言保留「上游 leonai42/stdd（MIT）衍生作品」署名 |
| **当前状态** | ❌ 测试缺（现状仅一个未标轴徽章） |

#### 案例 1.3 — fstdd-fin frontmatter 与 sources 用内核轴

| 字段 | 内容 |
|------|------|
| **ID** | TC-VNOM-003 |
| **对应 Spec** | version-nomenclature → SC-003 |
| **优先级** | P0 |
| **预置条件** | `skills/fstdd-fin/SKILL.md` 已改 |
| **输入** | 读取该文件 frontmatter（前 21 行） |
| **预期结果** | `stdd_version` 匹配 `"3.1.0"`（纯 `[0-9.]+`）；sources 方法论基底指向 K 并以 E 标注上游溯源；`version` 仍为 `"1.0.0"` |
| **当前状态** | ❌ 测试缺（现状 `3.0.5-fin.2`） |

#### 案例 1.4 — 安装说明版本表述按轴落位

| 字段 | 内容 |
|------|------|
| **ID** | TC-VNOM-004 |
| **对应 Spec** | version-nomenclature → SC-004 |
| **优先级** | P1 |
| **预置条件** | `docs/WORKBUDDY_INSTALL_NOTES.md` 已改 |
| **输入** | 读取该文档全部含版本号的表述（至少 :5 与 :89 区域） |
| **预期结果** | 上游项目来源 → E 轴并标明；内核/方法学形态 → K 轴或去除歧义版本词；无「内核/方法学 = 3.0.5」 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.5 — 活体声明面零矛盾定向扫描

| 字段 | 内容 |
|------|------|
| **ID** | TC-VNOM-005 |
| **对应 Spec** | version-nomenclature → SC-005 |
| **优先级** | P0 |
| **预置条件** | SC-001..SC-004 修正完成 |
| **输入** | 对 5 个活体声明面执行「内核轴被写作 3.0.5」定向扫描（命令原文记入 §六 证据表） |
| **预期结果** | 命中数为 0；扫描范围不含 `upstream/` 上游自有文档与历史/临时区 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.6 — 生成 frontmatter 版本字段派生

| 字段 | 内容 |
|------|------|
| **ID** | TC-VNOM-006 |
| **对应 Spec** | version-nomenclature → SC-006 |
| **优先级** | P0 |
| **预置条件** | 安装脚本已去硬编码 |
| **输入** | `FSTDD_OUT=<临时目录> python tools/install_workbuddy_skills.py`，读取任一生成 SKILL.md 的 frontmatter |
| **预期结果** | `version: "3.3.4"`（= `repo_stdd_version(REPO_ROOT)`）；`stdd_version: "3.1.0"`（纯 `[0-9.]+`）；生成 frontmatter 无字面量 3.0.5 |
| **当前状态** | ❌ 测试缺（现状两字段均 `"3.0.5"`） |

#### 案例 1.7 — 来源横幅与 docstring 去硬编码

| 字段 | 内容 |
|------|------|
| **ID** | TC-VNOM-007 |
| **对应 Spec** | version-nomenclature → SC-007 |
| **优先级** | P0 |
| **预置条件** | 安装脚本横幅与 docstring 已改 |
| **输入** | 读取生成 skill 头部横幅 + `tools/install_workbuddy_skills.py` 头部 docstring |
| **预期结果** | 横幅以 K 描述正文来源、保留上游项目名与源仓库 URL、保留绝对路径适配；docstring 无未标轴硬编码版本号；均无字面量 3.0.5 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.8 — install + verify 端到端 PASS

| 字段 | 内容 |
|------|------|
| **ID** | TC-VNOM-008 |
| **对应 Spec** | version-nomenclature → SC-008 |
| **优先级** | P0 |
| **预置条件** | 安装脚本改动完成 |
| **输入** | `python tools/install_workbuddy_skills.py`（退出码）→ `python tools/verify_workbuddy_skills.py`（输出/退出码） |
| **预期结果** | 安装退出码 0；校验输出含 `[PASS]` 且退出码 0；生成戳仍为 `生成自 stdd-repo@3.3.4`；`fstdd-deliver` 哨兵与静默回传策略块完整 |
| **当前状态** | ✅ 可复用（现有校验器即断言载体） |

#### 案例 1.9 — 改名门禁语义不变

| 字段 | 内容 |
|------|------|
| **ID** | TC-VNOM-009 |
| **对应 Spec** | version-nomenclature → SC-009 |
| **优先级** | P0 |
| **预置条件** | 全部改动完成；`verify_rename.py` 自身未被改动（`git diff` 无名） |
| **输入** | `python tools/verify_rename.py` |
| **预期结果** | `8/8 通过`；`EXCLUDE_DIRS` 与 `ALLOWED_OLD_MENTIONS` 内容与改动前一致；`upstream/` 上游自有文档零改动 |
| **当前状态** | ✅ 已有（8/8 基线） |

#### 案例 1.10 — 标准与行尾门禁回归

| 字段 | 内容 |
|------|------|
| **ID** | TC-VNOM-010 |
| **对应 Spec** | version-nomenclature → SC-010 |
| **优先级** | P1 |
| **预置条件** | 全部改动完成 |
| **输入** | `python tools/verify_skill_standards.py`；`python tools/verify_eol.py` |
| **预期结果** | 分别 `7/7 通过`；fstdd-fin 的 `version` 仍为 1.0.0；改动文件为 LF 行尾 |
| **当前状态** | ✅ 已有（7/7 基线） |

### 功能 2：上游基线对齐（capability `upstream-baseline-alignment`）

对应 `upstream-baseline-alignment/spec.md` → REQ-001..003。

#### 案例 2.1 — 基线快照文档存在且含必备证据段

| 字段 | 内容 |
|------|------|
| **ID** | TC-UBL-001 |
| **对应 Spec** | upstream-baseline-alignment → SC-001 |
| **优先级** | P0 |
| **预置条件** | `docs/UPSTREAM_BASELINE.md` 已落盘 |
| **输入** | 检查文件存在 + 逐项核对证据段 |
| **预期结果** | 文件存在；含 observed_at（带时区）、base git sha、tag、HEAD sha、pushed_at、Releases 状态、分支状态、通道排除（Gitee/PyPI） |
| **当前状态** | ❌ 测试缺（新增产物） |

#### 案例 2.2 — 快照数值与实测一致

| 字段 | 内容 |
|------|------|
| **ID** | TC-UBL-002 |
| **对应 Spec** | upstream-baseline-alignment → SC-002 |
| **优先级** | P0 |
| **预置条件** | 上游探针已完成（观测时点见 §六） |
| **输入** | 比对文档记录值与实测值 |
| **预期结果** | tag=v3.0.5；HEAD sha=b9a4af62b5f4fd2747884c0a61febbc341792ac2；pushed_at=2026-08-17T15:25:43Z；Releases 为空；记录观测通道（ssh fstdd-hub）；无凭证/内网私密路径/用户数据 |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.3 — 本仓领先量清单

| 字段 | 内容 |
|------|------|
| **ID** | TC-UBL-003 |
| **对应 Spec** | upstream-baseline-alignment → SC-003 |
| **优先级** | P1 |
| **预置条件** | 文档含领先量段 |
| **输入** | 读取领先量清单并与机器可读源核对 |
| **预期结果** | 至少覆盖 K（3.1.0）与 R（3.3.4）两轴，数值与 `.fstdd/version.yaml` / `upstream/pyproject.toml` 一致 |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.4 — 经验库回传边界结论

| 字段 | 内容 |
|------|------|
| **ID** | TC-UBL-004 |
| **对应 Spec** | upstream-baseline-alignment → SC-004 |
| **优先级** | P0 |
| **预置条件** | 对标段已落盘 |
| **输入** | 读取对标段 |
| **预期结果** | 明确 `leonai42/stdd-experiences` 非我方回传目标；指明我方目标为 `2749817087qq/Fstdd-experiences`；记录该上游库最近推送观测值 |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.5 — 我方 node 前缀条目数实测值

| 字段 | 内容 |
|------|------|
| **ID** | TC-UBL-005 |
| **对应 Spec** | upstream-baseline-alignment → SC-005 |
| **优先级** | P0 |
| **预置条件** | 只读拉取上游经验库清单（经 ssh fstdd-hub） |
| **输入** | 按 node 前缀（FSTDD003 / FSTDD-003）计数 |
| **预期结果** | 文档给出计数的**实测值**（0 亦为有效实测值）；写明计数口径；与观测时点绑定、标注为实测而非估计 |
| **当前状态** | ❌ 测试缺（BUILD 执行探针后回填） |

#### 案例 2.6 — 快照数字单一事实源

| 字段 | 内容 |
|------|------|
| **ID** | TC-UBL-006 |
| **对应 Spec** | upstream-baseline-alignment → SC-006 |
| **优先级** | P1 |
| **预置条件** | NOTICE / README 已改为链接引用 |
| **输入** | 在 `NOTICE.md` / `README.md` 中扫描 sha（`b9a4af62…`）与 `2026-08-17T15:25:43Z` 字面量 |
| **预期结果** | 命中数为 0；两文件对基线的引用为指向 `docs/UPSTREAM_BASELINE.md` 的链接 |
| **当前状态** | ❌ 测试缺 |

### 功能 3：整体回归闸门

#### 案例 3.1 — 四自检全绿

| 字段 | 内容 |
|------|------|
| **ID** | TC-REG-001 |
| **对应 Spec** | 覆盖 SC-008 / SC-009 / SC-010 |
| **优先级** | P0 |
| **预置条件** | 全部改动完成；工作树范围符合 TC-EOL-005 |
| **输入** | `verify_rename` / `verify_eol` / `verify_skill_standards` / `verify_workbuddy_skills` |
| **预期结果** | 8/8、7/7、7/7、PASS（四项退出码均 0） |
| **当前状态** | ✅ 已有（改动前基线全绿） |

#### 案例 3.2 — 全量回归 0 failed

| 字段 | 内容 |
|------|------|
| **ID** | TC-REG-002 |
| **对应 Spec** | 覆盖全 change（回归保护） |
| **优先级** | P0 |
| **预置条件** | 全部改动完成 |
| **输入** | `pytest upstream/tests -q` |
| **预期结果** | 0 failed（基线 906 passed / 54 skipped）；重点确认 `test_fstdd_matrix` / `test_cross_cutting_verification` / `test_install_source` / `test_canonical_in_workspace` 不受安装脚本改动波及 |
| **当前状态** | ✅ 已有（基线 0 failed） |

## 三、测试执行矩阵

| 功能模块 | 静态断言 | 集成 | E2E | 状态 |
|----------|---------|------|-----|------|
| 活体声明面版本轴（NOTICE/README/fstdd-fin/NOTES） | TC-VNOM-001..005 | — | — | 🔴 待建 |
| 适配层版本派生（install/verify） | TC-VNOM-006/007 | TC-VNOM-008 | — | 🔴 待建 |
| 既有门禁回归（rename/eol/standards/verify） | TC-VNOM-009/010、TC-REG-001 | — | — | 🟢 已有 |
| 上游基线快照（UPSTREAM_BASELINE.md） | TC-UBL-001..004/006 | TC-UBL-005（只读探针） | — | 🔴 待建 |
| 全量回归 | — | — | TC-REG-002 | 🟢 已有 |

## 四、回归风险矩阵

| 风险区域 | 本次改动 | 已有回归保护 | 风险等级 |
|----------|----------|-------------|---------|
| `tools/install_workbuddy_skills.py` 生成物 | frontmatter `version`/`stdd_version` 与横幅去硬编码 | `verify_workbuddy_skills`（生成戳/哨兵/路径）；`test_fstdd_matrix`；`test_cross_cutting_verification::test_b5/test_d6`；`test_install_source` | 🟡 中 |
| `NOTICE.md` | §1 版本轴显式化 | 无自动断言 → 本次定向扫描（TC-VNOM-001/005） | 🟡 中 |
| `README.md` | 徽章/引言双轴 | `test_install_source::test_f1`（README 前置要求须含 requests）——改动须不触及其判定串 | 🟢 低 |
| `skills/fstdd-fin/SKILL.md` | `stdd_version` + sources | `verify_skill_standards`（只认 `version`）；`test_canonical_in_workspace::test_d2`（≥5 skill 含 stdd-repo） | 🟢 低 |
| `docs/WORKBUDDY_INSTALL_NOTES.md` | 版本表述 | `test_install_source` 路径口径断言（工作区/法定源） | 🟡 中 |
| `upstream/**`（上游自有文档） | **零改动** | `verify_rename`（排除区语义）、MIT 署名事实 | 🟢 低 |
| 历史/临时区 | **零改动** | `verify_rename` 排除区 | 🟢 低 |
| 新增 `docs/UPSTREAM_BASELINE.md` | 新文件 | `verify_eol`（LF）、`verify_rename`（无旧名残留） | 🟢 低 |

## 五、建议补充顺序

1. **第一优先**（Gate 3 前必过，P0）：TC-VNOM-001/002/003/005/006/007/008/009、TC-UBL-001/002/004/005、TC-REG-001/002
2. **第二优先**（同变更内完成，P1）：TC-VNOM-004/010、TC-UBL-003/006
3. **第三优先**（后续 change）：把「活体声明面版本轴自洽」沉淀为常驻定向断言脚本（本 change 的 `impact.code` 限定唯一代码面改动，故本次以可复现命令 + 证据记录承接）

## 六、证据记录

> 每条引用实测数据的证据必须可定位**观测时刻**与**代码版本**（TC-EPR-002）。
> `observed_at` 是**信息采集时刻**，不是文档生成时刻。

| 证据 | observed_at（带时区） | observed_base_git_sha | 来源 |
|---|---|---|---|
| 上游基线探针：tag=v3.0.5 / HEAD=b9a4af62b5f4fd2747884c0a61febbc341792ac2 / pushed_at=2026-08-17T15:25:43Z / Releases=[] / 仅 master | 2026-10-05T11:20:00+08:00 | 1046f5eaffa4f4c80b533ca2d24700fd7b0a46f2 | GitHub API，经 `ssh fstdd-hub` 只读（本机不可直连 github.com:443） |
| 通道排除：Gitee `leonai42/stdd`=404；PyPI `stdd`=同名无关包（LiiraGH PyQt6 模板）、`fstdd`=404 | 2026-10-05T11:20:00+08:00 | 1046f5eaffa4f4c80b533ca2d24700fd7b0a46f2 | 经 `ssh fstdd-hub` 只读查询 |
| 本仓版本口径实测：R=3.3.4（`.fstdd/config.d/project.yaml`、`.fstdd/version.yaml`）；K=3.1.0（`.fstdd/version.yaml: upstream_version`、`upstream/pyproject.toml`） | 2026-10-05T11:20:00+08:00 | 1046f5eaffa4f4c80b533ca2d24700fd7b0a46f2 | 逐文件读取 |
| 漂移点定位：NOTICE.md:15/:33、README.md:5、skills/fstdd-fin/SKILL.md:10/:17、docs/WORKBUDDY_INSTALL_NOTES.md:5/:89、tools/install_workbuddy_skills.py:304-305/:377 | 2026-10-05T11:20:00+08:00 | 1046f5eaffa4f4c80b533ca2d24700fd7b0a46f2 | 逐文件读取（行号为准） |
| 上游经验库 `leonai42/stdd-experiences` pushed_at=2026-10-05T00:31:25Z | 2026-10-05T11:20:00+08:00 | 1046f5eaffa4f4c80b533ca2d24700fd7b0a46f2 | 经 `ssh fstdd-hub` 只读查询 |
| 我方 node 前缀条目数实测值（TC-UBL-005）= **0**（计数口径：文件名前缀 `FSTDD003-` / `FSTDD-003-` 命中 **0**；`HEAD` 归档全文扫描 `FSTDD003` / `FSTDD-003` 命中 **0**） | 2026-10-05T12:02:00+08:00 | 1046f5eaffa4f4c80b533ca2d24700fd7b0a46f2 | 经 `ssh fstdd-hub` 只读：GitHub tree API（210 项，truncated=false）+ 流式 tarball 全文扫描 |
| 定向扫描与快照断言（TC-VNOM-005 / TC-UBL-001..006） | 2026-10-05T12:02:00+08:00 | 1046f5eaffa4f4c80b533ca2d24700fd7b0a46f2 | `pytest tests/test_version_nomenclature.py tests/test_upstream_baseline.py -v` → 12 + 6 全通过；命令与断言原文见 `test-report.md` |

## 七、金融 10 维测试覆盖

> 由 `fstdd-understand` Step 0.5 判定：**FINANCIAL_PROJECT = NO**（本变更不涉及支付/银行/交易/
> 风控等金融关键词，无金融数据面）。故本节跳过，不填充 10 维表格。