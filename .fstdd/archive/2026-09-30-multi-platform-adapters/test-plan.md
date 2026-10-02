# v3.0 测试方案与详细案例

> 版本：3.0
> 创建日期：2026-09-30
> 对应 Phase 2 Spec：`canonical/specs/code/2026-09-30-multi-platform-adapters.yaml`、`canonical/specs/agent/2026-09-30-multi-platform-adapters.yaml`

## 一、测试策略

### 1.1 测试金字塔

1. **单元测试**：`platforms.yaml` 解析、front-matter 渲染（各平台字段取舍）、skill 根目录解析、未知平台拒绝。
2. **集成测试**：安装器端到端产出（落点 + front-matter + 正文同源）、校验器平台感知、安装器/校验器共用清单。
3. **回归测试**：`--platform workbuddy`（含缺省）与变更前基准**逐字节比对**。
4. **E2E 测试**：`install.sh --platform <p>` 与 `install.ps1 -Platform <p>` 全链路（装依赖 → 安装 → 校验），至少 claude-code 与 trae 实测。
5. **静态审查**：源码无按平台 if/else 分支、仓库无第二份手写正文副本（以代码审查 + 断言双保险）。

### 1.2 测试原则

- 先写测试再实现；每个 Slice 单独 red-green。
- 断言行为与不变量（落点、front-matter 字段、字节一致），不绑定易变日期、日志措辞或机器绝对路径。
- 「默认 workbuddy 逐字节一致」是本变更**唯一强回归保护**，必须独立成 P0 回归用例。
- 平台差异断言必须落到**清单数据**上，而不是在测试里再写一份平台分支（否则测试自身成为第二事实源）。

### 1.3 已有测试资产

> 下述为仓库内**上游 vendor**（`upstream/tests/`）相关用例：它们验证的是**上游** `fstdd install`
> 与上游 skill 元数据，对本仓库安装层改造是**间接参考**（可借鉴平台名与 front-matter 规则断言口径），
> **不能**直接证明本仓库 `tools/*` 改造正确。实测清单（`observed_at=2026-09-30T07:56:18+00:00`,
> `observed_base_git_sha=f556899fc17bba1bcbe914c85fe9411a3eb01a72`）：

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|----------|--------|------|----------|
| `upstream/tests/commands/test_install.py` | 14 | 单元/集成 | 平台安装（claude-code/cursor/trae/workbuddy/codex）、不支持平台、dry-run、front-matter 形态 |
| `upstream/tests/test_install_source.py` | 24 | 集成 | 源解析顺序、`install.sh`/`install.ps1` 依赖检查、包元数据一致性 |
| `upstream/tests/test_install_scripts.py` | 3 | 集成 | 安装脚本行为 |
| `upstream/tests/commands/test_skill.py` | 6 | 单元 | skill 创建与分发路由 |
| `upstream/tests/test_fstdd_matrix.py` | 41 | 矩阵 | 平台/能力矩阵 |
| `upstream/tests/test_license_compliance.py` | 15 | 合规 | skill front-matter 的 license 等字段 |
| `tools/verify_skill_standards.py` / `tools/check_skill_metadata.py` / `tools/verify_rename.py` | N/A（脚本） | 静态校验 | 本仓库 skill 元数据四项、命名残留、EOL |

本仓库 `tools/install_workbuddy_skills.py` / `tools/verify_workbuddy_skills.py` 目前**没有专属 pytest**，
故下表各 TC 绝大多数「当前状态」为 ❌ 测试缺，需在 BUILD 阶段补齐。

## 二、详细测试案例

### 功能 1：平台薄清单事实源

#### 案例 1.1 — 每平台一条清单且正文不复制

