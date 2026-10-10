# Phase Context — experience-library-consolidation（Phase 2 → 3 交接）

## 关键决策（Phase 2 锁定）

1. **修复 `_load_experience` 双块解析（AMD-002，实测驱动）**：P0-pre change（1555de9）只修了索引对账与基线审计，**未改解析器**。实测 `experience list` 仍只取首个 frontmatter 块（丢真身）。本 change 必须自己修，否则收敛 = 把坏数据搬进权威库。
2. **锚定等级 L1 → L3（AMD-001）**：因 `safety_critical=true`，按 Step 4.5 硬规则至少 L3；引用 `2026-10-10-p0-pre-audit-baseline` 的备份+幂等模式。
3. **权威库锁定 `stdd-repo/.fstdd/experiences`**；FSTDD003 / home-FSTDD 0 独有，降为只读参考；FSTDD002 有 12 独有须先回灌。
4. **21 个漂移 eid 默认以 stdd-repo 为准**，裁决依据落盘（SC-005 medium 置信度，用户已确认此默认策略）。
5. **迁移脚本 `consolidate_experiences.py` 幂等 + `--dry-run` + `--verify`**；删冗余走同盘 `os.rename` 移回收站（非 `rm -rf`，沙箱 safe-delete 拦截）。

## 用户关注点

- 不丢 FSTDD002 独有 12 条经验（已纳入 C2 + 备份兜底）
- 21 漂移裁决须留痕
- 索引不被读命令写脏（P2 旧债，C6→C5 在修复后解析器上重建）
- 收敛后经验库「先可信、再可见」（承接 P0-pre）

## 产出物

- `design.md`、`canonical/specs/code` + `canonical/specs/agent`、`test-plan.md`（11 TC：P0×4 / P1×6 / P2×1）
- `specs/experience-library-consolidation/spec.md`（Gate 2 渲染）
- `canonical/proposals/...yaml`（anchoring L3 + C5 修解析器 + C8 脚本）

## 风险预警（Phase 3 须注意）

- 改 vendored 内核 `upstream/fstdd/experience.py` → 须跑全量 `pytest upstream/tests` 门禁防回归
- 删冗余触发 safe-delete 拦截 → 必须用 `os.rename` 移回收站，不调 `rm -rf`/`shutil.rmtree`
- 收敛产物为未跟踪文件 → `test_a6` 在 commit 前变红，commit 后自愈（判据排除 `.fstdd/changes/`）
- 改 `upstream/fstdd/` 属 vendored 内核修改，须 D哥 知情（已在 proposal/design 明示）
