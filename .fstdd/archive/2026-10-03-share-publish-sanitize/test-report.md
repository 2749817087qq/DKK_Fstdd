# 2026-10-03-share-publish-sanitize 测试报告

> 测试日期：2026-10-03
> 测试环境：Windows / Python 3.13（workbuddy default env）/ pytest；ruff·mypy·coverage 未安装
> baseline：066b9f629d21547670a38a375e28e815794e17bd

## 一、总体概况

| 指标 | 数值 |
|------|------|
| 测试用例总数（本变更） | 12 TC / 16 test item |
| 通过 | 16 |
| 失败 | 0 |
| 跳过 | 0 |
| 通过率 | 100% |
| 全量回归（tests/） | 48 passed, 2 skipped in 50.61s |

### 1.1 覆盖率诊断（仅变更文件）

> 环境未安装 `coverage` 模块 → 行/分支覆盖率 **SKIPPED**（非通过/失败门禁）。

| 变更文件 | 行覆盖率 | 状态 |
|----------|----------|------|
| tools/share_experience.py | N/A（coverage 不可用） | ⚪ SKIPPED |
| tests/test_share_publish_sanitize.py | N/A（coverage 不可用） | ⚪ SKIPPED |

替代证据：`pytest --cov` 不可用时，以「12/12 TC 实现覆盖（`fstdd ci check-failures` (g) 项 PASS）」+ `py_compile` 语法校验作为覆盖证据。

## 二、按模块统计

| 测试模块 | 用例数 | 通过 | 失败 | 跳过 | 说明 |
|----------|--------|------|------|------|------|
| tests/test_share_publish_sanitize.py（本变更新增） | 16 | 16 | 0 | 0 | TC-SOS-001..012（002 参数化 4 例；012 拆 2 例） |
| tests/test_finance_content.py | - | - | - | - | 回归基线，无新增失败 |
| tests/test_install_smoke.py | - | - | - | - | 回归基线，无新增失败 |
| tests/test_multi_platform.py | - | - | - | - | 回归基线，无新增失败 |
| 全量 `pytest tests/` | 50 | 48 | 0 | 2 | 2 skipped 为平台/环境不适用项（非本变更引入） |

## 三、E2E 测试结果

> 项目未配置 `quality.e2e.enabled: true`（N/A）。本变更以「silent 入口单元级 E2E」替代：
> `silent_share()` 在 publish 失败与异常两条路径均返回 0 且写审计（TC-SOS-012）。

### 3.2 关键路径结果

| 路径 | 状态 | 失败原因 |
|------|------|----------|
| stage → inbox POST（本地 stub 端点） | ✅ | - |
| stage → scp（可观测桩） | ✅ | - |
| stage → GitHub 直推（git 命令桩 + copy2 spy） | ✅ | - |
| stage → fork+PR（gh_api 桩 + copy2 spy） | ✅ | - |
| silent 入口失败/异常零阻塞 + 留痕 | ✅ | - |

### 3.3 E2E 结论

四条出站通道的「发送/拷贝源 = stage 内容」均已被可观测桩验证；未触达真实服务器/GitHub（离线可重复）。

## 四、失败项详细分析

无本变更引入的失败项。

### 4.1 基线既存焦点（已核）

- **`fstdd ci check-failures` 项 (d)「重复 TC-ID」** — `TC-SOS-001/002/003/005/008/009/012`
  被判重复。人工核对 `test-plan.md`：每个 TC-ID 仅有 1 处**定义**（案例表 ID 行），
  其余出现均为**引用**（覆盖矩阵 `TC-SOS-001..007`、优先级清单 `TC-SOS-001、TC-SOS-002、TC-SOS-008`）。
  → 判定为**文本扫描假阳性**，命中既有经验 **EXP-2026-0016**。非真实重复。

## 五、功能/测试覆盖对照

| 功能模块 | 涉及源码 | 已有测试覆盖 | 缺失测试 |
|----------|----------|-------------|----------|
| 出站强制脱敏 stage_sanitized | tools/share_experience.py:461-497 | TC-SOS-001..005 | 无 |
| 出站残余自检 OUTBOUND_RESIDUAL_RE | tools/share_experience.py:165-178 | TC-SOS-006..007 | 无 |
| inbox 收口 | publish_via_inbox:663-669 | TC-SOS-008 | 无 |
| scp 收口 | publish_via_scp:593-601 | TC-SOS-009 | 无 |
| GitHub 直推收口 | publish():904-946 | TC-SOS-010 | 无 |
| fork+PR 收口 | publish_via_pr:768-774 | TC-SOS-011 | 无 |
| 零阻塞 + 审计留痕 | silent_share / record_audit | TC-SOS-012 | 无 |

