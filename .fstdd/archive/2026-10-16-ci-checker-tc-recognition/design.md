# 修复 CI 检查器两类识别缺陷 — 技术设计

## Context

**目标仓**：FSTDD003（`stdd-repo` worktree `FSTDD005-wt-311`，HEAD `c99ef7d`），CLI 实现位于 `upstream/fstdd/cli/`。

**两类缺陷的实测背景**：

1. **测试文件 glob 失明**：`check_tc_implementation_coverage`（`ci.py:558`）、`cmd_diff`（`diff.py:99`）、`cmd_trace`（`trace.py:95`）三处均以 `tests_dir.rglob("test_*.py")` 扫描测试文件，对连字符命名 `test-*.py` 结构性失明。2026-10-16 下游项目交付取证：对测试全部为连字符命名的归档 change 报「TC 实现覆盖 0/10」假 FAIL，修正 glob 后实测 9/10（唯一缺失为 test-plan 模板 boilerplate 引用）。同根因在下游记为 EXP-2026-0001，在本仓经验库中无对应条目（glob 类缺口是本次新沉淀点）。
2. **TC-ID 查重口径分裂**：`check_tcid_unique`（`ci.py:317`）按 test-plan.md **全文** `re.findall(r"(TC-[A-Z]+-\d{3})")` 计数，任一 ID 出现两次即 FAIL；而 `validate.py:82-88` 只数 `| **ID** | TC-… |` **定义行**，并在注释中声明意图「两个案例不得共用同一 ID」、说明矩阵/补充顺序中引用 TC-ID 是模板正常写法。

**关键历史事实**：本仓经验 **EXP-20260917-A1**（2026-09-17 由 FSTDD001 录入，severity=high）早已确诊缺陷②的根因与修法（「只统计定义行」），并附 10/10 历史归档 change 全部误报的决定性取证——但 30 天未落地。下游项目因此被迫以「每个 TC-ID 字面全文恰一次」的扭曲写法适配工具（EXP-2026-0017）。本 change 将该修复正式落地，并以同方法做真实数据验收。

**约束**（继承 proposal constraints）：不放宽任何真实判据；两检查器正则逐字一致；既有测试更新保留审计痕迹；不改其他检查项与阈值。

## Decisions

### 1. 共享 helper `iter_test_files()`，而非三处内联修复

**方案**：在 `fstdd/cli/utils.py` 新增 `iter_test_files(tests_dir)`，内部同时匹配 `test_*.py` 与 `test-*.py`（`seen` 集合去重防御未来模式扩张），三处调用点切换。

**为什么**：glob 失明是**同一根因的三处实例**（EXP-2026-0001 类）。内联修复 = 同一错误修三遍、留两处腐烂；helper 是单一事实源，docstring 声明「新增命名模式必须改此处」，杜绝第 4 处。

**备选方案及排除原因**：
- 备选 A（三处各写 `for pattern in (...)`）：重复三份，未来第四处点位（如 `status.py` 同类扫描）大概率再漏——正是本缺陷的成因模式。
- 备选 B（正则匹配任意 `test.*\.py`）：过宽，会误抓 `testify.py`、`testdata_utils.py` 等非测试文件，改变既有识别面。
- 备选 C（只修 ci.py，diff/trace 另案）：留下两处假阴性（`fstdd diff` 对连字符测试文件持续显示「未覆盖」、`fstdd trace` 找不到引用），下一份假报告还会再来；用户 Gate 1 未异议，按建议纳入。

### 2. helper 命名识别范围收敛为两种

**方案**：只识别 `test_*.py` 与 `test-*.py`。

**为什么**：这两种是本仓族（本仓 + 下游项目）的实际约定（下游经 `run-all.py` 聚合计 31 个连字符脚本）。过宽误抓、过窄漏报。

**备选方案及排除原因**：
- 备选 A（增加 `*_test.py` pytest 风格）：本仓族无此命名，引入无收益的识别面扩张。

### 3. (d) 查重对齐 validate 定义行口径（正则逐字复制）

**方案**：`check_tcid_unique` 改用 `\*\*ID\*\*\s*\|\s*(TC-[A-Z]+-\d{3})`——与 `validate.py:82-88` 逐字一致，并加注释引用 EXP-20260917-A1 / EXP-2026-0017 与 validate 对齐事实。

**为什么**：validate 的注释已声明该检查的意图（案例级查重）；EXP-20260917-A1 给出同样修法；下游 EXP-2026-0017 记录了不对齐的工作流代价。方向只能是 ci 向 validate 对齐，不能反向。

