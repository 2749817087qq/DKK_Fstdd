# 3.3.5 切片执行计划 — 2026-10-06-legacy-debt-cleanup

## Dependency Graph Summary

```
  零依赖节点（可并行）                    依赖节点
  ┌──────────────────────────┐
  │ Slice 1  test-suite-      │◀──────────┐
  │          portability (P0) │           │
  └──────────────────────────┘           │ depends-on
  ┌──────────────────────────┐           │ (RTA SC-004 GIVEN
  │ Slice 3  canonical-hash-  │           │  要求编码修复已完成)
  │          integrity  (P0)  │           │
  └──────────────────────────┘           │
  ┌──────────────────────────┐           │
  │ Slice 4  repo-hygiene (P0)│           │
  └──────────────────────────┘           │
                                         │
                        ┌────────────────┴─────────┐
                        │ Slice 2  release-tooling- │
                        │          accuracy (P0)    │
                        └───────────────────────────┘
  cycles: []  ← dependency-graph 实测无环
```

**并行化说明**：
- **并行组 1**：Slice 1 / Slice 3 / Slice 4（三者互不依赖，可并行）
- **并行组 2**：Slice 2（依赖 Slice 1 完成 —— `release-tooling-accuracy` 的 SC-004 GIVEN 明文要求「编码修复与版本断言修复均已完成」）

## Slice Execution Plan

| # | 优先级 | 风险 | 预估工时 | 并行组 | TC 覆盖 | 实现目标 | 依赖 |
|---|--------|------|---------|--------|---------|---------|------|
| 1 | P0 | 🟡 Med | L | 组1 | TC-TSP-001, TC-TSP-002, TC-TSP-003, TC-TSP-004, TC-TSP-005 | 16 文件 36 处 `subprocess` 补 `encoding="utf-8", errors="replace"`；新增编码策略审计测试 | 无 |
| 2 | P0 | 🟢 Low | M | 组2 | TC-RTA-001, TC-RTA-002, TC-RTA-003, TC-RTA-004 | `.fstdd/standards/release-and-docs.md` 纠错；`test_L1_11` 动态化；新增清单/动态性测试 | 1 |
| 3 | P0 | 🟢 Low | S | 组1 | TC-CHI-001, TC-CHI-002, TC-CHI-003 | 归档 `proposal.md` 的 `source_hash` 同步；新增 canon 一致性批量测试 | 无 |
| 4 | P0 | 🔴 High | S | 组1 | TC-RH-001, TC-RH-002, TC-RH-003, TC-RH-004 | `git rm -r --cached _scratch/` + `.gitignore`；新增仓库卫生断言测试 | 无 |

## Rationale

### Slice 1: test-suite-portability（P0，先行 · 关键路径）
- **依赖关系**：位于依赖图根节点，Slice 2 依赖它（RTA 的 SC-004 GIVEN 要求编码修复已完成）。必须先做。
- **风险分析**：经验库命中 EXP-2026-0014（`except: pass` 静默降级，severity high → +2）；跨 3 个测试目录、16 文件（跨模块 → +1）；MODIFIED 但不改接口（+0）。风险分 3 → 🟡 中。
- **工作量估算**：L —— 16 文件 / 36 调用点，且需新增 2 类审计测试（AST 扫描 + errors 取值扫描），超出 S/M 边界。

### Slice 2: release-tooling-accuracy（P0，依赖 Slice 1）
- **依赖关系**：显式依赖 Slice 1（SC-004 的 GIVEN 明文要求编码修复完成）。放在 Slice 1 之后。
- **风险分析**：经验库命中 EXP-2026-0013（契约断层：声明形态 ≠ 实际可匹配形态，+2）；跨 `tests/` 与 `.fstdd/standards/`（+1）；MODIFIED 不改接口（+0）。风险分 3 → 🟢 中偏低（改动面小、可逆）。
- **工作量估算**：M —— 3 个文件（1 文档 + 1 测试改写 + 1 新增测试），4 个 TC。

### Slice 3: canonical-hash-integrity（P0，可并行）
- **依赖关系**：零依赖（canon 双轨与测试套件无耦合），可与 Slice 1 并行。
- **风险分析**：经验库无高 severity 命中（+0）；单文件改动（+0）；MODIFIED 不改接口（+0）。风险分 1 → 🟢 低。
- **工作量估算**：S —— 1 处哈希同步 + 1 个新增测试文件，3 个 TC。

### Slice 4: repo-hygiene（P0，可并行 · 唯一破坏性切片）
- **依赖关系**：零依赖，可与 Slice 1 并行。**排在最后执行**（同一轮内），以便前序切片的产出先落盘、破坏性操作影响面最小。
- **风险分析**：经验库命中 EXP-2026-0015（工具误用：隔离 = 移动，破坏性副作用，severity high → +2）；变更类型含 REMOVED（索引条目移除，+1）。风险分 3+ → 🔴 高（本 change 唯一高风险项）。
- **工作量估算**：S —— 1 条 git 命令 + 1 行 gitignore + 1 个新增测试文件，4 个 TC。
- **⚠️ 强制前置**：执行 `git rm -r --cached _scratch/` 前，必须先落盘 27 个实体的清单；执行后立即核对磁盘实体数未减。

## 切片执行结果（Phase 3 BUILD 收口）

| # | capability | 状态 | 完成时刻 (UTC) | 关键证据 |
|---|-----------|------|---------------|---------|
| 1 | test-suite-portability | ✅ | 2026-10-06T14:34 | 双环境对照逐字一致（`1 failed, 74 passed, 3 skipped, 1 deselected`）；审计测试 5 passed |
| 2 | release-tooling-accuracy | ✅ | 2026-10-06T14:40 | 根 `tests/` `83 passed / 4 skipped / 0 failed`；`test_L1_11` 动态化；tag 字面量 5→0 |
| 3 | canonical-hash-integrity | ✅ | 2026-10-06T14:26 | 归档条目 `canon verify` 2/2；14 条 proposal 批量 2/2 |
| 4 | repo-hygiene | ✅ | 2026-10-06T14:43 | 索引 27→0；顶层实体 12→12；27 条实体缺失 0；gitignore 命中 25 条 |

**执行顺序实际为**：Slice 3 → Slice 1 → Slice 2 → Slice 4（并行组内按「低风险先行」自裁；Slice 2 严格在 Slice 1 之后）。

**新增测试文件（4 个 / 24 个测试函数）**：
- `tests/test_subprocess_encoding_policy.py`（5）
- `tests/test_canon_hash_integrity.py`（3）
- `tests/test_release_manifest_accuracy.py`（8）
- `tests/test_repo_hygiene_scratch.py`（8）

**切片期间的规格变更（详见 `pending-adjustments.yaml`）**：
- ADJ-004（major）：Slice 2 实现面新增 `tests/test_install_smoke.py`（第二处硬编码发布 tag）⇒ spec 补 SC-005。
- ADJ-006（minor）：Slice 4 的 SC-002 事实假设被证伪（2 个 gitlink 为空目录，备份源路径不存在）⇒ SC-002 改写为以索引实体快照为准。
- ADJ-005（minor）：发现但**刻意未改**（`release-and-docs.md` 第 16 行过期版本号，改它违反 SC-001 的「其余逐条不变」条款）。

