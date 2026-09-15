# EOL 治理 测试方案与详细案例

> 版本：1.0
> 创建日期：2026-09-15
> 对应 Phase 2 Spec：`canonical/specs/code/2026-09-15-crlf-eol-governance.yaml`（capability: eol-governance）

## 一、测试策略

### 1.1 测试金字塔

本变更为**仓库配置治理**，无应用代码，因此金字塔结构特殊：

- **单元层（无）**：不涉及函数级逻辑。
- **集成层（主体，7 例）**：以 Git 命令与文件状态为被测对象，验证规则声明与行尾状态一致性。
- **E2E 层（1 例）**：以「干净仓库复现 640 行告警」为基准场景，验证告警从 640 → 0。

### 1.2 测试原则

- **对照优先**：每条断言都设「无规则时」的实测对照值，避免"0 告警"因本身就无告警而假通过。
- **状态可复现**：所有断言基于 `git ls-files --eol` 的结构化输出，不依赖人眼观察。
- **拦截反向误用**：明确断言 `i/crlf` 数为 0，用于拦截 `* -text` 类规则误用（该误用实测会产生 4 个 `i/crlf`）。
- **零内容变更**：断言索引 diff 为 0，确保治理不改变任何文件实质内容。

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|----------|--------|------|----------|
| 无 | 0 | — | 本仓库此前无任何自动化测试资产 |

> 本变更的测试以一次性验证脚本形式执行（Phase 3 落地），后续建议沉淀为 `tools/verify_eol.sh`。

## 二、详细测试案例

### 功能 1：EOL 规则声明

#### 案例 1.1 — 根目录 .gitattributes 规则正确

| 字段 | 内容 |
|------|------|
| **ID** | TC-EOL-001 |
| **对应 Spec** | eol-governance → Scenario: SC-001 |
| **优先级** | P0 |
| **预置条件** | 已 clone 的 stdd-repo 工作副本 |
| **输入** | 读取仓库根 `.gitattributes` |
| **预期结果** | 文件 SHALL 存在，内容 SHALL 为 `* text=auto eol=lf`；规则 SHALL 覆盖 `upstream/`；`.git/info/attributes` SHALL 不存在 |
| **当前状态** | ❌ 测试缺（Phase 3 补） |

#### 案例 1.2 — 批量 add 无 CRLF 告警

| 字段 | 内容 |
|------|------|
| **ID** | TC-EOL-002 |
| **对应 Spec** | eol-governance → Scenario: SC-002 |
| **优先级** | P0 |
| **预置条件** | 干净临时仓库，`core.autocrlf=true`，670 个 LF 文件 |
| **输入** | 执行 `git add -A` |
| **预期结果** | `LF will be replaced by CRLF` 告警行数 SHALL 为 0（对照：无规则时实测 640 行 / 96,880 B） |
| **当前状态** | ❌ 测试缺（Phase 3 补） |

### 功能 2：行尾状态一致性

#### 案例 2.1 — 混合态文件清零

| 字段 | 内容 |
|------|------|
| **ID** | TC-EOL-003 |
| **对应 Spec** | eol-governance → Scenario: SC-003 |
| **优先级** | P0 |
| **预置条件** | 已应用规则并完成工作区重建 |
| **输入** | `git ls-files --eol`，统计 `i/lf` 且 `w/crlf` 的文件 |
| **预期结果** | 混合态文件数 SHALL 为 0（修复前实测 4：`docs/WORKBUDDY_INSTALL_NOTES.md`、`skills/stdd-fin/SKILL.md`、`tools/verify_workbuddy_skills.py`、`upstream/.gitignore`） |
| **当前状态** | ❌ 测试缺（Phase 3 补） |

#### 案例 2.2 — 索引无 CRLF 项

