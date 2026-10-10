# 经验库跨副本收敛与去重（4→1 权威库）— 技术设计

## Context

本机存在 4 个 FSTDD 经验库副本，共 **179** 个经验文件，但唯一 `experience_id` 仅 **90** 个：
`E:/FSTDD/stdd-repo/.fstdd/experiences`(79) / `D:/FSTDD003/.fstdd/experiences`(69) /
`~/.workbuddy-ai/FSTDD/experiences`(19) / `D:/FSTDD002/.fstdd/experiences`(12)。

实测分类（2026-10-10 只读扫描，`analyze_experiences.py` + `analyze_drift.py`）：
- 纯重复：47 个 eid 多份内容完全一致（134 冗余文件，67 组）
- 内容漂移：21 个 eid 同 id 多份内容不一致（stdd-repo vs FSTDD003 2 个 + home-FSTDD 漂移 19 个）
- FSTDD002 独有：12 个 eid 其他副本完全没有（删副本会丢）
- FSTDD003 / home-FSTDD 相对 stdd-repo **0 条独有**（纯重复/漂移子集）

**关键实测（推翻前置假设）**：上游 P0-pre change（commit `1555de9`）只修了索引对账
（`audit_experience_baseline.py` 的 `load_index_keys`）与基线审计工具，**未改 `_load_experience`**。
实测 `experience list --format json` 前几个条目仍只有 `{exported_at, sanitized}`（双块第 1 块），
`EXP-2026-0012` 起才含完整 `experience_id/category/severity` → **P1 解析器 bug 未修**，
`list`/`stats` 仍静默丢真身。故本 change 必须**自己修复 `_load_experience`**（P1 本体）。

约束：上游 `upstream/fstdd/` 是 vendored 内核（MIT，来自 `leonai42/stdd`）。修复属 bug fix，
但改动 vendored 文件需明确锚定、加契约测试、不扩展其对外行为。

## Decisions

### 1. 修复 `_load_experience` 双块解析（AMD-002，实测驱动）

**方案**：将 `upstream/fstdd/experience.py` 的 `_load_experience` 由「`content.split("---",2)[1]`
只取首个 frontmatter 块」改为「解析全部 `---` 分隔块，逐块 `yaml.safe_load` 并合并（后块覆盖前块冲突键，
或真身块优先），返回完整字段」。同步加 RED→GREEN 契约测试，用 46 个受影响样本
（`EXP-20260915-A1` 等双块条目）验证 `experience_id/category/severity` 全部回读正确。

**为什么**：实测 `experience list` 仍丢真身，证明 P0-pre 未修此路径。不修则 C6 重建的索引
仍基于错数据，收敛等于「把坏数据搬进权威库」。这是「先可信、再可见」的前提。

**备选方案及排除原因**：
- 备选 A（只在写入端统一为单块）：不修读取端，仅改 `share_experience.py`/inbox 导入。
  排除——存量 78/79 双块文件已存在，只防新增不治旧，收敛后 `list` 仍失真。
- 备选 B（写迁移脚本时顺手归一 frontmatter）：把修复塞进 `consolidate_experiences.py`。
  排除——解析器是 Phase 3 自动加载（`experience load`）的共享基础设施，应在其自身修，
  而非在一次性迁移脚本里绕开。

### 2. 锚定等级 L1 → L3（AMD-001）

**方案**：因 `risk_assessment.safety_critical: true`（经验数据有丢失风险），按 understand.md
Step 4.5 硬规则 `safety_critical=true → 至少 L3`，将 `anchoring.level` 由 L1 升为 L3，
引用 `2026-10-10-p0-pre-audit-baseline`（其备份 + 幂等模式作为模式锚定参照）。

**为什么**：L3 模式锚定要求引用已有同类 change 的解决模式。P0-pre 已建立「先备份、再校验、
幂等可重跑、契约测试防复发」的模式，本 change 复用同一模式，降低自由度风险。