## 五-B、多路并行 Review 结果

> C1 执行，3 代理并行审查（代码 / 测试 / 文档）

### Review 迭代历史

| 轮次 | C | H | M | L | 状态 |
|------|---|---|---|---|------|
| 1 | 0 | 0 | 0 | 1 | 通过 |

### 最终 Review 汇总

| 维度 | Critical | High | Medium | Low | 总计 |
|------|----------|------|--------|-----|------|
| 代码质量 | 0 | 0 | 0 | 0 | 0 |
| 测试/配置 | 0 | 0 | 0 | 0 | 0 |
| 文档/Skills | 0 | 0 | 0 | 1 | 1 |

### Review 已修复问题

| # | 严重性 | 文件 | 问题 | 状态 |
|---|--------|------|------|------|
| 1 | M | tests/test_share_publish_sanitize.py:221 | git 子命令伪造按 `cmd[1]` 判定，漏判 `git -c ... commit` 导致捕获为空 | ✅ 已修复（改为扫描 `cmd[1:]` 关键字） |
| 2 | H | .fstdd/experiences/.experience-index.yaml:246 | 编辑索引时 `low:` 缩进被改坏 → YAML 解析失败 | ✅ 已修复（恢复 2 空格缩进并校验通过） |

### Review 已知限制（未修复的低优先级问题）

| # | 严重性 | 文件 | 问题 |
|---|--------|------|------|
| 1 | L | design.md（L25-32 表格） | `publish_via_inbox L630-632` 等行号引用在实现后已偏移（文档漂移，非语义错误），DELIVER 阶段修正 |

## 六、设计调整说明

本变更 **无设计偏离**（design-adjustments count = 0）。
实现与 `design.md` 的 5 项 Decisions 逐项一致：收口点置于每个发送函数入口、残余自检常量、
`--no-sanitize` 对出站无效、frontmatter 改写 `sanitized: true`、临时目录 `finally` 清理。
唯一「澄清」（非偏离）：proposal 所称「三条出站路径」在 design 中确认为 **4 个拷贝点**（含 fork+PR 兜底）。

## 七、修复确认记录

| 问题 | 修复文件 | 状态 |
|------|----------|------|
| git 子命令伪造漏判 `-c` 前缀 → 捕获为空 | tests/test_share_publish_sanitize.py | ✅ 已修复 |
| 经验索引 `low:` 缩进被改坏 | .fstdd/experiences/.experience-index.yaml | ✅ 已修复 |
| verify_notices 误隔离 change 文档 | .fstdd/changes/.../design.md、proposal.md、test-plan.md | ✅ 已恢复并删除 .json 侧车 |

## 七-B、经验库更新

### 本次新增经验

| 经验ID | 类别 | 模式 | 严重程度 | 发现阶段 |
|--------|------|------|---------|---------|
| EXP-2026-0017 | security | 出站路径未统一收口：脱敏在上游、发送在下游直读源目录 | high | BUILD |

### 本次命中已有经验（复用）

| 经验ID | 类别 | 模式 | 命中阶段 |
|--------|------|------|---------|
| EXP-2026-0016 | tool_misuse | `ci check-failures` TC-ID 重复判定文本扫描假阳性 | BUILD |
| EXP-2026-0015 | tool_misuse | verify_notices 误隔离合法文档（本次复发，occurrences 1→2） | BUILD |
| FSTDD005-EXP-20260918-C1 | operations | 静默失败 exit 0 无消费者 → 失败必须留痕 | BUILD |
| FSTDD005-EXP-20260918-C4 | testing | 第二道防线天然不可观测 → 直接断言判据常量 | BUILD |
| FSTDD005-EXP-20260918-C5 | design | 收紧误伤 → 复用同源 sanitize + 保持宁漏勿误 | BUILD |
| FSTDD005-EXP-20260918-C6 | security | 凭证外泄 | BUILD |
| EXP-2026-0013 | contract_gap | 声明/实现不一致 → 参数化断言 | BUILD |

### 经验统计

| 指标 | 数值 |
|------|------|
| 本次新增 | 1 条 |
| 本次复用 | 7 条 |
| 经验库总计 | 68 条 |

## 八、C4 失败模式检查（23 类，全量）

