# 反漂移三道闸：断言证据分级 / 范围锁 + 全局 backlog 池 / DELIVER 冻结

<!-- source_hash: a235823200695d7f -->
<!-- generated_at: 2026-10-29T16:21:51+00:00 -->
<!-- canonical: canonical/proposals/2026-10-28-anti-drift-gates.yaml -->

## Why

FSTDD 的门禁只检查「做完了没」，不检查「说的对不对」。三种漂移形态因此在
BUILD / DELIVER 阶段反复发生，且现有检查拦不住。

形态 A（无证据断言）：AI 凭记忆断言版本/ID/状态，与实际不符。
  实测两例（均发生在本仓 2026-10-27）：
  - commit message 写「v3.4.0 增量」，实际 v3.4.0 早在 10-19 已发布
    （`git tag --sort=-creatordate` 第一条即 `fstdd-v3.4.0`）；
  - memory 记「EXP-2026-0044/0045」，实际不存在（真 ID 是 0043/0038）。

形态 B（范围蔓延）：BUILD 中「顺手」改本 change 之外的东西，无任何拦截。
  根因已定位：`upstream/fstdd/cli/commands/ci.py:417-458` 的 `check_scope_creep`
  判据是「文件路径是否含 `specs/<capability>/` 或 `commands/<capability>`」，
  而本仓代码在 `upstream/fstdd/cli/commands/*.py`，与 capability 名毫无路径
  关系 ⇒ 几乎所有真实代码改动都被判 out_of_scope ⇒ 长期以 WARN 呈现 ⇒
  被当噪声忽略。且它用 `git diff --stat HEAD~1` 只看最近一次 commit（不是
  整个 change 期间），change 刚开始时 `HEAD~1` 不存在 ⇒ 直接 SKIP
  （本仓 MEMORY 记的「(b) 恒 SKIP」即此）。

形态 C（收尾膨胀）：DELIVER 阶段「还应该补个 XXX」，无冻结机制。
  同时 `gate approve --evidence` 的 evidence 是自由文本，写「已完成」也算
  通过 —— 无法区分「有据」与「凭感觉」。

已存在可复用能力（本 change 不新造，只接线）：
- `guard.py:_load_change_scope()` 已能从 `canonical/proposals/*.yaml` 读
  `scope.paths`（失败 fail-closed）；
- `guard.py:_is_in_change_scope()` 已做 `normpath + resolve().relative_to()`
  归一化后匹配（`..` 逃逸挡得住），支持目录前缀 + fnmatch。
二者目前只用于 guard 的相位封锁，`ci` 侧完全没用 ⇒ 范围锁的数据源与判据
都已就位，缺的只是接线。


## What Changes

- 重写 `ci.py:check_scope_creep`：数据源改用 `_load_change_scope`（读
`canonical/proposals/*.yaml` 的 `scope.paths`），判据改用
`_is_in_change_scope`，diff 范围改为 `baseline.base_git_sha..HEAD`
（整个 change 期间累计）。

严格度按「是否声明 scope.paths」**自然分界**（D哥 定：只对本 change 之后
新建的 change 生效，老 change 走 WARN）：
- **已声明 scope.paths** ⇒ 超范围 **FAIL**（严格模式）；
- **未声明 scope.paths** ⇒ **WARN** 并提示「范围锁未生效」（老 change 不爆红）；
- `ci check-drift --strict` 时，未声明亦升为 **FAIL**（收尾自查口径）。
不引入时间基准 —— 声明与否本身就是分界线，且与 C7（模板补 scope 段）
配合后，新 change 从模板生成即带声明。
scope 过宽检测：paths 命中 `upstream/`、`tests/`、`""` 等宽前缀时 WARN 并提示收窄。

- 新增 `ci.py:check_deliver_freeze`：`phase == deliver` 且
`phases.build.status == completed` 时，若 `baseline..HEAD` 的 diff 含
`upstream/fstdd/**` 或 `upstream/tests/**` 的新增文件（A 状态）则 FAIL。
`.fstdd/**` 为归档产出物，豁免。逃生阀：`--allow-late-change "理由"`
显式放行并写入 `design-adjustments`。

- 新增 `ci.py:check_claims`：收尾断言核实 —— 扫描 `baseline..HEAD` 的
commit message，若出现 `vX.Y.Z` 形态版本号，须与
`.fstdd/version.yaml: fstdd_version` 一致；不一致则 FAIL。
这是「形态 A 无证据断言」唯一可机器验证的部分。