| 字段 | 内容 |
|------|------|
| **ID** | TC-MPA-001 |
| **对应 Spec** | multi-platform-adapters → SC-001 |
| **优先级** | P0 |
| **预置条件** | `platforms.yaml` 已存在并声明 workbuddy / claude-code / trae |
| **输入** | 解析 `platforms.yaml`，枚举每平台清单字段，检查正文来源指向 |
| **预期结果** | 每平台含显示名 + skill 根解析规则 + front-matter 规则；正文来源指向共享正文，清单内无正文副本 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.2 — 新增平台只需改清单

| 字段 | 内容 |
|------|------|
| **ID** | TC-MPA-002 |
| **对应 Spec** | multi-platform-adapters → SC-002 |
| **优先级** | P0 |
| **预置条件** | 现有安装层代码未改动 |
| **输入** | 仅在 `platforms.yaml` 增加一条平台清单后执行安装 |
| **预期结果** | 安装器可产出该平台 skill；全程未新增任何代码分支（`git diff` 仅含清单文件） |
| **当前状态** | ❌ 测试缺 |

### 功能 2：参数化安装器

#### 案例 2.1 — claude-code 落点与 front-matter

| 字段 | 内容 |
|------|------|
| **ID** | TC-MPA-003 |
| **对应 Spec** | multi-platform-adapters → SC-003 |
| **优先级** | P0 |
| **预置条件** | `platforms.yaml` 已声明 claude-code 规则 |
| **输入** | `install_workbuddy_skills.py --platform claude-code`（`FSTDD_OUT` 指向临时目录） |
| **预期结果** | 产出 `<claude skills 根>/<name>/SKILL.md`；front-matter 无 `version` / `trigger_keywords`；description 为引号形态 |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.2 — 未知平台被拒绝而非静默回退

| 字段 | 内容 |
|------|------|
| **ID** | TC-MPA-004 |
| **对应 Spec** | multi-platform-adapters → SC-004 |
| **优先级** | P0 |
| **预置条件** | `platforms.yaml` 未声明 `qoder` |
| **输入** | `install_workbuddy_skills.py --platform qoder` |
| **预期结果** | 非零退出码并列出可用平台；未向任何平台目录写入 skill |
| **当前状态** | ❌ 测试缺 |

### 功能 3：workbuddy 逐字节回归（强回归保护）

#### 案例 3.1 — 显式 workbuddy 与基准逐字节一致

| 字段 | 内容 |
|------|------|
| **ID** | TC-MPA-005 |
| **对应 Spec** | multi-platform-adapters → SC-005 |
| **优先级** | P0 |
| **预置条件** | 变更前已保存 workbuddy 产出的字节级基准快照 |
| **输入** | `install_workbuddy_skills.py --platform workbuddy`（固定 `FSTDD_OUT`） |
| **预期结果** | 每个 `<name>/SKILL.md` 的哈希与基准快照逐字节一致（含正文、front-matter、生成戳） |
| **当前状态** | ❌ 测试缺 |

#### 案例 3.2 — 缺省等同显式 workbuddy

| 字段 | 内容 |
|------|------|
| **ID** | TC-MPA-006 |
| **对应 Spec** | multi-platform-adapters → SC-006 |
| **优先级** | P0 |
| **预置条件** | 同上基准快照可用 |
| **输入** | 不传 `--platform` 执行安装器 |
| **预期结果** | 行为与 `--platform workbuddy` 完全一致；默认值来自集中声明，未散落在多处 |
| **当前状态** | ❌ 测试缺 |

### 功能 4：无平台分支代码 / 正文同源

#### 案例 4.1 — 任一平台正文与共享源同源

| 字段 | 内容 |
|------|------|
| **ID** | TC-MPA-007 |
| **对应 Spec** | multi-platform-adapters → SC-007 |
| **优先级** | P0 |
| **预置条件** | 已安装任一平台（如 claude-code） |
| **输入** | 剥离 front-matter 后比对平台正文与仓库共享正文源（经适配替换） |
| **预期结果** | 正文与共享源同源可验；仓库内无第二份按平台复制的手写正文副本 |
| **当前状态** | ❌ 测试缺 |

#### 案例 4.2 — 源码无按平台 if/else 分支

