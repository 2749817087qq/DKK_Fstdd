# FSTDD003复-经验回传要求

- **标题**：FSTDD003 经验回传要求落实回执
- **收到时间**：2026-09-18（K 发文）
- **执行结果**：三项动作全部完成（见下）
- **未完成项与原因**：无。试运行数据已停发、命名已合规、2 条被拒已查明并补发。

---

## 1. 试运行数据停止重发 ✅
- **增量去重机制**：`.fstdd/_fstdd003_share_log.json` 记录已提交 EXP-ID；helper `tools/fstdd003_daily_share.py` 只发「未记录过」的新经验。服务端不去重（同 ID 重复会累加计数），本地去重兜底，杜绝重发。
- **斩断原始工具重发源**：`tools/share_experience.py` 的 `collect_local()` 读 `.fstdd/experiences/EXP-*.md`，原先含 26 个试运行 `EXP-*.md`。已将这 26 个文件迁至 `.fstdd/_legacy_trial/` 归档（**未删除**），`.fstdd/experiences/` 现已清空——原始工具再被调用也不会重发试运行数据。
- 根目录 `experiences/` 内的试运行日期文件（`FSTDD003-EXP-20260915/16/17-*`、哈希 ID 共 26 个）也已迁至 `.fstdd/_legacy_trial/`；现 `experiences/` 仅留 8 条真实增量 + 索引/指南。

## 2. 命名合规 ✅
- 全部经验文件统一为 ASCII：`FSTDD003-EXP-<日期>-<编号>.md`。`experiences/` 目录经 Python 校验**无任何非 ASCII 文件名**。
- 原 `FSTDD003-回传指引-如何贡献经验.md`（即 K 所见 `FSTDD003-____-______.md` 的来源）是「回传指引」指南、非经验文档。已改名为 ASCII `FSTDD003-CONTRIB-GUIDE.md`，并更新 `MANIFEST.md` 引用。该文件不匹配 `FSTDD003-EXP-*.md` glob，本就不会进 inbox。
- 中文标题统一写入文件 frontmatter 的 `title` 字段，不进文件名。

## 3. 2 条被拒原因查明并补发 ✅
- **被拒条目**：`FSTDD003-EXP-20260917-EXTRACT-1`、`FSTDD003-EXP-20260917-MULTIWS-1`。
- **根因**：正文含 POSIX home 路径（`/c/Users/Administrator/...`、`~/.workbuddy-ai/...`），服务端校验 `content rejected: contains POSIX home path`。
- **修复**：绝对路径替换为占位符 `<USERPROFILE>/`、`<WORKBUDDY_HOME>/`，脱敏后单独 POST 重提 → 返回 `{"success": true, "accepted": 2, "rejected": 0}`。两文件已就地脱敏（grep 复核无残留 home 路径）。

## 现状小结
- `experiences/` 现含 8 条真实增量（K 点名：EXTRACT-1 / MULTIWS-1 / REGISTRY-1 / CRIT-1 / DESIGN-1 / GUI-1 / GUI-2 / GUI-3），全部 ASCII、已脱敏、已在服务端落地。
- 回传通道统一走 `http://43.134.236.80:8787`（POST `/api/share-experience`），不再直推 GitHub；GitHub 仅本地 commit。
- 每小时轮询自动化已建（拉 notices→执行→POST→回执），待补 SSH 取件 / 回执写回服务器步骤。
