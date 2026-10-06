# v3.3.5（在办）切片执行计划

> change: `2026-10-05-upstream-baseline-alignment` ｜ mode: standard ｜ task_type: documentation

## Dependency Graph Summary

```
zero_dependency: [upstream-baseline-alignment, version-nomenclature]   edges: []   cycles: []

  Slice 1  (version-nomenclature / 活体声明面)  ─┐
                                                 ├─> Slice 3 的 TC-UBL-006（NOTICE/README 单一事实源断言）依赖 Slice 1
  Slice 2  (version-nomenclature / 安装脚本去硬编码)  ← 独立，可与 Slice 1 并行
                                                 │
  Slice 3  (upstream-baseline-alignment / 快照文档) ─┘（仅断言层依赖 Slice 1，实现层独立）
```

**并行化说明**：
- 并行组 1：Slice 1、Slice 2（互不依赖，可并行）
- 并行组 2：Slice 3（其 TC-UBL-006 需 Slice 1 已改动 NOTICE/README 后方可断言通过）

## Slice Execution Plan

| # | 优先级 | 风险 | 预估工时 | 并行组 | TC 覆盖 | 实现目标 | 依赖 |
|---|--------|------|---------|--------|---------|---------|------|
| 1 | P0 | 🟡 Med | M | 组1 | TC-VNOM-001..005 | `NOTICE.md` / `README.md` / `skills/fstdd-fin/SKILL.md` / `docs/WORKBUDDY_INSTALL_NOTES.md` 按轴标注版本 | 无 |
| 2 | P0 | 🟡 Med | S | 组1 | TC-VNOM-006/007/008 | `tools/install_workbuddy_skills.py` 版本字段与横幅由机器可读源派生 | 无 |
| 3 | P0 | 🟢 Low | M | 组2 | TC-UBL-001..006 | 新增 `docs/UPSTREAM_BASELINE.md`（快照单一事实源 + 领先量清单 + 经验库只读对标） | 1（仅断言层） |

> 回归闸门（TC-VNOM-009/010、TC-REG-001/002）为 Part C 全量质量验证的一部分，不单独成切片（无新增测试，属既有门禁回归）。

## Rationale

### Slice 1: 活体声明面版本轴显式化（P0，可并行）
- **依赖关系**：零依赖。是「活体声明面零矛盾」成功标准的直接承载面。
- **风险分析**：🟡 中。文档改动无自动断言保护，易漏改一处留下新矛盾；且须区分「上游自有文档」（禁改）与「活体声明面」（必改）。经验库无 high 匹配（EXP-2026-0013 属形态一致性问题，用于提醒「标注轴」声明与实现同源）。
- **工作量估算**：M —— 4 个文件、5 处漂移点（NOTICE :15/:33、README :5、fstdd-fin :10/:17、NOTES :5/:89）。

### Slice 2: 适配层版本字段派生去硬编码（P0，可并行）
- **依赖关系**：零依赖。与 Slice 1 无文件交集。
- **风险分析**：🟡 中。`install_workbuddy_skills.py` 被 `test_fstdd_matrix` / `test_cross_cutting_verification` / `test_install_source` 直接加载；`stdd_version` 必须为纯 `[\d.]+` 形态（EXP-2026-0013：声明形态须被实现口径覆盖，故 K 取裸 3.1.0）。
- **工作量估算**：S —— 单文件，新增 1 个读取函数 + 改 2 处 frontmatter 字段 + 改横幅/docstring。

### Slice 3: 上游基线快照单一事实源（P0，组2）
- **依赖关系**：TC-UBL-006 断言「NOTICE/README 不含 sha/pushed_at 字面量且链接快照」→ 需 Slice 1 完成 NOTICE/README 改动后方可通过。
- **风险分析**：🟢 低。新增文件，不触碰既有门禁；唯一外部依赖是经验库只读探针（经 `ssh fstdd-hub`）。
- **工作量估算**：M —— 1 个新文档，含 E 全套证据 + 通道排除 + 领先量清单 + 经验库对标 5 个证据段。

## 执行状态（BUILD 完成后回填）

| # | 状态 | tc_coverage | new_tests | verified_at |
|---|------|-------------|-----------|-------------|
| 1 | ✅ done | 5/5 | 12 | 2026-10-05T11:53:05+08:00 |
| 2 | ✅ done | 3/3 | 3 | 2026-10-05T11:57:00+08:00 |
| 3 | ✅ done | 6/6 | 6 | 2026-10-05T12:10:00+08:00 |

> 设计偏离见 `pending-adjustments.yaml`（ADJ-001 / ADJ-002，均为小偏离）。