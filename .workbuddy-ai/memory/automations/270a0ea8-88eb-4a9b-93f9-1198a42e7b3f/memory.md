# 自动化记忆：FSTDD 产物本地收纳整理（每日 00:10）

- automation id: `270a0ea8-88eb-4a9b-93f9-1198a42e7b3f`
- 职责：**仅本地**收纳 FSTDD 产物（skill 副本 + 经验文档）+ 本地 git commit。回传由每小时自动化 `06ec2c4f` 负责，本任务不触外网。
- 时间口径：00:10 运行，收纳「头一天」（运行日 −1）的产物；文件名日期与更新的当日日志均用头一天日期。

## 执行记录

### 2026-09-19 00:10 运行（收纳对象 2026-09-18）— 首轮
- **skill**：刷新 1 个（`fstdd-experience-archive`，副本落后源 11.5h、缺 P15–P18）/ 跳过 17 个（当日无变更）。已把判据改为 mtime 比较。
- **经验文档**：新增 4 条（AUTH-1 / CODE-1 / SCOPE-1 / ARCHIVE-1），09-18 由 6 → 10 条。
- **git**：`9b2c64b`，1 file +29 行。remote 数=0，无 push。
- **偏离任务书**：未用 `git add -A`（会暂存 `_scratch/` 25MB 基线 + 内嵌 git 仓库），改显式路径提交。
- 详见 `D:\FSTDD003\.workbuddy-ai\memory\2026-09-18.md` 末尾「00:10 每日收纳」段。

### 2026-09-20 00:10 运行（收纳对象 2026-09-19）— 第 2 轮
- **skill**：刷新 1 个（`fstdd-experience-archive`，副本落后源 22.6h、缺 P19 SC 撞号速查段）/ 跳过其余 16 个（当日无变更）。`diff -r` 字节一致校验通过。
- **经验文档**：0 新增 —— 09-19 的 4 条 EXP（SPEC-1 / ARCHIVE-1 / ARCHIVE-2 / MUTATE-1）均由人工当日落盘并登记入索引。无未捕获的 FSTDD 特有坑点。
- **git**：显式路径提交（禁 `git add -A`）。未 push。
- 详见 `D:\FSTDD003\.workbuddy-ai\memory\2026-09-19.md` 末尾「00:10 每日收纳」段。

