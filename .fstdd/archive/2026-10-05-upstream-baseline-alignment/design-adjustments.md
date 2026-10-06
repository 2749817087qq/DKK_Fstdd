# Design Adjustments — 2026-10-05-upstream-baseline-alignment

> FSTDD 硬性约束 #2：**绝不静默修改设计** —— 任何偏离 proposal / spec 基线的实现决策
> 必须在此记录（含理由 + 影响 + 是否有后续 change 承接）。
> 本文件汇总 Phase 3 BUILD 的 `pending-adjustments.yaml`（ADJ-001 / ADJ-002 / ADJ-003，均为「小偏离」）。

---

## ADJ-001 · `verify_eol.py` 允许清单增补 `NOTICE.md`（门禁相容性）

- **基线**：`design.md` 决策 5 的改动边界为「只动活体声明面 + 新增 `docs/UPSTREAM_BASELINE.md`」，
  未包含 `tools/verify_eol.py`。
- **实现**：在 [`verify_eol.py`](file:///e:/FSTDD/stdd-repo/tools/verify_eol.py#L40-L44)
  的 `ALLOWED_DIFF_EXACT` 增补精确项 `NOTICE.md`（附原因注释）。
- **理由**：`verify_eol` 的 TC-EOL-005（索引零内容变更）以
  `ALLOWED_DIFF_PREFIX=("tools/","docs/","skills/")` + `ALLOWED_DIFF_EXACT={"README.md",".gitignore"}`
  判定「行尾治理是否引入非预期变更」。根级 `NOTICE.md` 属决策 1/5 的必改清单，却既不在前缀内、
  也不在精确项内 → 其 diff 会被误判为「非预期变更」→ TC-EOL-005 假失败。
- **影响**：低。仅扩展脚本自带的允许清单扩展位（该扩展位注释即写明「无法用前缀表达的散落文件，
  新增时必须注明原因」）；不改任何 TC 判据、不影响其它文件判定语义。影响面：单文件。
- **核验**：grep 全仓，`ALLOWED_DIFF_EXACT` 内容无任何测试钉住（仅命中 `verify_eol.py` 自身 +
  1 处归档 test-report 的引用）→ 不破坏既有门禁。改后 `verify_eol` 7/7。
- **承接**：无。

## ADJ-002 · 新增产物 `git add` 进暂存区（上游门禁相容性）

- **基线**：`design.md` 约束「全量 `pytest upstream/tests` 须保持 0 failed」。
- **实现**：将 4 个新产物 `git add` 进暂存区（`A ` 状态）：
  `docs/UPSTREAM_BASELINE.md` + `tests/test_version_nomenclature.py` +
  `tests/test_install_version_derivation.py` + `tests/test_upstream_baseline.py`。
- **理由**：上游自带门禁
  [`test_repo_home.py::test_a6_no_stray_untracked_files`](file:///e:/FSTDD/stdd-repo/upstream/tests/test_repo_home.py#L132-L142)
  要求「除 `.fstdd/changes/` 下的在办 change 外不得有 untracked 项」。BUILD 阶段新文件尚未提交，
  若不暂存则被判为「遗留垃圾」而 FAIL（实测 1 failed）。
- **影响**：极低。仅索引状态；不改文件内容、不改判据、不改工作区。
- **核验**：暂存前 `test_repo_home` 1 failed；暂存后 16 passed / 3 skipped。
- **承接**：无。（教训：新增交付物应在 Phase 3 尽早进入索引，避免与上游 untracked 门禁相冲。）

---

## ADJ-003 · `verify_eol.py` 允许前缀增补 `.fstdd/experiences/`（门禁相容性）

- **基线**：`design.md` 改动边界未含 `tools/verify_eol.py: ALLOWED_DIFF_PREFIX`；而 `build.md` 的 C5
  要求在 BUILD 期「自动记录/更新经验库」。
- **实现**：在 [`verify_eol.py`](file:///e:/FSTDD/stdd-repo/tools/verify_eol.py#L39-L42)
  的 `ALLOWED_DIFF_PREFIX` 增补前缀 `.fstdd/experiences/`（附原因注释）。
- **理由**：本次失败模式检查复现了两条既有经验（EXP-2026-0016 / EXP-2026-0015），按纪律需回填
  证据、递增 `occurrences`；这些条目是**已跟踪文件**。而 TC-EOL-005 的允许面
  `("tools/","docs/","skills/")` + `{"README.md",".gitignore","NOTICE.md"}` 不含 `.fstdd/experiences/`
  → 经验更新被判「非预期变更」→ TC-EOL-005 假失败（实测 6/7）。
- **影响**：低。仅扩展允许前缀（与 `tools/` 同类：正常开发活动产物）；不改任何 TC 判据。
- **核验**：grep 全仓，`ALLOWED_DIFF_PREFIX` / `ALLOWED_DIFF_EXACT` 内容无任何测试钉住
  （仅命中 `verify_eol.py` 自身）→ 不破坏既有门禁。改后 `verify_eol` 7/7。
- **承接**：无。

---

## 汇总

| ID | 类别 | 严重度 | 承接 change |
|----|------|--------|-------------|
| ADJ-001 | 门禁相容性（允许清单 · NOTICE.md） | 低 | 无 |
| ADJ-002 | 门禁相容性（索引状态 · 新产物暂存） | 极低 | 无 |
| ADJ-003 | 门禁相容性（允许前缀 · 经验库） | 低 | 无 |

**design_adjustments.count = 3**（均为小偏离，均已记录后继续；无重大偏离）