**备选**：保持 L1 → 排除，会触发 Gate 2 阻塞。

### 3. 权威写库锁定 stdd-repo

**方案**：唯一保留的写库 = `E:/FSTDD/stdd-repo/.fstdd/experiences`（随仓库走，有三远端
origin/local/server 备份，P0-pre 已加固）。其余 3 副本降为只读参考。

**为什么**：FSTDD003 / home-FSTDD 0 独有；FSTDD002 有 12 独有须先回灌。锁定单点避免多源冲突。

### 4. 迁移脚本幂等 + --dry-run（C8）

**方案**：`tools/consolidate_experiences.py` 实现 C2 回灌 / C3 裁决 / C4 去重 / C6 降级，
全程幂等：重跑不产生重复、不破坏已收敛状态；`--dry-run` 只打印将执行动作不落盘；
`--verify` 校收敛后不变量（唯一 eid=90、无重复内容、索引干净）。

**为什么**：破坏性操作须可重跑、可预览，符合 L3 锚定的「幂等可重跑」模式。

### 5. 删除走回收站非 rm（C4）

**方案**：删 134 冗余文件时，留 stdd-repo 那份，其余用同盘 `os.rename` 移入 Windows 回收站
（或 `_backup/.../trash/`），**不用 `rm -rf`**。逐批 ≤10。

**为什么**：本沙箱 `rm -rf`/`shutil.rmtree` 被 safe-delete 守卫拦截（state lock timeout，
连解释器都起不来）；且经验文件有回灌价值，移回收站可人工复核后清。

### 6. 备份先行（C1）

**方案**：操作前 `robocopy /E /COPYALL` 三副本到 `E:/FSTDD/_backup/exp-*-20261010/`，
校验文件数与源一致后再动。

**为什么**：破坏性操作兜底，满足 L3 数据安全要求。

## Architecture

```
            4 副本（现状，冲突源）
  stdd-repo(79)  FSTDD003(69)  home-FSTDD(19)  FSTDD002(12)
       |              |              |              |
       +--------------+--------------+--------------+
                     |  C1 备份到 _backup/
                     v
  [C5] 修 _load_experience（解析全部块合并）
                     |
                     v
  [C2] 回灌 FSTDD002 独有 12 --> stdd-repo/.fstdd/experiences
  [C3] 裁决 21 漂移 eid（默认 stdd-repo 为准）
  [C4] 删 134 冗余（移回收站，留 stdd-repo 份）
  [C6] FSTDD003/home/FSTDD002 降级只读参考
  [C8] consolidate_experiences.py 串联以上（幂等 + --dry-run）
                     |
                     v
  [C6->C5] 重建 .experience-index.yaml（修复后解析器）
                     |
                     v
        权威库 stdd-repo（唯一写源，90 唯一 eid）
           |                    |
           v                    v
  Phase 3 自动加载       经验回传网络消费
  (experience load)     (share_experience)
```

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 误删 FSTDD002 独有 12 条经验 | C1 先备份；C2 先回灌再删；备份可完整回退 |
| 21 个漂移 eid 裁决错选旧版 | 保留 home 版于 _backup/；默认以 stdd-repo 为准；裁决依据写入 change 记录 |
| 改 vendored 内核 `experience.py` 引入回归 | C5 加 RED→GREEN 契约测试（46 样本）；`pytest upstream/tests` 全量门禁 |
| 删冗余触发 safe-delete 拦截 | 改用同盘 `os.rename` 移回收站，不调 `rm -rf` |
| 索引与 git 跟踪冲突（P2 旧债） | C6→C5 重建后用修复后解析器；跑 `git status` 验证工作树干净 |
| 收敛后 `test_a6` 因未跟踪文件变红 | 收敛产物 commit 后即自愈（判据只排除 `.fstdd/changes/` 下，commit 使文件变 tracked） |