| 字段 | 内容 |
|------|------|
| **ID** | TC-EOL-004 |
| **对应 Spec** | eol-governance → Scenario: SC-004 |
| **优先级** | P0 |
| **预置条件** | 已完成本变更 |
| **输入** | `git ls-files --eol`，统计 `i/crlf` 项 |
| **预期结果** | `i/crlf` 文件数 SHALL 为 0（拦截规则误用） |
| **当前状态** | ❌ 测试缺（Phase 3 补） |

#### 案例 2.3 — 索引零内容变更

| 字段 | 内容 |
|------|------|
| **ID** | TC-EOL-005 |
| **对应 Spec** | eol-governance → Scenario: SC-005 |
| **优先级** | P0 |
| **预置条件** | 执行 `git add --renormalize .` 之后 |
| **输入** | `git diff --cached --stat` |
| **预期结果** | 变更文件数 SHALL 为 0（证明仅归一工作区行尾） |
| **当前状态** | ❌ 测试缺（Phase 3 补） |

### 功能 3：脚本可执行性

#### 案例 3.1 — CLI 脚本保持 LF 且可运行

| 字段 | 内容 |
|------|------|
| **ID** | TC-EOL-006 |
| **对应 Spec** | eol-governance → Scenario: SC-006 |
| **优先级** | P0 |
| **预置条件** | 已完成本变更，`upstream/bin/stdd` 已检出 |
| **输入** | 检查行尾；执行 `stdd init` / `new` / `status` |
| **预期结果** | 行尾 SHALL 为 LF（不含 `\r`），shebang SHALL 不以 `\r` 结尾；三个子命令 SHALL 均正常返回 |
| **当前状态** | ❌ 测试缺（Phase 3 补） |

### 功能 4：文档可维护性

#### 案例 4.1 — README 故障排除含 EOL 说明

| 字段 | 内容 |
|------|------|
| **ID** | TC-EOL-007 |
| **对应 Spec** | eol-governance → Scenario: SC-007 |
| **优先级** | P1 |
| **预置条件** | 已完成本变更 |
| **输入** | 查看 README「故障排除」章节 |
| **预期结果** | SHALL 包含 `.gitattributes` 作用说明与批量 add 建议做法 |
| **当前状态** | ❌ 测试缺（Phase 3 补） |

## 三、测试执行矩阵

| 功能模块 | 单元 | 集成 | E2E | 状态 |
|----------|------|------|-----|------|
| EOL 规则声明 | — | TC-EOL-001 | TC-EOL-002 | 🔴 |
| 行尾状态一致性 | — | TC-EOL-003/004/005 | — | 🔴 |
| 脚本可执行性 | — | TC-EOL-006 | — | 🔴 |
| 文档可维护性 | — | TC-EOL-007 | — | 🔴 |

## 四、回归风险矩阵

| 风险区域 | 本变更改动 | 已有回归保护 | 风险等级 |
|----------|-----------|-------------|---------|
| 索引行尾翻转（`* -text` 误用） | 规则由 `* -text` 修正为 `text=auto eol=lf` | TC-EOL-004 断言 `i/crlf` = 0 | 🟢 |
| 文件内容被改写 | `rm + checkout` 重建 4 个文件 | TC-EOL-005 断言 diff = 0 | 🟢 |
| 脚本 shebang 破坏 | 全库统一 LF | TC-EOL-006 断言 LF + CLI 冒烟 | 🟢 |
| 二进制文件被误判 | `text=auto` 自动判别 | 实测 31 个 `i/none` 未受影响 | 🟢 |
| 其他项目受全局配置影响 | 不改 `core.autocrlf` | 仅仓库级 `.gitattributes` | 🟢 |

## 五、建议补充顺序

1. **第一优先（Phase 3 必执行）**：TC-EOL-001 ~ TC-EOL-006（全部 P0）
2. **第二优先（同批次完成）**：TC-EOL-007（P1，文档）
3. **第三优先（后续沉淀）**：将 7 个案例固化为 `tools/verify_eol.sh`，纳入日常校验
