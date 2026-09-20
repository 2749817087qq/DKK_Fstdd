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
- **git**：显式路径提交 9 个 skill 副本 + memory 日志 + automation memory；未提交 `_scratch/`、内嵌 git repo、`TASK.md`（当日无关修改）、`docs/VERIFY_SPEC_ISSUES_2026-09-20_workbench.md`（当日无关新建）；remote 数=0 未 push。
- **偏离任务书**：未用 `git add -A`（理由同前两轮）。
- 详见 `D:\FSTDD003\.workbuddy-ai\memory\2026-09-20.md` 末尾「00:10 每日收纳」段。

## 下次运行须知（固化判据）
1. **skill 判据 = mtime 比较**，不是「目录存在即跳过」：
   `if [ -d "$DST" ] && [ "$SRC" -nt "$DST" ]; then cp -r "$SRC/." "$DST/"; fi` → 再 `diff -r` 校验。
   `cp -r "$SRC/." "$DST/"`（点号）才不会嵌一层同名子目录。单副本，不双写 `artifacts/skills/`。
2. **skill 扫描范围**：`C:\Users\Administrator\.workbuddy-ai\skills\`（17 个目录）+ `C:\Users\Administrator\.workbuddy-ai\FSTDD\{skills,.fstdd\skills}`。
   实测 D 盘无其它 `.workbuddy-ai/skills`。**避免 `find D:` 全盘扫**（一次跑 4 分钟+，用 Glob 或定向 find）。
3. **git**：显式路径提交，禁 `git add -A`。`experiences/` 被 gitignore，不进 git（靠回传通道留存）。`_scratch/` 绝不提交。
4. **经验文档**：五段式（现象/根因/处理/建议修法/复测建议）；文件名 `FSTDD003-EXP-<YYYYMMDD>-<英文主题>-<序号>.md` 纯 ASCII，中文进 frontmatter `title`；写完须追加 `experiences/FSTDD003-README.md` 索引表并更新文件头说明。
   脱敏底线：不写 IP / home path（`/c/Users/...`）/ 凭证值——服务端会拒收。
5. **去重**：09-15/16/17 系列为历史快照，不新建同名同类。写前 grep 现有 `experiences/` 避免重复主题。
6. **docs/ 长报告**：仅当 ≥3 条属「成体系问题群」时才写；互不相关的单点问题不进 `docs/`。
