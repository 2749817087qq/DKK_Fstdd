# Phase 3 BUILD 测试报告

> Change: `2026-10-26-experience-lib-triage`
> 版本: v3.4.0 增量修复
> 观测时刻: 2026-10-26T14:12:42+08:00
> 基线 SHA: 2096839

## 一、变更范围

### 已完成修复（3 项）

| EXP-ID | 类别 | 修复点 | 涉及文件 |
|--------|------|--------|---------|
| EXP-2026-0062 | data-integrity | 关键写入点 fsync 原子落盘 | `fstdd/cli/commands/experience.py` (`_save_index` + `_atomic_write_text` helper)、`fstdd/cli/commands/knowledge.py` (`_save_graph`) |
| EXP-2026-0055 | data-integrity | 知识图谱 edges 幂等去重 | `fstdd/cli/commands/knowledge.py` (`_dedupe_edges` helper) |
| EXP-2026-0067 | tooling | `ci check-failures` 的 TC planned 只按定义点提取 | `fstdd/cli/commands/ci.py` (`check_tc_implementation_coverage`) |

### 未处理（后续迭代输入）

| EXP-ID | 原因 | 后续建议 |
|--------|------|---------|
| EXP-2026-0018 | phase advance 缺 `_index_lock` 保护，涉及架构改动 | 需单独 change + 设计讨论锁粒度 |
| EXP-2026-0044 | `yaml.dump` 破坏手写 YAML 注释 | 需引入 `ruamel.yaml` 或改保守合并策略 |
| EXP-2026-0045 | yaml 序列化路径相关问题（与 EXP-0044 同源） | 与 EXP-0044 一起处理 |
| EXP-2026-0067 剩余 | scope creep 对 canon proposal SKIP；锚定检查只认仓库根 | 需先明确 canonical proposal 渲染规则 |

## 二、测试结果

### 2.1 单元测试（pytest）

| 指标 | 数值 |
|------|------|
| 测试文件 | `tests/test_experience_lib_fixes.py` |
| 用例总数 | 11 |
| 通过 | 11 (100%) |
| 失败 | 0 |
| 执行时间 | 66.23s |
| Python | 3.13.12 |
| pytest | 9.1.1 |

### 2.2 TDD 用例与 TC-ID 对应表

| TC-ID | 用例 | 类型 | 状态 |
|-------|------|------|------|
| TC-ELT-001 | `test_save_index_calls_fsync` | 正常路径 | ✅ |
| TC-ELT-002 | `test_save_index_atomic_replace_used` | 边界（原子替换） | ✅ |
| TC-ELT-003 | `test_save_graph_calls_fsync` | 回归（fsync） | ✅ |
| TC-ELT-004 | `test_atomic_write_text_helper` | 回归（新 helper） | ✅ |
| TC-ELT-005 | `test_dedupe_drops_duplicates` | 正常路径（同向去重） | ✅ |
| TC-ELT-006 | `test_dedupe_undirected` | 边界（无向边） | ✅ |
| TC-ELT-007 | `test_dedupe_ignores_self_loops` | 边界（非法边） | ✅ |
| TC-ELT-008 | `test_save_graph_dedupes_on_write` | 回归（落盘去重） | ✅ |
| TC-ELT-009 | `test_extract_form_a_definitions` | 正常路径（定义点） | ✅ |
| TC-ELT-010 | `test_extract_returns_empty_when_no_tables` | 边界（裸文本） | ✅ |
| TC-ELT-011 | `test_check_coverage_excludes_references` | 回归（引用不算 planned） | ✅ |

## 三、门禁检查（`ci check-failures`）

| 检查项 | 结果 |
|--------|------|
| (a) 必需文件存在 | ✅ PASS |
| (b) proposal capability 声明 | ⏭ SKIP（proposal 未声明 capability 列表） |
| (d) TC-ID 唯一（按定义点） | ✅ PASS（11 个） |
| (f) THEN 含 SHALL | ✅ PASS |
| (g) AND 数量 | ⚠ WARN（spec.md AND 数量 12，不阻塞） |
| (j) coverage 覆盖 | ⏭ SKIP（无 coverage.json） |
| (k) capability 契约 | ⏭ SKIP（少于 2 个 capability） |
| (l) canonical proposal 锚定 | ⏭ SKIP |
| TC 实现覆盖 | ✅ PASS（11/11 = 100%） |
| 切片完成记录 | ⏭ SKIP（已 record-slice S1） |

**总计**：3 PASS / 1 WARN / 5 SKIP / **0 FAIL**

## 四、已知限制与风险

1. **Windows 目录 fsync 降级**：`os.open(dir, O_RDONLY)` 在 Windows 上抛 `PermissionError`，目录 fsync 静默降级。文件 fsync 已保证，目录 fsync 是可选项（Linux/macOS 上生效）。测试注释已明示。
2. **`test_check_coverage_excludes_references` 用例的 tests_dir 假设**：`check_tc_implementation_coverage` 只扫描 `project_root/tests/`，测试用例通过构造 `tmp_path/tests/` 目录验证。实际生产路径的 tests 目录结构需符合 FSTDD 约定。
3. **未处理项的下游影响**：EXP-0018（phase advance 缺锁）与 EXP-0044/0045（YAML 注释破坏）留待后续 change。

## 五、结论

- **Phase 3 BUILD 完成**：3 项 high/critical 经验修复落地
- **回归保护**：11 个 TDD 用例覆盖正常路径 / 边界 / 回归三类
- **门禁通过**：0 FAIL，可进入 Phase 4 DELIVER
- **剩余经验**：2 项留待后续迭代（EXP-0018 / EXP-0044+0045）
