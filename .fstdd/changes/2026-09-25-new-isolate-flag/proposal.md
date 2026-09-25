# 让「一 change 一隔离环境」可选且可见：复活 --isolate 开关 + new 提示 + init 配置

<!-- source_hash: 44ade3359d6f1ade -->
<!-- generated_at: 2026-09-25T16:53:08+00:00 -->
<!-- canonical: canonical/proposals/2026-09-25-new-isolate-flag.yaml -->

## Why

FSTDD 的 change 默认活在主工作区，没有任何隔离策略；而 CLI 里唯一的隔离能力
`--parallel` 已不可达（argparse 未注册 ⇒ `stdd new --parallel` 直接报
unrecognized arguments），其调用的 `_setup_parallel_worktrees()` 恒不执行 = 死代码。
后果有三：① ACTIVE_CHANGE 停只读相位即冻结整个工作区（阶段劫持，W5 只做范围
收窄，非根治）；② 同一工作区并发写同一文件会产生冲突（实测提交 c0fe872
「guard.py UU 冲突合并」）；③ 依赖「工作区干净」的测试易被无关改动触红
（test_a6_d_repo_worktree_clean）。此外 `stdd init` / `stdd new` 零交互、零提示，
用户无从得知可以隔离。


## What Changes

- 复活并更名隔离开关：`stdd new --isolate {none|worktree|branch}`，默认 none（维持现状，零行为漂移）。
- `--isolate worktree` 时按 change 名建独立 git worktree；显式声明分支创建策略（是否 -b、分支名规则），不使用隐式同名分支。
- `stdd new` 结束时打印一行提示：当前为共享工作区模式 + 如需隔离的完整命令（不阻塞、不交互）。
- `stdd init` 时把建议的隔离策略写入 `.fstdd/config.d/project.yaml`（自动化可读，零交互）。
- 清理死代码：移除不可达的 `--parallel` 分支或将其并入 `--isolate`，消除「看似有功能实则不可达」的假象。

### New Capabilities

- **change-isolation**：创建 change 时可显式选择隔离形态（共享工作区 / git worktree / 独立分支）

### Modified Capabilities

- **stdd-new**：stdd new 增加 --isolate 参数与一行提示；移除不可达的 --parallel 分支
- **stdd-init**：stdd init 写入建议隔离策略到项目配置

## Success Criteria

- [ ] `stdd new x --isolate worktree` 在 git 仓内成功建出独立 worktree，且 worktree 内 ACTIVE_CHANGE 与主工作区互不干扰（实测：两处同时有不同 change 处于只读相位，各自只冻结自己作用域）
- [ ] `stdd new x`（无参数）行为与现状逐字一致（默认 none，零漂移）
- [ ] `stdd new --isolate branch` 创建命名明确的分支，不产生隐式同名分支
- [ ] `stdd new --parallel` 不再以「看似可用」形态存在（要么并入 --isolate，要么彻底移除并留 CHANGELOG 说明）
- [ ] `stdd new` 结束输出包含隔离提示行；`--help` 列出 `--isolate`
- [ ] `stdd init` 后 `.fstdd/config.d/project.yaml` 含隔离策略字段，且旧配置无该字段时行为不变
- [ ] 非 git 仓库下 `--isolate worktree|branch` 给出明确报错（不静默降级为 none）
- [ ] 新增用例覆盖上述各点；全量套件 0 failed；吞异常零漂移哨兵通过
