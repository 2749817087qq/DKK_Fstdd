# FSTDD × 金融：修复 fstdd-fin 资产 + 核心四阶段融合 — 测试方案

> 版本：v1.0 | 创建日期：2026-10-03 | 对应 Phase 2 Spec：4 个 capability spec.yaml

## 一、测试策略

### 1.1 测试类型

纯 skill + 配置层变更，零代码。测试 = 存在性验证 + 内容匹配 + 格式合规 + 回归验证。

### 1.2 测试原则

- **存在性优先**：每个 success criterion 都有对应的文件/段落存在
- **内容精确匹配**：关键字段 sha256 匹配、条目数匹配
- **格式合规**：YAML 合法、skill 格式符合模板
- **回归验证**：非金融项目四阶段流程无变化

## 二、详细测试案例

### Capability 1: fstdd-fin-skill-registration

#### TC-REG-001 — SKILL.md 存在且内容匹配

| 字段 | 内容 |
|------|------|
| **ID** | TC-REG-001 |
| **对应 Spec** | fstdd-fin-skill-registration.yaml → REQ-001 SC-001 |
| **优先级** | P0 |
| **预置条件** | `_scratch/stdd-dev/stdd-repo/skills/fstdd-fin/SKILL.md` 存在 |
| **输入** | 执行复制 + 比对 |
| **预期结果** | `skills/fstdd-fin/SKILL.md` 存在，sha256 与源文件一致 |

#### TC-REG-002 — install_workbuddy_skills.py 包含 fstdd-fin

| 字段 | 内容 |
|------|------|
| **ID** | TC-REG-002 |
| **对应 Spec** | REQ-002 SC-002 |
| **优先级** | P0 |
| **预置条件** | install_workbuddy_skills.py 存在 |
| **输入** | Select-String "fintech\|fstdd-fin" |
| **预期结果** | 至少 2 处命中（source 路径声明 + install 输出循环） |

#### TC-REG-003 — platforms.yaml 注册 fstdd-fin

| 字段 | 内容 |
|------|------|
| **ID** | TC-REG-003 |
| **对应 Spec** | REQ-003 SC-003 |
| **优先级** | P0 |
| **预置条件** | platforms.yaml 当前 6 个 skill |
| **输入** | Select-String "fstdd-fin" + Get-Content 数条目 |
| **预期结果** | fstdd-fin 条目存在，总 skill 数 ≥ 7 |

### Capability 2: understand-phase-finance-redlines

#### TC-RED-001 — understand.md 含金融判定钩子

| 字段 | 内容 |
|------|------|
| **ID** | TC-RED-001 |
| **对应 Spec** | REQ-010 SC-010 |
| **优先级** | P0 |
| **预置条件** | `.fstdd/skills/understand.md` 存在 |
| **输入** | Select-String "金融系统前置检查\|FINANCIAL_PROJECT" |
| **预期结果** | 命中，且包含关键词白名单（支付/银行/交易 等） |

#### TC-RED-002 — understand.md 含 7 红线检查

| 字段 | 内容 |
|------|------|
| **ID** | TC-RED-002 |
| **对应 Spec** | REQ-011 SC-011 |
| **优先级** | P0 |
| **输入** | Select-String "7.*红线\|交易准确性\|幂等性\|审计.*篡改\|账实相符" |
| **预期结果** | 命中 ≥ 3 条红线关键词 |

#### TC-RED-003 — 非金融项目无强制钩子

| 字段 | 内容 |
|------|------|
| **ID** | TC-RED-003 |
| **对应 Spec** | REQ-012 SC-012 |
| **优先级** | P1（回归） |
| **输入** | 模拟非金融需求 → 关键词匹配不命中 |
| **预期结果** | Agent 不被要求做额外金融检查 |

### Capability 3: build-phase-finance-test-dimensions

#### TC-BLD-001 — build.md 含 10 维金融测试

| 字段 | 内容 |
|------|------|
| **ID** | TC-BLD-001 |
| **对应 Spec** | REQ-020 SC-020 |
| **优先级** | P0 |
| **预置条件** | `.fstdd/skills/build.md` 存在 |
| **输入** | Select-String "金融.*测试\|幂等.*测试\|Decimal.*精度" |
| **预期结果** | 命中 10 维测试维度提示 |

#### TC-BLD-002 — 非金融项目 BUILD 无金融测试

| 字段 | 内容 |
|------|------|
| **ID** | TC-BLD-002 |
| **对应 Spec** | REQ-021 SC-021 |
| **优先级** | P1（回归） |
| **预期结果** | FINANCIAL_PROJECT=NO 时不触发 10 维测试 |

### Capability 4: finance-quality-failure-modes

#### TC-QFM-001 — quality.yaml 含 8 类金融失败模式

| 字段 | 内容 |
|------|------|
| **ID** | TC-QFM-001 |
| **对应 Spec** | REQ-030 SC-030 |
| **优先级** | P0 |
| **预置条件** | `.fstdd/config.d/quality.yaml` 存在 |
| **输入** | Select-String "重复扣款\|账实不符\|静默降级\|精度丢失\|审计缺口\|状态机漏洞\|额度穿透\|合规遗漏" |
| **预期结果** | 8 类全部命中，每类有 failure_pattern + detection_trigger + fix_template |

#### TC-QFM-002 — 原有 14 类失败模式不变

| 字段 | 内容 |
|------|------|
| **ID** | TC-QFM-002 |
| **对应 Spec** | REQ-031 SC-031 |
| **优先级** | P0 |
| **输入** | 追加前后 sha256 比对（排除追加部分） |
| **预期结果** | 原有 14 类条目一字不改 |

## 三、测试执行矩阵

| 模块 | 单元（存在性） | 内容匹配 | 格式合规 | 回归 | 状态 |
|------|-------------|---------|---------|------|------|
| C1 SKILL.md 资产回归 | ✅ TC-REG-001 | ✅ sha256 | ✅ | — | 待执行 |
| C2 安装脚本 | ✅ TC-REG-002 | ✅ hits | ✅ Python 语法 | — | 待执行 |
| C3 understand.md | ✅ TC-RED-001/002 | ✅ 关键词数 | ✅ Markdown | ✅ TC-RED-003 | 待执行 |
| C4 build.md | ✅ TC-BLD-001 | ✅ 10 维命中 | ✅ | ✅ TC-BLD-002 | 待执行 |
| C5 quality.yaml | ✅ TC-QFM-001 | ✅ 8 类全命中 | ✅ YAML parse | ✅ TC-QFM-002 | 待执行 |
| C6 platforms.yaml | ✅ TC-REG-003 | ✅ 条目数 | ✅ YAML parse | — | 待执行 |

## 四、回归风险矩阵

| 风险区域 | 改动 | 已有回归保护 | 风险等级 | 缓解 |
|---------|------|------------|---------|------|
| 非金融项目 understand 被误触发 | 关键词判定逻辑 | —（需手动验证） | 中 | 白名单 35+ 专业词，不用泛词 |
| 非金融项目 BUILD 被误触发 | 同上 | — | 中 | 同上 |
| quality.yaml schema 破坏 | 追加 8 类 | fstdd validate | 低 | append-only，不改 14 类 |
| install_workbuddy_skills.py 路径错 | 追加 source 路径 | — | 低 | 安装后验证文件存在 |

## 五、建议补充顺序

P0 → C1（资产回归） → C6（platforms） → C2（install） → C5（quality.yaml） → C3（understand） → C4（build）

逻辑：先让资产存在 + 注册，再插流程钩子。
