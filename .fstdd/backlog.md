# FSTDD 候选池（Backlog）

> 执行中发现、但**不属于当前 change 范围**的问题，一律写这里。
> BUILD / DELIVER 阶段只写这里，**不改当前 change 的 proposal 范围** ——
> 这是「反漂移」的第二道闸：发现的额外问题进池子，不进本次改动。
>
> 条目格式：`- [ ] [<change-id>] 一句话描述（发现于 <PHASE>）—— 建议处置`
> 处置后改成 `- [x]` 并注明由哪个 change 修掉的。

## 未处理

- [ ] [2026-10-28-anti-drift-gates] `fstdd extract-proposal` 把多行 `description` 按行切碎，`what_changes` 从 8 项变成 11 项碎片（发现于 SPEC）—— 另立 change 修解析器，按 YAML 列表项聚合而非按行切
- [ ] [2026-10-28-anti-drift-gates] `.fstdd/skills/build.md` 与 `upstream/.fstdd/skills/build.md` 既存 21 行内容漂移（405 vs 384 行，v3.2.0 的 DA-10 记过但未修）（发现于 BUILD）—— 另立 change 对齐
- [ ] [2026-10-28-anti-drift-gates] `.fstdd/skills/deliver.md` 与 upstream 版在第 41 行仍有一处内容差异（BOM 已修）（发现于 BUILD）—— 同上
- [ ] [2026-10-28-anti-drift-gates] `fstdd ci check-failures` 的检查项编号只到 (l)，本轮新增用了 (n)/(o)/(p)，(m) 空缺（发现于 BUILD）—— 补 (m) 或重排编号并同步文档
- [ ] [2026-10-28-anti-drift-gates] `ci check-scope` 等单检查子命令的 `--strict` 语义与 `check-drift --strict` 不统一（前者无 strict 开关）（发现于 BUILD）—— 统一口径
- [ ] [2026-10-28-anti-drift-gates] `fstdd new` 生成的 `canonical/specs/{code,agent}/<change-name>.yaml` 占位模板需手工删除才能通过 spec 校验（发现于 SPEC）—— `new` 应不生成占位或 `ci` 应忽略空占位
- [ ] [2026-10-27-release] `server` 裸库的 mirror hook 用 `git push --tags`（不带 `--force`），重打 tag 后 GitHub 上的 tag 停在旧 commit，须人工到 server 上强推（发现于 DELIVER）—— 改成 `git push --force --tags` 或 `+refs/tags/*`
- [ ] [2026-10-27-release] 本机无 GitHub 凭据（`gh` 未登录、GCM 空），发布 Release 须从会话转录里挖历史 PAT（发现于 DELIVER）—— 建议 `gh auth login` 一次并轮换旧 PAT

## 已处理
