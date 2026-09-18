# 项目长期记忆 (MEMORY.md)

> 工作区：FSTDD003 ｜ 维护规则：只记录跨会话有价值、长期有效的约定与结论，不记临时路径/临时错误。

## 项目约定 / Conventions

### FSTDD 回传命名规范（2026-09-17 确立）
- **规则**：所有因 fstdd 流程要「回传」回去的 **skill 与文档**，其名称 / 文件名最前面**必须加前缀 `FSTDD003`**。
- **目的**：便于识别这些产物归属于本工作区（FSTDD003），与全局其他 skill / 文档区分开，明确归属。
- **适用范围**：因 fstdd 产生、需要回传的 skill 目录名与文档文件名（例如 `FSTDD003-xxx-skill`、`FSTDD003-<report>.md`）。
- **注意（2026-09-17 补充）**：本工作区本地归档副本 `D:\FSTDD003\skills-archive\` 内的条目（4 个 skill 目录 + 3 个内部状态文件）**也已统一加 `FSTDD003-` 前缀**（如 `FSTDD003-data-repair-migration`），便于归属本工作区；原文件名前导的 `.`/`_` 已去除，统一为 `FSTDD003-*` 形式。
- **执行提醒**：每次要回传 fstdd 相关 skill / 文档前，先确认名称已带 `FSTDD003` 前缀再操作。
- **已上升为全局硬约束（2026-09-17）**：上述 FSTDD003 留存/命名约定已写入 WorkBuddy AI 全局记忆 `~/.workbuddy-ai/MEMORY.md`（「FSTDD 产物必须留存副本到 FSTDD003」）。因 FSTDD 处于试运行阶段，凡 FSTDD 产出的 skill / 经验文档都必须在 `D:\FSTDD003` 留副本，跨项目生效。
- **已落地的存量前缀（2026-09-17）**：工作区内所有「fstdd 回传的 skill/文档」存量均已加 `FSTDD003-` 前缀——
  - `skills-archive/`：7 项（4 skill 目录 + 3 内部状态文件）
  - `artifacts/skills/`：10 个 fstdd 产出 skill 目录
  - `experiences/`：29 个回传经验文档
  - `artifacts/identity/`：4 个身份文档（IDENTITY/MEMORY/SOUL/USER.md）
  - `MANIFEST.md` 对 `回传指引-如何贡献经验.md` 的引用已同步改为 `FSTDD003-回传指引-如何贡献经验.md`。
- **明确不改动的项（历史快照 / 活引用，改了会失真或断链）**：`artifacts/memory/` 历史日志、`artifacts/hardening-src/` 的 `_backup_*` 快照与 `pending-push/*.patch` 补丁、`artifacts/hardening-src/guard-block.md`（被活脚本 `apply.py` 引用）、`install.sh.fixed`（被 `MANIFEST.md` 与历史日志引用）、`docs/` 旧日志、`artifacts/hardening/`（空目录）。

### FSTDD003 协作通知处理（2026-09-18 确立）
- **性质**：云服务器 `ubuntu@43.134.236.80:/home/ubuntu/fstdd-notices/FSTDD003/` 下发的 `FSTDD003收-*.md` 即「协作通知」（K 按 Slice 拆分下发的开发/盘点/演练任务）。
- **处理准则（D哥 2026-09-18 明确）**：协作通知到货后**直接执行并回传**，不再逐项请示。
- **执行闭环**：每小时轮询自动化 `06ec2c4f`（ACTIVE）已实现 —— 拉取 notices → 按文件要求执行 → 交付三件套（`<编号>-<slice>.patch` + `-tests.txt` + `FSTDD003复-<主题>.md`）scp 回本节点目录 → `/health` 自查 → 本地 git commit（不 push）。
- **纪律边界（不可破）**：① 只读他人目录、不碰其他节点与 K 的 memory；② 文件名仅 ASCII（`FSTDD003-EXP-<日期>-<编号>.md`，中文进 frontmatter `title`）；③ POST 前必脱敏（路径/IP/域名/凭证 → `<PATH>/<IP>/<DOMAIN>/<TOKEN>`）；④ GitHub 仅本地 commit 不直推；⑤ 文件域白名单外一律不改——若验收要求迫使扩展文件域（如 S3 的 `tools/check_timestamps.py`），须在回执中**显式记录偏离，不得静默**；⑥ 审计表等共享产物归 S5 归口刷新，本节点不代删。

## 其他长期事实
- 全局 skill 归档位置：`D:\FSTDD003\skills-archive\`（来源 `C:\Users\Administrator\.workbuddy-ai\skills\`，已剔除手动 GitHub 装的 9 个 STDD/fstdd 系列，保留 4 个 WorkBuddy AI 自身产物；归档内条目均已加 `FSTDD003-` 前缀）。
