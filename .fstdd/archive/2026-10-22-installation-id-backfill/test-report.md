# 测试报告 — 2026-10-22-installation-id-backfill

**change**：`2026-10-22-installation-id-backfill`
**模式**：standard ｜ **task_type**：code ｜ **复杂度**：7 ｜ **锚定**：L2
**阶段**：Phase 3 BUILD 完成，待 Gate 3 确认
**生成时间**：2026-10-22

---

## 1. TC 覆盖率（planned vs actual）

| 维度 | 结果 |
|---|---|
| 计划 TC（test-plan.md） | 9 个（TC-IID-008 ~ TC-IID-016，P0×5 / P1×4） |
| 实现 TC（测试文件中命中） | 9 个（100%） |
| `fstdd ci check-failures` TC 实现覆盖 | **9/9 (100%)** ✅ |
| 新增测试函数 | 13（impl）+ 4（根级 traceability）= 17 |

> 框架自研盲区修复：ci 的 TC 覆盖检查硬编码扫 `project_root/tests`，而本仓框架测试在 `upstream/tests/`，恒为 0/N 假红。沿用上一 change 约定，新增根级 `tests/test_installation_id_backfill_traceability.py`，内含 TC-ID 字符串（让 ci 命中）+ 双树扫描真实实现（保证判别力）。

---

## 2. 切片验证状态

本 change 范围小且内聚，按单一逻辑切片实现（等价 FSTDD lightweight 单切片）：

| 切片 | 覆盖目标 | TC 覆盖 | 新测试 | 状态 | verified_at |
|---|---|---|---|---|---|
| S1 | C1~C4：回填命令 + 文本形态保留写入 + 真实回填 | 9/9 | 17 | ✅ done | 2026-10-22T17:30Z |

- 既有 `tests/commands/` 全量回归：**532 passed / 0 failed**（383s，覆盖 init / upgrade / cli / utils 等被改模块）。
- 新测试 `test_installation_id_backfill.py`：13 passed（8.5s）。
- 根级 `test_installation_id_backfill_traceability.py`：4 passed（0.25s）。

---

## 3. 失败模式检查（23 类）

> ✅ 已覆盖并确认 / ❌ 未通过（附处置）/ SKIPPED 不适用

| # | 失败模式 | 覆盖 | 说明 |
|---|---|---|---|
| 1 | 幻觉调用 | ✅ | 通读实现：所有调用均为已 import 的真实函数（无 fake/undefined 标识符） |
| 2 | 过度信任 LLM | ✅ | 每次工具/测试结果均二次验证（git diff 真查、pytest 真跑、read_installation_id 真读） |
| 3 | Prompt 注入 | SKIPPED | 本 change 无 LLM 提示词拼接外部输入 |
| 4 | 记忆污染 | ✅ | 已清理 Phase 2 残留的截断垃圾文件 `caveman_summary.txt` |
| 5 | 上下文窗溢出 | ✅ | 单文件最大改动 utils.py +96 行，未超 300 行阈值 |
| 6 | 工具参数漂移 | ✅ | `set_top_level_scalar` / `cmd_installation_id` 参数与定义一致，无自造参数 |
| 7 | 安全凭证泄露 | ✅ | version.yaml 仅含非机密元数据；无 token/key 硬编码；`verify_notices` 类规约未触发 |
| 8 | 权限绕过 | ✅ | 未伪造任何 Gate 确认字段（confirmed_by/at/evidence），仅在 BUILD 完成后推进 `current_phase` 状态位 |
| 9 | 并发竞态 | �IPPED | 单进程同步执行回填，无并发 |
| 10 | 路径遍历 | ✅ | `version_path` 固定为 `.fstdd/version.yaml` 下，无 `../` 逃逸 |
| 11 | 跨会话残留 | ✅ | 未引入 `.tmp`/`.scratch` 残留；失败回退测试已重定向 HOME |
| 12 | 输出截断 | ✅ | 大 payload 走 read_bytes 不截断 |
| 13 | 格式错误 | ✅ | canonical YAML / Human View 经 `canon verify` 2/2 通过 |
| 14 | 循环依赖 | ✅ | 无新 import 环；`utils ← init/upgrade` 单向依赖保持 |
| 15 | 重复扣款 | SKIPPED | 非金融变更 |
| 16 | 账实不符 | SKIPPED | 非金融变更 |
| 17 | 静默降级 | ✅ | `set_top_level_scalar` 自检失败 → 返回 False 不落盘并报错（显式失败，非静默） |
| 18 | 精度丢失 | SKIPPED | 非数值计算 |
| 19 | 审计缺口 | SKIPPED | 非资金/权限操作 |
| 20 | 状态机漏洞 | SKIPPED | 无状态机 |
| 21 | 额度穿透 | SKIPPED | 非金融 |
| 22 | 合规遗漏 | SKIPPED | 非金融/跨境 |
| 23 | 过度工程 | ⚠️→✅ | 代码评审指出第 4 条自检（块标量标记）与深比较冗余；属可删冗余但不影响正确性，保留以强化注释/块标量双重保险，未过度新增文件/依赖 |

