# 3.1.0 测试报告 —— change 目录解析增归档回退

> 测试日期：2026-09-29（**回填补齐**；本 change 于 2026-09-26 归档，DELIVER 阶段漏落本报告）
> 测试环境：Windows / Python 3.13.14 / pytest 9.1.1
> 被测版本：`db4cc7ed4faa49d3a830289b7901d51abb644694`（本次复跑）
> 原 change 建立基线：`f3b27139c0e6ee50778bd2878f4680a989f50e8a`（2026-09-26）
> 对应 Spec：`canonical/specs/code/2026-09-26-finder-archive-fallback.yaml`
> （capability `change-dir-resolution`；REQ-001 ~ REQ-003，SC-001 ~ SC-013）
> 测试方案：`test-plan.md`（TC-FAF-001 ~ TC-FAF-013）

## 一、总体概况

| 指标 | 数值 |
|------|------|
| 测试用例总数 | 21 |
| 通过 | 21 |
| 失败 | 0 |
| 跳过 | 0 |
| 通过率 | 100% |
| 执行耗时 | 8.57 秒 |

> 复跑命令：`python -m pytest upstream/tests/test_finder.py upstream/tests/commands/test_finder_archive_fallback.py -q`

## 二、按模块统计

| 测试模块 | 用例数 | 通过 | 失败 | 跳过 | 说明 |
|----------|--------|------|------|------|------|
| `upstream/tests/test_finder.py` | 8 | 8 | 0 | 0 | 单元：`find_change_dir` 精确/后缀/无匹配/None/缺 `.fstdd.yaml` |
| `upstream/tests/commands/test_finder_archive_fallback.py` | 13 | 13 | 0 | 0 | 本 change 新增：TC-FAF-001 ~ TC-FAF-013 |

## 三、E2E 测试结果

N/A —— 本 change 不涉及用户可见流程，集成层已覆盖全部行为面（见 `test-plan.md` §1.1）。

## 四、功能/测试覆盖对照

| 功能模块 | 用例 | 结果 |
|----------|------|------|
| `finder.find_change_dir`（`include_archive` 开关 + 默认零漂移） | TC-FAF-001 ~ 006 | ✅ 通过 |
| 归档后 `validate` / `status` / `canon verify` / `structure merge` 四条命令可用 | TC-FAF-007 ~ 010 | ✅ 通过 |
| 归档相关既有行为零漂移（二次 archive 自我移动反例 / rollback 回归 / 正向 archive） | TC-FAF-011 ~ 013 | ✅ 通过 |

## 五、证据记录

> 每条引用实测数据的证据须可定位观测时刻与代码版本（TC-EPR-002）。

| 证据 | observed_at | observed_base_git_sha | 来源 |
|---|---|---|---|
| 复跑 21 passed / 0 failed / 0 skipped（8.57s） | 2026-09-29T12:56:00+08:00 | `db4cc7ed4faa49d3a830289b7901d51abb644694` | `pytest upstream/tests/test_finder.py upstream/tests/commands/test_finder_archive_fallback.py -q` |
| BUILD 阶段全量套件 850 passed / 1 skipped / 0 failed（21m46s） | 2026-09-26T05:47:41+00:00 | `f3b27139c0e6ee50778bd2878f4680a989f50e8a` | `.fstdd.yaml` → `phases.build.confirmed_evidence`（K-main 裁定原文） |
| 假阴性自检 9 failed / 12 passed（新增能力 9 例敏感、4 例零漂移守卫保持绿） | 2026-09-26T05:47:41+00:00 | `f3b27139c0e6ee50778bd2878f4680a989f50e8a` | 同上 |

- `observed_at` 为信息采集时刻，非文档生成时刻。

## 六、结论

✅ 可部署 —— 归档后四条命令（`validate` / `status` / `canon verify` / `structure merge`）均恢复可用，
且 `include_archive` 默认语义零漂移由反例 TC-FAF-011（二次 archive 不得自我移动）锚定，未见回归。

> 本报告为**归档补齐**：该 change 归档时未落 `test-report.md`（`tools/verify_rename.py` TC-RENAME-005
> 要求每个归档 change 的关键资产可访问）。本次按仓库现有测试资产复跑并补录，复跑结论与 BUILD
> 阶段记录一致；未新增/修改任何源码或测试。