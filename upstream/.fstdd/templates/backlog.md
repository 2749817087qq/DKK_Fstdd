# FSTDD 候选池（Backlog）

> 执行中发现、但**不属于当前 change 范围**的问题，一律写这里。
> BUILD / DELIVER 阶段只写这里，**不改当前 change 的 proposal 范围** ——
> 这是「反漂移」的第二道闸：发现的额外问题进池子，不进本次改动。
>
> 条目格式：`- [ ] [<change-id>] 一句话描述（发现于 <PHASE>）—— 建议处置`
> 处置后改成 `- [x]` 并注明由哪个 change 修掉的。

## 未处理

<!-- 示例（保留注释作格式参考，实际条目写在下面）：
- [ ] [2026-10-28-anti-drift-gates] `extract-proposal` 把多行 description 按行切碎（发现于 BUILD）—— 另立 change 修解析器
- [ ] [2026-10-27-release] `server` 的 mirror hook 用 `git push --tags` 不带 `--force`（发现于 DELIVER）—— 改成 `+refs/tags/*`
-->

## 已处理
