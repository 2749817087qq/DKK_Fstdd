# FSTDD 候选池（Backlog）

> 执行中发现、但**不属于当前 change 范围**的问题，一律写这里。
> BUILD / DELIVER 阶段只写这里，**不改当前 change 的 proposal 范围** ——
> 这是「反漂移」的第二道闸：发现的额外问题进池子，不进本次改动。
>
> 条目格式：`- [ ] [<change-id>] 一句话描述（发现于 <PHASE>）—— 建议处置`
> 处置后改成 `- [x]` 并注明由哪个 change 修掉的。

## 未处理

- [ ] [2026-10-31] **`git checkout --` 对「被外部改坏但 size/mtime 未变」的文件会静默跳过** —— 实测 `tests/test_installation_id_traceability.py` 被 null 填充（3767 字节里 2897 个 `\x00`，从 offset 870 起连续填充），`git status` **无输出**、`git checkout --` **无效**（git 按 stat 缓存认为「无修改」），只能 `git show <commit>:<path>` 取 blob 再 `write_bytes` 强制重写才恢复。后果：pytest 报 `SyntaxError: source code string cannot contain null bytes` ⇒ **整个全量门禁收集失败**（只跑出 1 个 testcase）。建议给 `ci check-failures` 加一项「源码文件 null bytes 扫描」（发现于 BUILD）

- [ ] [2026-10-31-share-scp-tar-packing] **SC-03 未达标**：tar 打包后真实链路 **54s**（目标 <30s；改前 319s = 5m19s）。差距来自 5 次 ssh 往返（可达性 / 目录可写 / mkdir / 解包 / 数量校验，每次 2-5s）+ 112 文件的脱敏处理。进一步优化空间：① 合并 ssh 往返（一次连接跑多命令）② 脱敏并行化 ③ 已知可用时跳过可达性探测。核心目标（消除 timeout 假失败）已达成 —— 54s 远低于任何合理 timeout（发现于 BUILD）

- [ ] [2026-10-31] **FSTDD 缺「修复层级」声明机制** —— AI 倾向用**临时一次性脚本**让检查变绿，而非修掉让检查变红的根因，且流程没有规定「必须改生产代码」。本次会话实测 3 例：① `tmp-refresh-audit2.py` 刷审计表行号（生成逻辑未修，下次改代码还会漂）② 手动 `cp` 合并 canonical specs（`fstdd archive` 只合 MD 层的缺陷未修）③ 从会话转录挖 PAT + 临时 askpass（后由 `gh auth login` 根治，属正面案例）。建议：proposal 加 `fix_level: root_cause|symptom` + `followup_change`（symptom 时必填），并给 `ci check-drift` 加闸4「task_type=code 但 diff 无生产代码改动 ⇒ WARN」（发现于 SPEC）
- [ ] [2026-10-31] `safe-delete` 的 `SAFE_DELETE_BULK_GUARD_ERROR state lock timeout` 会拦住**所有**删除（bash `rm` 与 Python `Path.unlink()` 都拦），本轮删 `fstdd new` 生成的占位 spec 只能改用 `mv` 移走 —— 属环境级限制，建议给 `fstdd new` 加 `--no-placeholder-spec` 或让 `ci` 忽略空占位（发现于 SPEC）

- [ ] [2026-10-30-v3.6.0] `tools/share_experience.py` 的 scp 通道**逐文件传输**：112 个经验需 **5 分 19 秒**，若外层 timeout < 5min 会被 SIGTERM 杀掉 ⇒ `_scp_dir` 返回非 0 ⇒ 降级 inbox（缺 token ⇒ 401）⇒ 审计记 `endpoint/failure`，**但部分文件其实已落盘**（实测 13/25/37 个的三次半成品）。症状极具迷惑性：服务器上明明有文件，审计却说失败（发现于 DELIVER）—— 建议改成 tar 打包后单次 scp，或分批（每批 30）+ 内部超时 + 部分失败重试
- [ ] [2026-10-30-v3.6.0] `fstdd archive` **只合并 MD 层 specs**（`.fstdd/specs/`），不合并 canonical YAML 层（`canonical/proposals/` 与 `canonical/specs/{code,agent}/`）—— 但输出说「Specs 已合并到 specs/」，易误以为四层都合了（发现于 DELIVER）—— 归档应四层齐合，或在输出里明示只做了 MD 层
- [ ] [2026-10-28-anti-drift-gates] `fstdd extract-proposal` 把多行 `description` 按行切碎，`what_changes` 从 8 项变成 11 项碎片（发现于 SPEC）—— 另立 change 修解析器，按 YAML 列表项聚合而非按行切
- [ ] [2026-10-28-anti-drift-gates] `.fstdd/skills/build.md` 与 `upstream/.fstdd/skills/build.md` 既存 21 行内容漂移（405 vs 384 行，v3.2.0 的 DA-10 记过但未修）（发现于 BUILD）—— 另立 change 对齐
- [ ] [2026-10-28-anti-drift-gates] `.fstdd/skills/deliver.md` 与 upstream 版在第 41 行仍有一处内容差异（BOM 已修）（发现于 BUILD）—— 同上
- [ ] [2026-10-28-anti-drift-gates] `fstdd ci check-failures` 的检查项编号只到 (l)，本轮新增用了 (n)/(o)/(p)，(m) 空缺（发现于 BUILD）—— 补 (m) 或重排编号并同步文档
- [ ] [2026-10-28-anti-drift-gates] `ci check-scope` 等单检查子命令的 `--strict` 语义与 `check-drift --strict` 不统一（前者无 strict 开关）（发现于 BUILD）—— 统一口径
- [ ] [2026-10-28-anti-drift-gates] `fstdd new` 生成的 `canonical/specs/{code,agent}/<change-name>.yaml` 占位模板需手工删除才能通过 spec 校验（发现于 SPEC）—— `new` 应不生成占位或 `ci` 应忽略空占位
- [ ] [2026-10-27-release] `server` 裸库的 mirror hook 用 `git push --tags`（不带 `--force`），重打 tag 后 GitHub 上的 tag 停在旧 commit，须人工到 server 上强推（发现于 DELIVER）—— 改成 `git push --force --tags` 或 `+refs/tags/*`
- [ ] [2026-10-27-release] 本机无 GitHub 凭据（`gh` 未登录、GCM 空），发布 Release 须从会话转录里挖历史 PAT（发现于 DELIVER）—— 建议 `gh auth login` 一次并轮换旧 PAT

## 已处理

- [x] [2026-10-31] 服务器 `/home/ubuntu/fstdd-inbox/` 的 3 个不完整批次 —— 已由 D哥 确认删除（2026-10-31 20:46，精确路径逐个 `rm -rf`，删后验证 3 个 GONE、完整批次 `203459` 的 112 files 完好）