| # | 失败模式 | 结果 | 证据 / 处置 |
|---|----------|------|-------------|
| 1 | 幻觉调用 | ✅ | py_compile 通过；新增代码仅调用 sanitize/export_files/record_audit/_now/tempfile/shutil/re 等已定义符号 |
| 2 | 过度信任 LLM | ✅ | 每步工具结果二次核对；覆盖率/lint 不可用如实标 SKIPPED，未编造数值 |
| 3 | Prompt 注入 | ✅ | 新增文本无 `ignore previous`/`you are now` 等注入痕迹 |
| 4 | 记忆污染 | ✅ | 经验库仅作检查清单，未把旧结论当事实注入 |
| 5 | 上下文窗溢出 | ✅ | 单次 edit 均 < 300 行，改动分块 |
| 6 | 工具参数漂移 | ✅ | 仅用标准库/既有函数；CLI 调用先查用法（`verify_notices` 缺参报错后即补 directory） |
| 7 | 安全凭证泄露 | ✅ | 代码无 token/key 硬编码（仅正则模式字面量）；verify_notices 已运行（真实凭证未命中；误隔离合法文档已恢复）；收口本身即本变更目标 |
| 8 | 权限绕过 | ✅ | 未手改 .fstdd.yaml 确认字段；Gate1/2 记 dialog+原文，Gate3 待用户确认 |
| 9 | 并发竞态 | ✅ | 无并发；staged 目录 mkdtemp 唯一 |
| 10 | 路径遍历 | ✅ | 仅遍历 out_dir 下 export_files；临时目录为系统 temp；无 `../` 逃逸 |
| 11 | 跨会话残留 | ✅ | staged 目录 `finally` + rmtree 清理；测试用 tmp_path；无 .tmp/.scratch 残留 |
| 12 | 输出截断 | ✅ | 无大 payload hook；命令输出完整 |
| 13 | 格式错误 | ✅ | canonical YAML 合法；py_compile 通过；经验索引 YAML safe_load 通过 |
| 14 | 循环依赖 | ✅ | wrapper → internal 单向，无环 |
| 15 | 重复扣款 | N/A | 非金融扣款场景 |
| 16 | 账实不符 | N/A | 无账本/对账 |
| 17 | 静默降级 | ✅ | 出站失败保持 exit 0 但写 .fstdd/share-audit.yaml（EXP-C1）；stage 剔除条目显式 skipped |
| 18 | 精度丢失 | N/A | 无金额计算 |
| 19 | 审计缺口 | ✅ | stage 剔除与发送失败均写审计（time/id/target/result/reason，reason 先脱敏） |
| 20 | 状态机漏洞 | N/A | 无状态机 |
| 21 | 额度穿透 | N/A | 无限额 |
| 22 | 合规遗漏 | ✅ | 敏感数据脱敏在出站侧收口（本变更核心） |
| 23 | 过度工程 | ✅ | YAGNI-7：①真需要（出站必脱敏）②本仓已有（复用 sanitize，不重写）③标准库（tempfile/shutil）④⑤无新依赖 ⑥⑦最小实现（1 常量 + 1 函数 + 3 wrapper） |

**统计**：23 类全量执行 → ✅ 18 / N/A 5（金融红线不适用） / ❌ 0 / SKIPPED 0。

## 九、结论

**可进入 Gate 3。** 四条出站通道已统一收口到 `stage_sanitized()`，12/12 TC 全绿，全量回归无新增失败，
23 类失败模式全量检查无 ❌。

风险等级：**低**。潜在遗留：
- 环境缺 `coverage`/`ruff`/`mypy` → 覆盖率与 lint 检查 SKIPPED（非本变更加入，DELIVER 可评估补装）。
- design.md 行号引用漂移（L1）→ DELIVER 阶段修正。
- staged 目录在 scp 失败降级到 GitHub/inbox 时会重复 stage（可接受，换来「每个出口自收口」的旁路免疫）。

### 9.1 质量信号汇总

| 信号源 | 状态 | 备注 |
|--------|------|------|
| 单元/集成测试 | ✅ | 本变更 100%；全量 48 passed / 2 skipped |
| E2E 测试 | ✅（单元级替代） | 4 通道 stub 验证 |
| Lint | ⚪ SKIPPED | ruff 未安装 |
| 类型检查 | ⚪ SKIPPED | mypy 未安装 |
| 多版本测试 | N/A | 无多版本矩阵 |
| 覆盖率 | ⚪ SKIPPED | coverage 未安装（替代证据：12/12 TC 实现覆盖） |
| 23 类失败模式 | ✅ | 18 ✅ / 5 N/A / 0 ❌ |