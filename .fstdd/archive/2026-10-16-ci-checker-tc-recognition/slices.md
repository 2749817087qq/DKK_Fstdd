# v1.0 切片执行计划 — 2026-10-16-ci-checker-tc-recognition

## Dependency Graph Summary

```
[ci-checker-tc-recognition]  ← 唯一 capability（nodes=1, edges=0, cycles=0, zero_dependency=1）
        │
        ├─ Slice 1 ── helper + ci 覆盖检查（REQ-CTR-001 / SC-001~003）
        ├─ Slice 2 ── (d) 查重口径对齐（REQ-CTR-002 / SC-005~006 + 003 可审计性 SC-008）
        └─ Slice 3 ── diff/trace 同根因点位（REQ-CTR-001 / SC-004）
```

**并行化说明**：无并行组——Slice 1/2 同改 `ci.py` 与 `tests/commands/test_ci.py`，Slice 3 改 `diff.py`/`trace.py`（与 1 共享 helper 引入点），单 agent 串行执行，避免同文件写冲突。

## Slice Execution Plan

| # | 优先级 | 风险 | 预估工时 | 并行组 | TC 覆盖 | 实现目标 | 依赖 |
|---|--------|------|---------|--------|---------|---------|------|
| 1 | P0 | 🟡 中 | S | — | TC-CTR-001/002/003 | `utils.iter_test_files()` + `ci.py:558` 切换 + 2 测试文件新增 | 无 |
| 2 | P0 | 🟡 中 | S | — | TC-CTR-005/006/008 | `ci.py:317` 定义行正则 + TC-CI-008 换语义更新 + 3 新测试 | 无（与 1 同文件，串行） |
| 3 | P1 | 🟢 低 | S | — | TC-CTR-004 | `diff.py:99` / `trace.py:95` 切换 + subprocess CLI 测试 | Slice 1（helper 先行） |

## Rationale

### Slice 1: helper + ci 覆盖检查（P0，先行）
- **依赖关系**：helper 是三处调用点的公共前提，必须第一个落地；无外部依赖（零依赖节点）。
- **风险分析**：经验库匹配 EXP-20260917-A1（severity=high，+2）；Scenario 9 > 5（+1）；接口无破坏（helper 为新增、check 函数签名不变，+0）→ 风险分 3 = 中风险 🟡。glob 语义变更影响所有历史 change 的覆盖判定，故 P0 先行。
- **工作量估算**：S——1 新函数 + 1 行切换 + 3 个测试函数（2 进 test_ci.py、1 进 test_utils.py）。

### Slice 2: (d) 查重定义行口径（P0）
- **依赖关系**：与 Slice 1 无硬依赖，但同改 ci.py 与 test_ci.py → 串行跟在 Slice 1 后。这是 EXP-20260917-A1 等待 30 天未落地的核心修复。
- **风险分析**：同条目高严重经验（EXP-20260917-A1 / EXP-2026-0017）；语义收窄可能让存量写法判定翻转（PASS 翻转）——以真实数据验收（SC-007 十连 archival + SC-009 下游复跑）兜底。
- **工作量估算**：S——1 处正则 + 1 个既有测试更新 + 3 个新测试（含 TC-CTR-008 审计注释守卫）。

### Slice 3: diff/trace 同根因点位（P1）
- **依赖关系**：依赖 Slice 1 的 helper；独立于 Slice 2。
- **风险分析**：同根因（EXP-2026-0001 类 glob 失明）的机械切换；CLI subprocess 测试有环境耦合（cwd/编码），用仓库既有 `run_cli` 模式（PYTHONIOENCODING=utf-8 + timeout）防抖。
- **工作量估算**：S——2 处一行切换 + 1 个 subprocess 测试。