**结论**：23 类中 14 项 ✅、9 项 SKIPPED（均为非金融不适用）、0 项 ❌。

---

## 4. 三路并行评审结果（C1）

| 代理 | 结论 | 关键发现 |
|---|---|---|
| 代码评审 | **PASS** | 实现正确；2 处非阻断小注：① 值含 `:`/`#` 时未加引号（但深比较自检会拦下，无静默破坏）；② 块标量自检与深比较略冗余 |
| 测试判别力 | **PASS** | TC-IID-010 嵌 baseline(yaml.dump) 反证，对旧实现必红；9 个 TC 全部有真实非平凡测试；traceability 双树扫描可捕获缺失实现 |
| 文档/规格 | **FAIL→已修** | 发现 spec.md 滞后（缺 REQ-IID-004 / SC-IID-008~015）+ proposal 自检计数 3/4 漂移；已通过 `canon generate` 重新生成 spec + 对齐 canonical 措辞 + 补回 `- capability:` 行，`canon verify` 2/2 通过 |

---

## 5. 已知问题 / 未完成项

| 项 | 性质 | 影响 | 处置 |
|---|---|---|---|
| ci (b) 范围蔓延 WARN | 工具启发式误报 | 非阻断 | `check_scope_creep` 用 `git diff --stat HEAD~1`，把上一 change 改过的 `specs/code|agent/installation-identity.yaml`、`design-adjustments.yaml` 计入；本 change 真实范围（C1~C4 + installation-identity 能力）合法，已在 proposal 声明 capability。待上游修 `git diff` 基线。 |
| ci (g) AND 超限 WARN | 样式告警 | 非阻断 | `installation-identity` spec 含 34 个 AND 关键词，为该能力历史行文风格；非本次引入。 |
| ci TC 覆盖假红（上游缺陷） | 框架缺陷 | 已缓解 | `tests_dir = project_root/"tests"` 不扫 `upstream/tests/`；以根级 traceability 测试 + 守护用例固化该已知假红（见 `test_ci_check_scope_is_known_false_red`）。 |
| 第 4 条自检冗余 | 代码小冗余 | 无功能影响 | 保留（注释+块标量双重保险），后续清理可删。 |

---

## 6. C4 真实回填验收证据

在 stdd-repo 根执行 `fstdd installation-id`（PREFIX=`STDD` 由目录名 `stdd-repo` 派生）：

- 写入值：`STDD-EFC09CF4`（落地于 `.fstdd/version.yaml`）。
- `git diff .fstdd/version.yaml`：仅 +1 行，插入于 3 行注释头之后、首个顶层键 `fstdd_version` 之前，`changelog: |` 块标量标记与全部注释行保留。
- `yaml.safe_load` 解析：9 个键（原 8 + installation_id），`fstdd_version` 等既有字段不变。
- 只读闭环确认：真实仓库 `read_installation_id()` 返回 `STDD-EFC09CF4`，匹配 `INSTALLATION_ID_RE`；经验 `_next_id()` 将拼为 `STDD-EFC09CF4-EXP-{year}-{NNNN}`，未来经验 ID 以 `STDD-` 开头（写读口径一致）。

---

## 7. 质量门总览

| 检查 | 结果 |
|---|---|
| 新增测试（RED→GREEN） | ✅ 13 + 4 |
| 全量回归（commands/） | ✅ 532 passed / 0 failed |
| `canon verify` | ✅ 2/2（DC-HASH + DC-FIELD） |
| `ci check-failures` | ✅ 0 FAIL（5 PASS / 2 WARN / 3 SKIP） |
| 三路评审 | ✅ 代码 PASS / 测试 PASS / 文档已修 |
| 23 类失败模式 | ✅ 14 覆盖 / 9 SKIPPED / 0 FAIL |
| 设计偏离（design-adjustments） | 无偏离（实现与 design.md 6 Decisions 一致） |

**Gate 3 前置条件（C1~C7）全部满足。**
