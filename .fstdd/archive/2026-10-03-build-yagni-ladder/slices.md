# v3.2.0（候选）切片执行计划

> change：2026-10-03-build-yagni-ladder | mode=standard | complexity=7

## Dependency Graph Summary

```
build-quality-verification   yagni-ladder-gate
        (zero_dependency)        (zero_dependency)
              │                       │
              └───────────┬───────────┘
                          ▼
              tests/test_finance_content.py
              （L1 静态断言为共同验证面）
```

**并行化说明**：
- 依赖图显示两个 capability 均为 `zero_dependency`，`edges=[]`，`cycles=[]`。
- 但两者共用同一验证文件 `tests/test_finance_content.py`，且 Slice 2 的模板断言（L1-16/17）
  与 Slice 1 无代码交集；为避免同一测试文件并发编辑冲突，本 change 采用**串行执行**（不并行）。

## Slice Execution Plan

| # | 优先级 | 风险 | 预估工时 | 并行组 | TC 覆盖 | 实现目标 | 依赖 |
|---|--------|------|---------|--------|---------|---------|------|
| 1 | P0 | 🟡 Med | M | —（串行） | TC-BQV-001/002/003/004/005/006, TC-YLG-004 | `.fstdd/skills/build.md` + `upstream/.fstdd/skills/build.md` 的 C4 #23 + 标题；`tests/test_finance_content.py` L1-05/06/14/15 | 无 |
| 2 | P0 | 🟢 Low | S | —（串行） | TC-YLG-001/002/003 | `.fstdd/templates/yagni-ladder.md` + `upstream/.fstdd/templates/yagni-ladder.md`；`tests/test_finance_content.py` L1-16/17 | 1（同测试文件，串行） |

## Rationale

### Slice 1: C4 22 → 23 + 静态断言同步（P0，先行）
- **依赖关系**：C4 行数是本 change 的核心信号，静态断言 L1-05/06 直接依赖它；后续模板切片只增文件、不改行数，故先行。
- **风险分析**：🟡 Med。命中 EXP-2026-0013「声明形态 vs 正则实际匹配形态不一致」——C4 行数正则 `## C4.*?## C5` 边界必须仍能截到新行；两份 build.md 必须逐字一致否则 upstream 漂移。缓解：两份同改 + diff 核对 + pytest 实跑。
- **工作量估算**：M（2 文件改 + 1 测试文件 4 处改，覆盖 7 个 TC）。

### Slice 2: yagni-ladder.md 双份 + 模板断言（P0，可后置）
- **依赖关系**：与 Slice 1 无代码依赖，但共用测试文件，串行以避免编辑冲突。
- **风险分析**：🟢 Low。纯新增文件，无回归面；风险在「两份不一致」→ 断言内容一致 + install/verify 覆盖。命中 EXP-2026-0013 缓解：断言用直接 substring 匹配，不依赖复杂正则。
- **工作量估算**：S（2 新文件 + 1 测试文件 2 处新增，覆盖 3 个 TC）。