| 字段 | 内容 |
|------|------|
| **ID** | TC-MPA-008 |
| **对应 Spec** | multi-platform-adapters → SC-008 |
| **优先级** | P0 |
| **预置条件** | 安装层改造已完成 |
| **输入** | 审查 `tools/install_workbuddy_skills.py` / `tools/_skill_install_env.py` 源码 |
| **预期结果** | 无按平台硬编码的 if/else 分支；平台差异全部由 `platforms.yaml` 数据驱动 |
| **当前状态** | ❌ 测试缺 |

### 功能 5：入口脚本透传

#### 案例 5.1 — install.sh 透传 --platform

| 字段 | 内容 |
|------|------|
| **ID** | TC-MPA-009 |
| **对应 Spec** | multi-platform-adapters → SC-009 |
| **优先级** | P1 |
| **预置条件** | POSIX shell 环境，解释器绝对路径可用 |
| **输入** | `./install.sh --platform claude-code`（另一轮不传平台） |
| **预期结果** | `--platform claude-code` 被透传给安装器与校验器并据此产出/校验；不传时默认行为不变 |
| **当前状态** | ❌ 测试缺 |

#### 案例 5.2 — install.ps1 透传 -Platform

| 字段 | 内容 |
|------|------|
| **ID** | TC-MPA-010 |
| **对应 Spec** | multi-platform-adapters → SC-010 |
| **优先级** | P1 |
| **预置条件** | Windows PowerShell，解释器绝对路径可用 |
| **输入** | `./install.ps1 -Platform trae`（另一轮不传平台） |
| **预期结果** | `-Platform trae` 被透传给安装器与校验器并据此产出/校验；不传时默认行为不变 |
| **当前状态** | ❌ 测试缺 |

### 功能 6：平台感知校验

#### 案例 6.1 — 校验缺省针对 workbuddy

| 字段 | 内容 |
|------|------|
| **ID** | TC-MPA-011 |
| **对应 Spec** | multi-platform-adapters → SC-011 |
| **优先级** | P1 |
| **预置条件** | workbuddy 已按现状安装 |
| **输入** | `verify_workbuddy_skills.py`（不传平台） |
| **预期结果** | 针对 workbuddy 安装点校验；判据与安装器共用 `platforms.yaml` |
| **当前状态** | ❌ 测试缺 |

#### 案例 6.2 — 校验指定平台

| 字段 | 内容 |
|------|------|
| **ID** | TC-MPA-012 |
| **对应 Spec** | multi-platform-adapters → SC-012 |
| **优先级** | P1 |
| **预置条件** | claude-code 或 trae 已按该平台安装 |
| **输入** | `verify_workbuddy_skills.py --platform claude-code`（及 trae） |
| **预期结果** | 针对该平台安装点与其 front-matter 规则校验；能区分「已装且合规」与「未装/不合规」 |
| **当前状态** | ❌ 测试缺 |

## 三、测试执行矩阵

| 功能模块 | 单元测试 | 集成测试 | E2E | 状态 |
|----------|---------|----------|-----|------|
| platforms.yaml 事实源 | 待补 | 待补 | N/A | 🔴 |
| 参数化安装器（--platform） | 待补 | 待补 | 待补 | 🔴 |
| workbuddy 逐字节回归 | 待补 | 待补 | 待补 | 🔴 |
| 无平台分支/正文同源 | 待补 | 待补 | N/A | 🔴 |
| 入口脚本透传 | N/A | 待补 | 待补 | 🔴 |
| 平台感知校验 | 待补 | 待补 | 待补 | 🔴 |
| 上游 install 既有用例（间接参考） | 现有 | 现有 | 现有 | 🟢 |

## 四、回归风险矩阵

