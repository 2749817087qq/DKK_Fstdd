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

### FSTDD003 每日收纳判据（2026-09-19 确立，替代「目录存在即跳过」）
- **规则**：每日 00:10 收纳自动化（`270a0ea8`）判断「是否已归档」一律用**源/副本 mtime 比较**，不用存在性判断——`源 -nt 副本 → 覆盖刷新`；存在性判断只用于「首次归档」。
- **触发原因**：`fstdd-experience-archive` 副本落后源 11.5 小时（13:25 vs 01:59），被「目录存在即跳过」漏掉，丢失 P15–P18 四条缺陷速查（含 P16 SSH 密钥位置，高）。见 `experiences/FSTDD003-EXP-20260918-ARCHIVE-1.md`。
- **配套动作**：① 复制用 `cp -r "$SRC/." "$DST/"`（`cp -r "$SRC" "$DST"` 会嵌一层同名子目录）；② 刷新后必须 `diff -r` 校验字节一致；③ 一个 skill 只保**单副本**，不双写 `skills-archive/` 与 `artifacts/skills/`（避免两处漂移）；④ 日志须分别记录「刷新 N 个 / 跳过 N 个」，不只记新增。
- **git 提交**：本仓库**禁止 `git add -A`**（会连带暂存 `_scratch/stdd-dev/` 25MB 基线与内嵌 git 仓库，产生坏 gitlink）——一律显式路径提交。仓库 remote 数=0，永不 push。
- **experiences/ 不进 git**：该目录被 `.gitignore`（P11），经验文档留存靠每小时云端回传通道（自动化 `06ec2c4f`），本地 git 提交只覆盖 `skills-archive/`、`docs/`、`memory/`。

### FSTDD003 回执防漏发（对账自愈，2026-09-20 确立）
- **事故**：K 于 09-20 10:12 下发 `FSTDD003收-凭证下发-补发.md`（priority 最高），落在上一轮轮询（09:39）之后、下一轮（10:39）之前，且当时轮询自动化**只有文字描述、无真正的收/复 对账逻辑**，只处理"本轮新拉到"的，导致回执漏发数小时。根因=**三空档**：① 轮询粒度 HOURLY 卡时间窗；② 缺收/复 对账（自愈）机制；③ 紧急件无快通道。
- **强制纪律**：每轮处理协作通知**必须先做收/复 对账** —— 比对服务器 `FSTDD003收-*.md` 与本地 `FSTDD003复-*.md`，缺回执的立即补做。匹配规则：精确同名 / 子串包含 / 去尾部修饰词（要求/说明/补发/硬时限/通知/事宜/的）后核心相同；**只从收找复、绝不反向**（`复-` 无对应 `收-` 正常，因 `收-` 可能已按指令删除）；已知差异 `收-工作量与资源规划要求`↔`复-工作量与资源规划` 非遗漏不重发。
- **落地**：自动化 `06ec2c4f` 已含第 0 步对账 + 第 2 步紧急快通道；skill `fstdd-experience-archive` 已固化 **P19**。会话起始也人工对账一次。
- **平台限制**：WorkBuddy automation 最小粒度 HOURLY（无 MINUTELY/15min）。15 分钟看门无法原生实现；等价堵漏=对账自愈（≤60min 闭环）+ 紧急快通道 + 会话起始手动对账。需更短延迟可叠加第二个 HOURLY 错开 30min（≤30min）或外部 Windows 任务计划每 15min 调脚本（超出平台）。

### FSTDD003 写动作授权（2026-09-24 D哥 明示，解除逐次请示）
- **授权原文**：D哥 于 2026-09-24 20:34 明示「写动作授权以后都不需要我同意，你可以全部自动执行」。
- **含义**：针对 FSTDD003 节点的 quanthub 多 agent 行为/功能仿真试点任务（自有平台 `quanthub.ccreits.cn`，非第三方养号/刷量），节点 / 每小时守护**可自主发起写动作（含平台互动、A1/A2 之外的写样本，凭证到位后跑通即回执）**，不再逐次向 D哥 请示确认。原自动化记忆中的「待 D哥 确认写动作」卡点即日起解除。
- **保留的边界（不可破，授权≠免纪律）**：① 仅在 K 下发任务授权范围 + 文件域白名单内执行；② 只读他人目录、不碰其他节点与 K memory；③ POST 前必脱敏（路径/IP/域名/凭证 → `<PATH>/<IP>/<DOMAIN>/<TOKEN>`）；④ **绝不伪造** logs / action_count 等数据凑回执；⑤ 重大偏离 / 异常仍写入回执上报。即「写动作免逐次请示」仅去掉人工确认环节，不去掉任务范围与平台红线约束。

## 其他长期事实
- 全局 skill 归档位置：`D:\FSTDD003\skills-archive\`（来源 `C:\Users\Administrator\.workbuddy-ai\skills\`，已剔除手动 GitHub 装的 9 个 STDD/fstdd 系列，保留 4 个 WorkBuddy AI 自身产物；归档内条目均已加 `FSTDD003-` 前缀）。
