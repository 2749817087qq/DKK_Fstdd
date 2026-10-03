# 2026-10-03-caveman-kg-sync 任务清单

## 1. caveman-compressor（P0）

- [x] 1.1 实现 `upstream/fstdd/caveman.py` — `compress(text, max_chars=200)` + `compress_dict(d, keep_keys=None)`（独立库，无 hub_client/canon 依赖）
- [x] 1.2 trim_rules 落地：中文修饰词 regex / 英文停用词 / 长句截断 / 重复合并 / motivation 砍除
- [x] 1.3 field_weights + budget_allocation（含截断优先级倒转：缺 constraints 时先砍 summary）
- [x] 1.4 新增 `upstream/fstdd/cli/commands/caveman.py` + 在 `cli/__init__.py` 注册 `caveman` 子命令（`--max` / `--out` / 文件不存在 exit non-zero）
- [x] 1.5 canon 集成：`canon.py::_generate_one` 生成 proposal.md 后追加 `caveman_summary.txt`（≤200）
- [x] 1.6 hub_client 集成：`issue()` 附 `scope["scope_min"]`；`complete()` result>200 时附 `result_min`

## 2. kg-autosync（P0）

- [x] 2.1 实现 `upstream/fstdd/kg_sync.py` — scan_targets 5 类路径 + ID 正则提取 + type/severity 关键词推断
- [x] 2.2 ADD / UPDATE / DEPRECATE(>30天) / BUILD_EDGES(共现≥阈值) 四类操作
- [x] 2.3 KG schema 升级：node 新增 `first_seen_at` / `last_synced_at` / `last_removed_at` / `deprecated` / `source_files`；edge 统一 `{from,to,type,last_synced_at}`
- [x] 2.4 新增 `kg sync` CLI（`--dry-run` / `--deep` / `--edge-threshold` / `--full`）+ diff_kg.yaml 输出 + 幂等
- [x] 2.5 `.git/hooks/post-commit.fstdd.sample`（可选 sample，不自动 install）
- [x] 2.6 knowledge-graph.yaml 首次 re-index（先 --dry-run 验证）

## 3. 测试与验证

- [x] 3.1 `upstream/tests/test_caveman.py`（22 TC）RED→GREEN
- [x] 3.2 `upstream/tests/test_kg_sync.py`（24 TC）RED→GREEN
- [x] 3.3 每切片 Step B3.4 验证（TC 覆盖 + 产出物 + 测试通过 + 无回归）
- [x] 3.4 全量 pytest 通过（本变更 46 TC 全绿；15 项失败为预存基线，见 test-report §3.1）
- [x] 3.5 C4 失败模式检查（14 常规 + 8 金融 = 22 行）+ test-report.md

<!--
优先级说明：
- P0：阻塞性任务，完成前无法进入下一阶段
- P1：重要任务，应在当前阶段完成
- P2：可延后到后续版本的任务
-->