**备选方案及排除原因**：
- 备选 A（validate 改成全文口径反向对齐）：违背 validate 注释声明的意图，且会让更多存量合规 test-plan（含矩阵引用）转红——与 EXP-20260917-A1 的 10/10 取证结论直接冲突。
- 备选 B（两边统一到第三种口径）：双倍改动面、零收益，且破坏两处既有测试。
- 备选 C（ci (d) 降级为 WARN）：把「两案例共用 ID」这个真实问题从错误降级为警告，放松真实判据，违反 constraint #1。

### 4. TC-CI-008 fixture 更新：换语义、留痕迹

**方案**：既有测试 `test_check_failures_detects_duplicate_tc_ids`（TC-CI-008）的 fixture 由「裸重复 TC-ID、无定义行」改为「两条 `| **ID** | TC-X-001 |` 定义行」——同一测试意图（检测重复）在新语义下重新落地；测试内注释说明「旧 fixture 编码旧全文语义，随本 change C4 同批更新」。

**为什么**：旧 fixture 是旧语义的编码，修复后必然转红；直接删测试会丢失覆盖，静默改绿会丢失审计痕迹。

**备选方案及排除原因**：
- 备选 A（保留旧 fixture 加新 fixture 双跑）：旧 fixture 断言的行为恰是本次要消除的误报，保留它等于固化错误。
- 备选 B（删除该测试）：丢失「两案例共用 ID 必 FAIL」的真实判据覆盖。

### 5. 回归测试落点：既有布局，两层

**方案**：checker 行为测试进 `tests/commands/test_ci.py`（与 TC-CI-006/007/008 同类）；helper 单测进 `tests/test_utils.py`；diff/trace 行为以 subprocess 跑 CLI 取证（仓库既有模式，见 `test_validate_voice.py` 的 `run_cli`）。

**为什么**：跟从仓库既有测试布局；行为测试贴近调用点，单测贴近实现。

## Architecture

```
                  ┌────────────────────────────────────────────┐
                  │  fstdd/cli/utils.py                        │
                  │  iter_test_files(tests_dir)                │
                  │  = rglob("test_*.py") ∪ rglob("test-*.py") │
                  │  （seen 去重；新增命名模式唯一修改点）        │
                  └───────┬──────────────┬──────────────┬──────┘
                          │              │              │
              ci.py:558   │   diff.py:99 │  trace.py:95 │
                          ▼              ▼              ▼
        check_tc_implementation    cmd_diff        cmd_trace
        _coverage（计划TC vs       （覆盖 diff：    （TC 追溯：
        实际测试文件）              未覆盖判断）      测试引用定位）

   ci.py:317 check_tcid_unique
     before: re.findall(r"(TC-[A-Z]+-\d{3})", content)        ← 全文口径（误报源）
     after:  re.findall(r"\*\*ID\*\*\s*\|\s*(TC-[A-Z]+-\d{3})", content)  ← 定义行口径
             与 validate.py:82-88 逐字一致（EXP-20260917-A1 / EXP-2026-0017）
```

**判定流向不变**：`check_tc_implementation_coverage` 的 FAIL/WARN 阈值（<50% FAIL）与原逻辑保持一致，仅扩大文件识别面；`check_tcid_unique` 的 PASS/FAIL 结构不变，仅收窄统计口径到定义行。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| glob 补全后历史存量 test-plan 的 TC-ID 被更多识别，(d) 从 FAIL 翻 PASS 的 change 被误读为「质量提升」 | 翻转即修复目的（去假红）；test-report 以「修复前后对同一 change 复跑对比」留证，PASS 翻转不作为独立质量结论 |
| 定义行口径让「TC-ID 只在矩阵出现、从无案例定义行」的 test-plan 逃过查重 | validate 的「ID 行数 ≥ Scenario 数」同向兜底；(d) 语义本就是案例级查重，存在性由 TC 实现覆盖检查负责（职责分离） |
| iter_test_files 未来第三种命名模式出现又忘抽常量 | 单一 helper + `tests/test_utils.py` 单测钉死两种模式；docstring 声明修改点唯一性 |
| (g) AND 数量检查存在同类「统计粒度」错误（EXP-20260917-A1 同表列出：按文件计数、阈值 5 本为单 SC 设计） | **不在本 change 范围**（用户点名 2 条 + C3 同根因 glob 点位，均不含 (g)）；已记 followup：需要独立 change 评估按 SC 计数及其对存量 spec 的影响面 |
| 本 change 自己的 test-plan 在新旧语义切换窗口期被 (d) 误判 | Phase 3 先在 RED 态记录旧语义误判，GREEN 后复跑取证；test-plan 按「一行一 ID」写法从开始就合规 |