| 风险区域 | V3.0 改动 | 已有回归保护 | 风险等级 |
|----------|-------------|-------------|---------|
| **默认 workbuddy 产出** | 安装器参数化后，workbuddy 走「清单渲染 + 现状头」路径 | **逐字节基准快照比对（TC-MPA-005/006）**；变更前先固化基准 | 🔴 高 |
| skill 根目录解析 | 由单一 WorkBuddy 判据泛化为平台感知 | TC-MPA-006/011；workbuddy 分支保持既有解析顺序 | 🟡 中 |
| front-matter 渲染 | 由固定模板改为清单驱动 | TC-MPA-003/005；claude-code 以上游实测差异为基准 | 🟡 中 |
| 入口脚本 | `install.sh`/`install.ps1` 增参数 | TC-MPA-009/010；无参路径断言行为不变 | 🟡 中 |
| 校验器 | 增平台感知，默认仍 workbuddy | TC-MPA-011/012 | 🟡 中 |
| 正文适配（安全策略/路径替换） | 适配步骤重构为「共享正文一次替换」 | TC-MPA-007；各平台正文均须含哨兵 | 🔴 高 |

> **「默认 workbuddy 逐字节一致」是本次唯一的强回归保护**：变更前必须先固化基准快照（同一解释器、
> 同一 `FSTDD_OUT`、同一 `FSTDD_SRC`），变更后以哈希/`Compare-Object` 逐字节比对；该用例未通过前
> 不得进入交付。

## 五、建议补充顺序

1. **第一优先（部署前必补）**：TC-MPA-005、TC-MPA-006（逐字节回归）、TC-MPA-001、TC-MPA-002、TC-MPA-004、TC-MPA-008。
2. **第二优先（铺平台时补）**：TC-MPA-003（claude-code 落点/front-matter）、TC-MPA-007（正文同源）、TC-MPA-012（平台感知校验）。
3. **第三优先（端到端收尾）**：TC-MPA-009、TC-MPA-010（入口透传）、TC-MPA-011（缺省校验）。

## 六、证据记录

> 每条引用实测数据的证据必须可定位**观测时刻**与**代码版本**（TC-EPR-002）。

| 证据 | observed_at（带时区） | observed_base_git_sha | 来源 |
|---|---|---|---|
| 仓库 HEAD（当前基线） | 2026-09-30T07:56:18+00:00 | f556899fc17bba1bcbe914c85fe9411a3eb01a72 | `git -C e:/FSTDD/stdd-repo rev-parse HEAD` |
| 变更阶段状态：understand completed / spec pending / current_phase=understand | 2026-09-30T07:56:18+00:00 | f556899fc17bba1bcbe914c85fe9411a3eb01a72 | `python -m fstdd phase status 2026-09-30-multi-platform-adapters` |
| 上游 6 平台适配目录（aider/claude-code/copilot/cursor/trae/workbuddy），claude-code 与 trae 各含 6 个 skill 文件 | 2026-09-30T07:56:18+00:00 | f556899fc17bba1bcbe914c85fe9411a3eb01a72 | `Get-ChildItem -Recurse upstream/.fstdd/platforms` |
| 相关既有测试资产清单与用例数（见 §1.3） | 2026-09-30T07:56:18+00:00 | f556899fc17bba1bcbe914c85fe9411a3eb01a72 | 对 `upstream/tests/` 的 `def test_` 计数与关键字检索 |
| 安装层硬编码现状：`install_workbuddy_skills.py` 无 `--platform`；`_skill_install_env.resolve_skill_dir()` 只解析 WorkBuddy；`install.sh`/`install.ps1` 无平台参数；校验器只认 WorkBuddy | 2026-09-30T07:56:18+00:00 | f556899fc17bba1bcbe914c85fe9411a3eb01a72 | 只读源码审查（`tools/install_workbuddy_skills.py`、`tools/_skill_install_env.py`、`tools/verify_workbuddy_skills.py`、`install.sh`、`install.ps1`） |

- `observed_at` 是**信息采集时刻**，不是文档生成时刻（generated_at 与此无关）。
- 缺 `observed_at` 的证据时效判为「无法判定」（undetermined），**不等同未过期**。