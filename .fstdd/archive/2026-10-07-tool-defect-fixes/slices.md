# 3.3.6+ 切片执行计划 — 2026-10-07-tool-defect-fixes

## Dependency Graph Summary

```
  零依赖节点（全部可并行）                    实测 dependency-graph：
  ┌──────────────────────────────┐            nodes  = 5
  │ S2 experience-io-contract    │            edges  = 0   ← 无任何依赖
  ├──────────────────────────────┤            cycles = []  ← 无环
  │ S4 ci-check-accuracy         │            zero_dependency = 全部 5 个
  ├──────────────────────────────┤
  │ S1 dry-run-fidelity          │            故「并行组」仅表达风险分层，
  ├──────────────────────────────┤            实际由单 agent 串行执行。
  │ S5 quarantine-opt-in-safety  │
  ├──────────────────────────────┤
  │ S3 proposal-extraction-      │
  │    fidelity  🟡 高风险       │
  └──────────────────────────────┘
```

**并行化说明**：
- **并行组 1（低 / 中风险，先做）**：S2、S4、S1
- **并行组 2（行为语义变更 / 高风险，后做）**：S5、S3

**实际执行顺序（技术自裁）**：`S2 → S4 → S1 → S5 → S3`
—— 按风险升序；S3 改**共享渲染器**（影响所有新建 proposal.md 的结构），放最后做，
以便前序切片的产出先稳定，最后一次性重渲染并复核 `canon verify`。

## Slice Execution Plan

| # | capability | 优先级 | 风险 | 工时 | 并行组 | TC 覆盖 | 实现目标 | 依赖 |
|---|-----------|--------|------|------|--------|---------|---------|------|
| 1 | dry-run-fidelity | P0 | 🟢 中 (2) | M | 组1 | TC-DRY-001..004 | `phase.py::cmd_phase` 补 dry-run + 新增契约扫描测试 | 无 |
| 2 | experience-io-contract | P0 | 🟢 低 (1) | M | 组1 | TC-EIO-001..005 | `_save_index()` 补 `newline` + `_json_default()` 覆盖 5 个 `json.dumps` | 无 |
| 3 | proposal-extraction-fidelity | P0 | 🟡 高 (4) | M | 组2 | TC-PXF-001..003 | `canon.py` 渲染器补 h2 + `extract_proposal.py` 锚点同源 | 无 |
| 4 | ci-check-accuracy | P0 | 🟢 中 (2) | S | 组1 | TC-CCA-001..002 | `check_tcid_unique()` 改定义点判定 | 无 |
| 5 | quarantine-opt-in-safety | P0 | 🟢 中 (3) | S | 组2 | TC-QIS-001..003 | `verify_notices()` 默认只报告 + `--quarantine` opt-in | 无 |

## Rationale

### Slice 1: dry-run-fidelity（P0，可并行）
- **依赖关系**：零依赖（`phase.py` 与其它切片无交集）。
- **风险分析**：经验库命中 **FSTDD005-EXP-20260918-C2**（high，「SCHEMA 声明了 FOREIGN KEY 但从未生效」= 声明与实现脱节，+2）；
  跨模块（`phase.py` + 需扫描全部命令模块，+1）；MODIFIED 但不改接口（+0）⇒ **2 → 🟢 中**。
- **工作量估算**：M —— 1 个源文件 + 1 个新测试文件（含契约扫描器与自检）+ 4 个 TC。

### Slice 2: experience-io-contract（P0，可并行）
- **依赖关系**：零依赖（`experience.py` 单文件）。
- **风险分析**：无 high 直接命中（EXP-2026-0020 属「机械补参数」不同族，不计）；Scenario 4（≤5，+0）；
  单模块（+0）；MODIFIED 不改接口（+0）⇒ **1 → 🟢 低**。
- **工作量估算**：M —— 1 个源文件（2 处改动）+ 1 个新测试文件 + 5 个 TC。

### Slice 3: proposal-extraction-fidelity（P0，**高风险**）
- **依赖关系**：零依赖，但**改共享渲染器** ⇒ 影响所有新建 `proposal.md` 的结构，
  故排最后执行，避免前序切片期间反复重渲染。
- **风险分析**：经验库命中 **EXP-2026-0013**（high，契约断层：声明形态 ≠ 实际可匹配形态，+2）；
  跨模块（`canon.py` + `extract_proposal.py`，+1）；MODIFIED 且**输出结构变更**（+1）⇒ **4 → 🟡 高**。
- **工作量估算**：M —— 2 个源文件 + 1 个新测试文件 + 3 个 TC（含历史 h3 兼容回归）。

### Slice 4: ci-check-accuracy（P0，可并行）
- **依赖关系**：零依赖（`ci.py` 单文件）。
- **风险分析**：无 high 直接命中（EXP-2026-0016 为 low，但正是本缺陷的历史记录）；
  Scenario 2（+0）；单模块（+0）；MODIFIED 且**判据语义变更**（+1）⇒ **2 → 🟢 中**。
- **工作量估算**：S —— 1 个源文件 + 1 个新测试文件 + 2 个 TC（含反向样本）。

### Slice 5: quarantine-opt-in-safety（P0，**行为语义变更**）
- **依赖关系**：零依赖（`tools/verify_notices.py` 单文件）。
- **风险分析**：经验库命中 **EXP-2026-0015**（high，隔离=移动的破坏性副作用，+2）；
  Scenario 3（+0）；单模块（+0）；MODIFIED 且**默认行为语义变更**（+1）⇒ **3 → 🟢 中**。
  ⚠️ 虽评级为中，但它是本 change 唯一**改变安全工具默认行为**的切片，验证强度按高风险执行。
- **工作量估算**：S —— 1 个源文件 + 1 个新测试文件 + 3 个 TC。

## 切片验证口径（B3.4 强制）

每个切片完成后必须同时满足三项，否则不得进入下一切片：

1. **TC 覆盖**：该切片全部 TC-ID 都有对应测试函数（100%）
2. **产出物核对**：`slices.md` 的「实现目标」逐项存在
3. **测试运行**：该切片新增测试 **> 0** 且全部通过；同时跑既有回归（`test_ci` / `test_phase` /
   `test_experience` / `test_experience_v29` / `tools/test_verify_notices`）

> ⚠️ **本 change 的两条自设纪律**（因待修缺陷自身会干扰验证）：
> - **不使用 `phase advance --dry-run`**（缺陷 1 未修前会真实落盘）
> - **跑过 `experience` 命令后必查 `.experience-index.yaml` 是否被写成 CRLF**，提交前归一/还原（缺陷 2）