### 2026-09-21 00:10 运行（收纳对象 2026-09-20）— 第 3 轮
- **skill**：刷新 7 个（mtime 判据）—— `skills-archive/`：data-repair-migration（+9.5h）/ fintech-engineer（+2.9h）/ install-github-skill（+2.9h）/ neodata-financial-search（+2.9h）/**新增** memory-detail-sink（09-20 12:50 首次产出）；`artifacts/skills/`：stdd-file-convention（+3.6h）/ stdd-hardening（+3.6h）。跳过其余 11 个。`diff -r` 7/7 通过。
- **经验文档**：**新增 1 条** `FSTDD003-EXP-20260920-RECON-1`（每小时轮询缺收/复 对账，priority-最高任务落 09:39↔10:39 轮询窗口，回执漏发 1h27m；三空档根因 + 防护三件套 + P19 固化 + 磁盘/memory 双向核对纪律）。README 索引同步。
  - 判据：09-20 有 14 次轮询，10:12 是当日唯一「FSTDD 特有事故」（其他都是常规轮询或已入 EXP 的人工事件）；无未捕获的 FSTDD 特有坑点。
- **git**：显式路径提交 9 个 skill 副本 + memory 日志 + automation memory；未提交 `_scratch/`、内嵌 git repo、`TASK.md`（当日无关修改）、`docs/VERIFY_SPEC_ISSUES_2026-09-20_workbench.md`（当日无关新建）；remote 数=0 未 push。commit `5d4b573`（amended，第一次提交 `2d92971` 因 `@'... '@` here-string 语法在标题首尾误留 `@`，已 `--amend -F-` 重写为干净消息）。
- **偏离任务书**：未用 `git add -A`（理由同前两轮）。
- 详见 `D:\FSTDD003\.workbuddy-ai\memory\2026-09-20.md` 末尾「00:10 每日收纳」段。

### 2026-09-22 00:10 运行（收纳对象 2026-09-21）— 第 4 轮
- **skill**：**新增 1 个** `FSTDD003-silent-failure-guards`（09-21 11:18 首次产出，`agent_created: true`，16077B，「静默失败」六模式 + 守卫变异自检）/ 跳过 13 个（mtime 判据）。`diff -r` 字节一致通过。
- **经验文档**：**新增 2 条** —— `FSTDD003-EXP-20260921-RECUR-1`（🔴 对账机制结构性盲区：周期性义务无独立文件名，09-21 全天 22 轮对账「0 待补」全是假阴，欠账 2 天；含与 RECON-1 的边界表）、`FSTDD003-EXP-20260921-RELEASE-1`（升级验证 V2 未通过：commit message 声称升版但树里版本 blob 未更新，3.0.6 blob 在对象库却**未被任何提交引用** —— 对象存在性 ≠ 对象可达性）。README 索引同步（变更日志 1 行 + 表 2 行）。
  - 判据：grep 确认「周期性」「3.0.6」「升级验证」「未被任何提交引用」在既有 EXP 中**零命中**；09-21 已落盘的 4 条 EXP（JUNCTION/LIFECYCLE/DRIFT/FLOW）全部来自 `工作台` change，与本节点 09-21 升级验证/复盘补交是不同事件源。
- **git**：显式路径提交 skill 副本 + memory 日志 + automation memory；`experiences/` 被 gitignore 不进 git；未提交 `TASK.md`（144 行当日无关增量）、`_scratch/`、3 个 `docs/*.md`（人手工产出，非本运行输出）、内嵌 git repo；remote 数=0 未 push。
- **偏离任务书**：未用 `git add -A`（同前 3 轮）。
- 详见 `D:\FSTDD003\.workbuddy-ai\memory\2026-09-21.md` 末尾「00:10 每日收纳」段。

### 2026-09-23 04:08 补跑（收纳对象 2026-09-22）— 第 5 轮（原 09-23 00:10 自动化 499 canceled）
- **背景**：原定 09-23 00:10 的每日收纳自动化运行被调度侧取消（499 canceled，非逻辑错误），未落盘；04:08 手动补跑补齐。
- **skill**：0 新增/刷新（源目录 09-22 无 mtime 变更，最新 09-21）。跳过。
- **经验文档**：0 新增（09-22 全天回传「无新增需回传经验，末份 RELEASE-1」；09-23 新建的 GATE/CI/SCRIPT/DIFF-1 属下轮对象，不动）。
- **git**：显式路径提交 memory 日志（2026-09-22.md）+ 本自动化记忆；未 push。
- **偏离任务书**：未用 `git add -A`。

### 2026-09-25 00:10 运行（收纳对象 2026-09-24）— 第 6 轮
- **skill**：**刷新 1 个** `artifacts/skills/FSTDD003-fstdd-spec/SKILL.md`（源 20347B @ 09-24 13:25，副本 18345B @ 09-17 已 7 天未刷新；`diff -rq` 刷新后 IDENTICAL）/ 跳过 16 个（源 mtime 最新 09-23，09-24 无变更）。
  - **附带检查**：`fstdd-experience-archive/SKILL.md` 源 mtime 09-24 12:27 但副本已 09-24 12:28 双向一致（36922B IDENTICAL），已被前轮或人工操作刷新过，本轮不重复刷。
- **经验文档**：0 新增 —— 09-24 的 5 条 EXP（CANON-1 / CANON-2 / DELIVER-1 / MODE-1 / PHASE-1）均由「工作台」change `2026-09-24-native-wx-ui` 当日 09:37–13:24 落盘、README 索引已同步；均为 FSTDD 特有 CLI 缺陷（`stdd canon generate` 双轨漂移 / `phase advance` 静默降级 / MODE 三字段无 CLI 写入端 / DELIVER 门走不通），符合 EXP 判据，无未捕获坑点。本节点 09-24 其余事件（quanthub 凭证下发 / 写动作授权 / K 催办闭环）属本节点运营事务而非 FSTDD 工具缺陷，仅入当日记忆，不单开 EXP。
- **git**：显式路径提交 3 个文件（skill 副本 + memory/2026-09-24.md + 本自动化记忆），未用 `git add -A`（会连带暂存 `_scratch/` 25MB 基线、`TASK.md` 当日无关修改、`.fstdd/_notices/` 守护轮次产物、`docs/*.md` 人手工报告）。remote 数=0 未 push。
- **偏离任务书**：未用 `git add -A`（同前 5 轮）。

### 2026-09-27 00:10 运行（收纳对象 2026-09-26）— 第 8 轮
- **skill**：**刷新 1 个** `skills-archive/FSTDD003-fstdd-experience-archive/SKILL.md`（源 40573B @ 09-26 12:18，副本 36922B @ 09-24 12:28 已 47h 未刷新、+3651B；`diff -rq` 刷新后 IDENTICAL）/ 跳过其余 12 个（源 mtime 最新 09-21，09-26 无变更）。
- **经验文档**：0 新增。09-26 的 3 条 EXP（DRYRUN-1 / NEWNAME-1 / FAKERED-1）均由「工作台」change `2026-09-26-wx-post-cleanup` 当日自建并登记 README 索引，全部为 FSTDD 特有 CLI 缺陷（`--dry-run` 逐命令失效 / `fstdd new` 双日期前缀静默坑 / 变异自检 `env={...}` 清环境致假红），符合 EXP 判据，无未捕获坑点。本节点其余 7 段事件（6 轮轮询 + 2 次窗口超时同源）属**节点运营 / SOP 匹配**（K 侧窗口卡 5min SLA vs HOURLY 轮询粒度不兼容），RECON-1 / RECUR-1 已覆盖根因，不重复开 EXP。
- **git**：显式路径提交 3 文件（skill 副本 + memory/2026-09-26.md + 本自动化记忆）。**未用 `git add -A`**（会连带 `_scratch/` 25M、`.fstdd/_notices/` 24 项守护产物、`TASK.md`、`docs/*.md`、内嵌 git repo）。remote 数=0 未 push。
- **偏离任务书**：未用 `git add -A`（同前 7 轮）。
- 详见 `D:\FSTDD003\.workbuddy-ai\memory\2026-09-26.md` 末尾「00:10 每日收纳」段。

### 2026-09-26 00:10 运行（收纳对象 2026-09-25）— 第 7 轮
- **skill**：0 新增 / 0 刷新。源目录 09-25 无文件 mtime 变更（最新 09-24 13:25）。22 副本按 mtime 判据全 skip。
  - **新坑（已固化）**：`windows-junction-selfcontained` 被 `[ "$SRC" -nt "$DST" ]` 标记 REFRESH，实为**目录级 mtime 假阳性**（源目录 09-21 10:18 vs 副本 09-21 09:10，`diff -rq` exit=0 字节一致、SKILL.md 同为 14750B@09-21 09:32）⇒ 目录 mtime ≠ 内容 mtime（新建/删除子项、touch 都会改目录 mtime），**必须 `diff -rq` 兜底**后才动手拷。
- **经验文档**：0 新增。09-25 唯一 EXP `FSTDD003-EXP-20260925-CI-1.md`（11441B，20:52）已由「工作台」change 当日自建并登记 README 索引（说明行 + 表行，`grep -c 20260925` = 2）。当日其余 8 段轮询守护 + 3 类节点事件（K 下发交付物已入仓通告 / K 催办升级规程回执 / 对账命名差异白名单化）+ automation memory null 字节覆写，均为本节点运营事务或非 FSTDD 工具缺陷 ⇒ 仅入当日日志，不单开 EXP。
- **git**：显式路径提交 7 文件（`.gitignore` + `MEMORY.md` + `2026-09-23.md` + `2026-09-25.md` + 3 automation memory）。remote 数=0 未 push。`.gitignore` 新增忽略凭证文件 `.fstdd/_fstdd003_quanthub.json`（安全改进，已入库）。未提交 `_scratch/`(25M)、内嵌 git repo、`TASK.md`、`docs/*.md`、`.fstdd/_notices/**`。
- **偏离任务书**：未用 `git add -A`（同前 6 轮）。

### 2026-09-28 00:10 运行（收纳对象 2026-09-27）— 第 9 轮
- **skill**：**刷新 2 个**（mtime 判据 + `diff -rq` 字节级验证均通过）—— `skills-archive/FSTDD003-fstdd-experience-archive/SKILL.md`（源 46002B @ 09-27 18:20，副本 40573B @ 09-27 00:14 已 18h 未刷新、+5429B）、`artifacts/skills/FSTDD003-stdd-file-convention/SKILL.md`（源 15655B @ 09-27 15:44，副本 11061B @ 09-21 已 6 天未刷新、+4594B）。刷新后两处 `diff -rq` 均 IDENTICAL。跳过其余 20 个（源 mtime 均 ≤ 09-26）。
- **经验文档**：**新增 1 条** `FSTDD003-EXP-20260927-SCPLEAK-1.md`（P59）—— 主 `scp -r` 快照窗口内新到/未拷文件被静默漏拷，09-27 单日 3 次触发（14:20/20:04 两次是**新任务卡**落在 scp 4–6min 传输窗口内、21:17 一次是**跨轮累积的 2 份历史老文件**——09-18 通道演练 + 09-24 凭证下发）；根因=`scp -r` 快照式传输（先列目录再传输、无增量语义）+ 对账兜底在**下一轮** HOURLY 才触发。与 RECON-1（缺对账）/ RECUR-1（对账看文件名而非义务）**机制不同**、独立编号；修法首选=主 `scp` 结束后追加 `ssh ls` 差集比对 + 单文件循环补拉（本节点侧自解，无需 K 介入）。判据：`grep -l "2026-09-27\|20260927" experiences/*.md` 仅命中 ANDLIMIT-1 + README（ANDLIMIT-1 是工作台 change 自建的 FSTDD CLI 缺陷，与本节点 SCP 边缘场景不重叠）。README 索引同步（表头说明行 + 表末行）。
- **git**：显式路径提交 5 文件（2 个 skill 副本 + memory/2026-09-27.md + automation memory + EXP 文档不进 git 因 `experiences/` 被 gitignore）。**未用 `git add -A`**（会连带 `_scratch/` 25M、`.fstdd/_notices/**` 数十项守护产物、`artifacts/hardening-src/_backup_stdd_20260916/stdd-repo` 内嵌 git repo、`TASK.md`、`docs/*.md`）。remote 数=0 未 push。
- **偏离任务书**：未用 `git add -A`（同前 8 轮）。
- 详见 `D:\FSTDD003\.workbuddy-ai\memory\2026-09-27.md` 末尾「2026-09-28 00:10 每日收纳」段。

## 下次运行须知（固化判据）
1. **skill 判据 = mtime 比较 + `diff -rq` 兜底**，不是「目录存在即跳过」：
   `if [ -d "$DST" ] && [ "$SRC" -nt "$DST" ]; then` **`diff -rq "$SRC" "$DST"` 有实际差异才** `cp -r "$SRC/." "$DST/"; fi`
   ⚠ 目录级 ` -nt ` 是**假阳性高发源**（第 7 轮实测）：目录 mtime 会被子项增删/touch 改动，与内容新旧无关。
   `cp -r "$SRC/." "$DST/"`（点号）才不会嵌一层同名子目录。单副本，不双写 `artifacts/skills/`。
2. **skill 扫描范围**：`C:\Users\Administrator\.workbuddy-ai\skills\`（17 个目录）+ `C:\Users\Administrator\.workbuddy-ai\FSTDD\{skills,.fstdd\skills}`。
   实测 D 盘无其它 `.workbuddy-ai/skills`。**避免 `find D:` 全盘扫**（一次跑 4 分钟+，用 Glob 或定向 find）。
3. **git**：显式路径提交，禁 `git add -A`。`experiences/` 被 gitignore，不进 git（靠回传通道留存）。`_scratch/` 绝不提交。
4. **经验文档**：五段式（现象/根因/处理/建议修法/复测建议）；文件名 `FSTDD003-EXP-<YYYYMMDD>-<英文主题>-<序号>.md` 纯 ASCII，中文进 frontmatter `title`；写完须追加 `experiences/FSTDD003-README.md` 索引表并更新文件头说明。
   脱敏底线：不写 IP / home path（`/c/Users/...`）/ 凭证值——服务端会拒收。
5. **去重**：09-15/16/17 系列为历史快照，不新建同名同类。写前 grep 现有 `experiences/` 避免重复主题。
6. **docs/ 长报告**：仅当 ≥3 条属「成体系问题群」时才写；互不相关的单点问题不进 `docs/`。
