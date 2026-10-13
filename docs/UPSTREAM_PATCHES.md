# UPSTREAM_PATCHES.md — vendored 内核补丁登记表

> 单一事实源：凡对 `upstream/` 内任何文件的修改，**必须**先于修改在此登记。
> `fstdd validate` 应对"未登记的 upstream/ 修改"报非零退出（检查项实现属 change 2026-10-10-p0-pre-audit-baseline，Gate 2 定案）。
> 同步上游（E 轴/K 轴变化）时，按"回退版本"列逐条核对是否已被上游吸收。

**基线**：E=3.0.5 / K=3.1.0 / R=3.3.8（详见 docs/UPSTREAM_BASELINE.md）

| # | 文件 | 行号 | 修改原因 | 关联上游 issue/PR | 登记日期 | 登记人 | 预期回退版本 |
|---|---|---|---|---|---|---|---|
| 1 | upstream/fstdd/cli/commands/canon.py | 38/50/613/699 | 新增 `cmd_canon_merge`（DELIVER 自动合并根 canonical 的命令，613 行）+ `_root_canonical_dir`（根 canonical 唯一定义点，38 行）；`_get_canon_dir` 无 change_name 分支由 `.fstdd/canonical` 改为 `_root_canonical_dir`（50 行，修复两个根 canonical 错位，EXP-2026-0026）；`_dispatch` 注册 merge（699 行） | 待上游 PR（新增命令，无既有对应） | 2026-10-13 | FSTDD-F | 3.3.8 |
| 2 | upstream/fstdd/cli/__init__.py | 312/313 | 在 `canon` 子解析器下注册 `merge` 子命令（含 `change_name` 位置参数；`--dry-run` 继承父解析器） | 待上游 PR（新增命令，无既有对应） | 2026-10-13 | FSTDD-F | 3.3.8 |
<!-- 示例行格式（勿放入表内）：| 1 | upstream/fstdd/cli/experience.py | 428 | <原因> | <issue/PR> | <日期> | <登记人> | <回退版本> | -->

## 待登记（已识别未动手）
- upstream/fstdd/cli/experience.py:428 — 解析器缺陷（Phase 1.1 修复批次动手前必须先登记）
- upstream/fstdd/ 71 处 write_text() 未传 newline= — CRLF（走上游 PR 路线，评审已裁定不直接改）
