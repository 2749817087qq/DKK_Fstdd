# change 2026-10-12-test-teardown-resilience 切片执行计划

## Dependency Graph Summary

```
（dependency-graph --format json ⇒ nodes=0 / edges=0 / cycles=无）

本 change 只改 `tests/`，不进入代码结构图 ⇒ 无图内依赖。
实际依赖由「同文件写入」决定：

  S1 韧性层（tests/conftest.py）
        │
        └─► S2 规避层 + 症状加固（tests/conftest.py 同文件 + tests/test_verify_notices_default_safe.py）
```

**并行化说明**：
- 并行组 1：**无** —— S1 与 S2 **都要写 `tests/conftest.py`**，同文件不可并行（否则互相覆盖）。
- 故本 change **串行执行 2 个切片**，不做并行分组。

## Slice Execution Plan

| # | 优先级 | 风险 | 预估工时 | 并行组 | TC 覆盖 | 实现目标 | 依赖 |
|---|--------|------|---------|--------|---------|---------|------|
| 1 | P0 | 🟡 Med | M | — | TC-TTR-001, TC-TTR-002, TC-TTR-003, TC-TTR-004, TC-TTR-005 | `tests/conftest.py`：`pytest_configure` 内包装 `os.remove`/`os.unlink`/`shutil.rmtree`（捕获 `SystemExit` → 告警 + 计数；真实异常照抛） | 无 |
| 2 | P0 | 🟢 Low | S | — | TC-TTR-006, TC-TTR-007 | `tests/conftest.py`：测试期 `TMP`/`TEMP`/`TMPDIR` → 仓库外中立目录；`tests/test_verify_notices_default_safe.py`：2 处 `d.mkdir()` → `exist_ok=True` | 1（同文件） |

**验证类 TC（不占切片，Part C 执行）**：TC-TTR-008（连续 3 次全量 failed/errors 一致）、TC-TTR-009（未触碰 `upstream/`）
—— 二者是**会话级/边界级**验证，不产出代码，故在 Part C 执行并在 `test-report.md` 记录证据。

## Rationale

### Slice 1: 韧性层（P0，先行）

- **依赖关系**：无前置。它是 S2 的宿主文件（`tests/conftest.py`），故必须先落地 S1 的结构，S2 再在同一文件的 `pytest_configure` 内追加环境变量设置。
- **风险分析**：
  - 经验库匹配：**EXP-2026-0029**（同根因，medium，`fix_template` 含「TMP/TEMP 中立目录」）、**EXP-2026-0014**（`except Exception: pass` 静默降级，medium）、**KG-092**（失败静默腐烂，high）。按 A2b 公式（有 `severity: high` 匹配 → +2）—— 严格说 KG-092 是知识图谱非经验库，经验库侧最高为 medium ⇒ **经验库项 +0**；复杂度项（Scenario 7 > 5）**+1**；变更类型 NEW **+0** ⇒ **公式分 1（低）**。
  - ⚠️ **但 design.md 的风险评估为「中」**（`tests/conftest.py` 面状影响全部 204 个根级测试；且「不得静默」是纪律风险）⇒ **本切片取「🟡 Med」**（公式分与设计评估不一致时，取更保守者）。
- **工作量估算**：**M** —— 5 个 TC（001..005）、单一文件但需同时满足「捕获 + 可见 + 计数 + 反向守卫」四要件，且要能被 monkeypatch 稳定驱动。

### Slice 2: 规避层 + 症状加固（P0，依赖 S1）

- **依赖关系**：与 S1 **同文件**（`tests/conftest.py`）⇒ 必须串行；`test_verify_notices_default_safe.py` 部分独立，但为保持「一次切片一次验证」合并入本切片。
- **风险分析**：🟢 低 —— `TMP/TEMP` 设置只影响测试进程；`exist_ok=True` 为零风险改动。经验库匹配 **EXP-2026-0030**（TMP/TEMP 指向 agent runtime 目录会被 Guard 误判）⇒ 直接决定「中立目录必须在**仓库之外**」。
- **工作量估算**：**S** —— 2 个 TC、2 个文件、改动点少且机械。

### 切片顺序总理由

1. S1 先（提供包装骨架 + 满足最高优先级的 5 个 TC）；
2. S2 后（同文件追加 + 另一文件的零风险加固）；
3. TC-008/009 不切片：它们是**验证判据**而非实现，放进 Part C 才不会把「验证」伪装成「实现」。
