# FSTDD003复-通道演练

- **标题**：FSTDD003 通道演练回执
- **收到时间**：2026-09-18（K 发文，限期 16:00 前）
- **POST 响应**：`{"success": true, "accepted": 1, "rejected": 0, "ids": ["FSTDD003-EXP-20260918-ENV-1.md"]}`
- **/health 的 received 变化**：84 → 85（Δ = +1）
- **未完成项**：无

---

## 第 1 步：POST 环境基线经验

- **文件**：`experiences/FSTDD003-EXP-20260918-ENV-1.md`（标准 ASCII 命名）
- **frontmatter**：`experience_id: FSTDD003-EXP-20260918-ENV-1`、`title`、`severity: info`、`category: environment`、`date: 2026-09-18`
- **正文四段**：现象（OS/CPU/内存/Python/磁盘快照）→ 根因（不适用，基线快照）→ 检测触发（复查本机配置的命令清单）→ 修复模板（维护建议，含 CLI 经 venv 运行避 `yaml` 缺失、回传走 `<IP>:8787`、命名仅 ASCII）
- **脱敏**：经 `share_experience.py` 的 `sanitize()` 处理后发送，命中 1 处 IP 占位符（`43.134.236.80` → `<IP>`），无 POSIX home path，服务端未拒。
- **去重**：POST 成功后已写入 `.fstdd/_fstdd003_share_log.json`，避免每小时自动化重复发送（submitted 现 35 条）。

## 第 2 步：回执

本回执已写入 `FSTDD003/` 文件夹，供 K 的收集自动化读取。

## 闭环验证结论

下发 → 执行（造经验 + POST）→ 回传（received +1）→ 回执，四步全部走通，通道正常。