- 新增 `fstdd ci check-drift [change] [--json] [--strict]`：把 C1/C2/C3
聚合成人类可读三闸报告（闸1 断言证据 / 闸2 范围锁 / 闸3 收尾冻结），
`--strict` 时任一 WARN 也返回非 0。供 AI 在 BUILD 末与 DELIVER 前自查。

- `gate approve` 新增 evidence 格式校验：evidence 须含至少一个事实标签
`[F]`（形态 `[F]` 或 `[F:来源]`）。**默认即强制**（D哥 定）—— 缺标签时
拒绝并返回非 0，同时打印正确写法示例。
新增 `utils.has_fact_tag()` 作为唯一判据（不散落正则）。
仅作用于 `gate approve`；`gate amend-audit`（补历史审计）不受约束。

- 新增**全局候选池** `.fstdd/backlog.md`（D哥 定：统一一个文件，不按 change 散落）：
执行中发现、但不属于当前 change 范围的问题一律写这里，按 `[<change-id>]` 前缀
归属来源。`fstdd new` **不**生成 per-change 的 discoveries.md。
`check_deliver_freeze` 额外检查：DELIVER 时若 backlog 有未勾选 `- [ ]` 项则
WARN，并区分「本 change 引入的项数」与「历史遗留项数」（不阻断）。
模板双份落盘：`.fstdd/templates/backlog.md` + `upstream/.fstdd/templates/backlog.md`。

- `.fstdd/templates/canonical/proposal.yaml` 增补 `scope:` 段（`mode` +
`paths`），并在 `upstream/.fstdd/templates/canonical/proposal.yaml` 同步
双份一致。这是范围锁能生效的前提 —— 模板无此段是 40+ change 全无声明的根因。

- `fstdd-build` / `fstdd-deliver` skill 增补「反漂移硬规则」章节：断言证据
分级（`[F]` 事实须附命令/文件证据、`[D]` 推导须给链、`[G]` 猜测禁入任务
清单）、范围外发现一律写 `.fstdd/backlog.md`、DELIVER 禁新增功能。
本地 `.fstdd/skills/` 与 `upstream/.fstdd/skills/` 双份一致。


## Capabilities

### New Capabilities

- **anti-drift-gates**：三道闸的机器检查与报告：范围锁（scope.paths 接线）、DELIVER 冻结
（新增源文件拦截）、断言核实（commit message 版本号 vs version.yaml）。
统一入口 `fstdd ci check-drift`。


### Modified Capabilities

- **ci-check-accuracy**：修复 `check_scope_creep` 的判据错配（capability 名 vs 路径前缀）与
diff 范围错配（HEAD~1 vs baseline..HEAD），结论由 WARN 提升为 FAIL。


## Success Criteria

- [ ] SC-01：`fstdd ci check-drift` 命令存在，输出三闸报告（闸1/闸2/闸3 各一节），退出码 0/1 语义正确
- [ ] SC-02：`check_scope_creep` 对**已声明** scope.paths 且改动超范围的 change 返回 FAIL（反例），对范围内改动返回 PASS（正例）
- [ ] SC-03：`check_scope_creep` 在 change **未声明** scope 时返回 WARN（不是 FAIL、不是 SKIP）；`ci check-drift --strict` 下同一情形升为 FAIL
- [ ] SC-04：`check_deliver_freeze` 在 phase=deliver 且新增 upstream/fstdd/** 文件时返回 FAIL，`--allow-late-change` 时放行
- [ ] SC-05：`check_claims` 对 commit message 版本号与 version.yaml 不一致返回 FAIL，一致返回 PASS
- [ ] SC-06：`.fstdd/backlog.md` 模板存在且双份（.fstdd/ + upstream/.fstdd/）逐字节一致；`fstdd new` **不**创建 per-change discoveries.md
- [ ] SC-07：proposal 模板含 scope 段且双份一致；`_load_change_scope` 能从新模板产物读到 paths
- [ ] SC-08：`gate approve --evidence` 缺 `[F]` 标签时**默认拒绝**（非 0 退出 + 打印正确写法）；`gate amend-audit` 不受影响
- [ ] SC-09：新增测试 >= 15 个，且每个判据正例+反例成对
- [ ] SC-10：全量门禁 `pytest upstream/tests tests` 0 failed；`ci check-failures` 0 FAIL
