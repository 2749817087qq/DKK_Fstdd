# 2026-10-04-baseline-failures-zero 测试报告

> 测试日期：2026-10-04
> 测试环境：Windows / Python 3.13.14（workbuddy default env）/ PyYAML 6.0.3 / pytest
> baseline：e7bfb45755f48387225a8ecb4da0a2dd38ec4603
> 说明：本变更为基线治理，不新增产品模块，全部落在单元 + 集成两层。

## 一、总体概况

| 指标 | 数值 |
|------|------|
| 本变更 TC 数 | 8 TC（TC-BFZ-001..008） |
| 本变更关键测试函数 | 11 个（全绿） |
| 定向测试（6 文件 + 1 节点） | 34 passed, 0 failed |
| 全量回归（`upstream/tests`） | **873 passed, 54 skipped, 0 failed** |
| 基线失败数 | 6 → **0** |
| 通过率 | 100% |

## 二、按模块统计

| 测试模块 | 关键用例 | 结果 | 说明 |
|----------|----------|------|------|
| `test_constitution_ops.py` | `test_tmpl_001_dual_source_templates_identical` | ✅ | 模板双源字节一致（REQ-001） |
| `test_evidence_ops.py` | `test_epr_003_templates_consistent_with_examples` | ✅ | 模板与示例一致（REQ-001） |
| `test_except_audit.py` | `test_aud_002/003/004/005` | ✅ | 指纹零漂移 / 分类 / 严重度 / 检测路径（REQ-002） |
| `test_guard_silent_except.py` | `test_grd_001_check_passes_on_current_repo` | ✅ | 审计哨兵在当前仓通过（REQ-002） |
| `test_silent_share.py` | `test_tc_cas_008b_explicit_publish_still_nonzero` | ✅ | 显式 publish 失败→非零（REQ-003） |
| `test_timestamp_ops.py` | `test_tsn_005/006/007` | ✅ | 豁免自检 / 全仓 naive 清零 / 只读（REQ-004） |
| 全量 `pytest upstream/tests -q` | — | ✅ | 873 passed / 54 skipped / 0 failed（REQ-004 / SC-008） |

## 三、工具级验证（发布门禁证据）

| 命令 | 结果 | 退出码 |
|------|------|--------|
| `tools/check_timestamps.py --repo .` | `0 违规 / 0 条失效豁免 / 0 个扫描失败` | 0 |
| `tools/audit_silent_except.py --check` | `哨兵结果: 通过 (0 条提示)` | 0 |

## 四、失败项详细分析

无本变更引入的失败项；基线 6 项已全部转绿（非 skip、非删除用例）。

### 4.1 6 项基线失败 → 修复映射

| # | 现象（最小可复现证据） | 根因 | 修复切片 |
|---|------------------------|------|----------|
| 1 | `test_tmpl_001` 报镜像缺 finance 段 | 项目模板新增 finance 段未下发镜像 | S1 |
| 2 | `test_epr_003` 报模板与示例不一致 | 同上 | S1 |
| 3 | `test_aud_002` 报指纹/行号漂移 | 归档表未随 guard.py 位移刷新 | S2 |
| 4 | `test_grd_001` 哨兵报 5 处行号超容差 | 同上 | S2 |
| 5 | `test_tc_cas_008b` 环境耦合（具备 scp 别名时误判） | 用例未隔离 scp 优先通道 | S3 |
| 6 | naive 时间戳值层/源层非零 | 8 处值缺时区 + 2 处源层 naive + 3 处标识符未豁免 | S4 |

### 4.2 跨午夜边界说明（非基线失败）

`test_fstdd_matrix.py::TestCLI::test_b10_gate_approve_ok` 曾在跨午夜窗口出现一次假失败：
`DEMO_CHANGE` 于 import 期用 `date.today()` 计算（跨午夜前 = 2026-10-03），`new` 执行时
用 `date.today()`（跨午夜后 = 2026-10-04），二者不一致导致目录找不到。单独复跑 3 次全通过，
**判定为非真实基线失败**，不计入本变更范围。

## 五、功能/测试覆盖对照

| 功能模块 | 涉及文件 | 已有测试覆盖 | 缺失测试 |
|----------|----------|-------------|----------|
| 模板双源 | `.fstdd/templates/**` ↔ `upstream/.fstdd/templates/**` | `test_tmpl_001` / `test_epr_003` | 无 |
| 审计活表 | `.fstdd/changes/2026-10-04-baseline-failures-zero/audit/except-points.yaml` | `test_aud_002/003/004/005` / `test_grd_001` | 无 |
| 显式 publish | `upstream/tests/test_silent_share.py` | `test_tc_cas_008b` | 无 |
| naive 时间戳 | `tools/check_timestamps.py` / `tools/heartbeat.py` / `tools/fstdd003_daily_share.py` | `test_tsn_005/006/007` | 无 |

## 六、设计调整说明

本变更 **无设计偏离**（design-adjustments count = 0）。实现与 `design.md` 的 4 项 Decisions 逐项一致。

## 七、C4 失败模式检查（关键项）

| # | 失败模式 | 结果 | 证据 / 处置 |
|---|----------|------|-------------|
| 1 | 幻觉调用 | ✅ | 改动仅复用既有 `.astimezone()` / `strftime` / monkeypatch，无新 API |
| 2 | 过度信任 LLM | ✅ | 每条断言以实跑退代码为准；`astimezone` 是否被 `_AWARE_MARKERS` 识别的疑问经实测证伪后修正结论 |
| 3 | 安全凭证泄露 | ✅ | 审计活表与文档无凭证明文；`sanitized` 纪律不受影响 |
| 4 | 权限绕过 | ✅ | 未手改 `.fstdd.yaml` 确认字段；Gate1/2 记 dialog + 原文 |
| 5 | 静默降级 | ✅ | 不新增裸 except；审计表本身即治理吞错 |
| 6 | 审计缺口 | ✅ | 审计活表 25 点与实况零漂移；`--check` 哨兵通过 |
| 7 | 格式错误 | ✅ | canonical YAML / 审计活表 `yaml.safe_load` 通过；`canon verify` 2/2 |
| 8 | 过度工程 | ✅ | 4 类修复均为最小改动（补齐镜像 / 刷表 / 隔离用例 / 时区后缀 + aware + 豁免） |

## 八、结论

**可进入 Gate 3。** 6 项预存基线失败全部转绿（非 skip），全量 `upstream/tests` 873 passed / 0 failed，
`check_timestamps` 与 `audit_silent_except --check` 双绿，`canon verify` 2/2。
风险等级：**低**。潜在遗留：`verify_eol TC-EOL-005` 要求工作树干净（仅允许 tools/docs/skills/README/.gitignore
未提交 diff），故四自检脚本须在提交后复跑确认全绿。