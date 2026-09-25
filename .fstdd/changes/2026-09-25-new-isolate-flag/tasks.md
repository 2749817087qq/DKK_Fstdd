# v3.0.7 任务清单 — change-isolation

> Change：`2026-09-25-new-isolate-flag` ｜ Phase 3 BUILD ｜ base_git_sha：`4eec636`
> 裁定依据：design.md「裁定记录」ISO-1/2/3（总工裁定，D哥 全权授权）

## 切片总览

| Slice | 主题 | 优先级 | 覆盖 TC | 依赖 |
|---|---|---|---|---|
| 1 | 隔离形态解析 + 配置回落 | **P0** | 002, 003, 015, 016 | — |
| 2 | 失败前置与 git 前置检查 | **P0** | 006, 007, 008 | 1 |
| 3 | worktree 创建 + 脚手架落点切换 | **P0** | 001, 004, 009, 010 | 2 |
| 4 | branch 形态 | P1 | 005 | 2 |
| 5 | 门禁随 worktree 生效（ISO-1） | P1 | 019, 020 | 3 |
| 6 | 提示行 + init 配置写入 | P1 | 011, 012, 013, 014 | 1 |
| 7 | 死代码移除 + CHANGELOG | P1 | 017, 018 | 1 |
| 8 | 质量验证与交付证据 | **P0** | 021, 022, 023 + agent_spec | 1–7 |

**执行纪律**：每片按 RED → GREEN → REFACTOR；**每片通过后才进下一片**。
每片结束时记录 per-slice 证据（命令 + 输出摘要 + 观测时刻）。

---

## 1. 隔离形态解析 + 配置回落（P0）✅ 已完成 — commit `e883547`

- [x] 1.1 在 `cli/__init__.py` 的 `p_new` 注册 `--isolate`（`choices=["none","worktree","branch"]`，`default=None`）
- [x] 1.2 新增 `_resolve_isolate_mode(args, project_root) -> str`：显式参数优先 → 读 `project.yaml` 的 `isolation.default` → 缺失/不可解析/非法一律回落 `none`（fail-safe 方向锁）
- [x] 1.3 新增 `_load_isolation_config(project_root) -> dict`，只读不写，异常吞掉并回落默认
- [x] 1.4 RED：写 TC-ISO-003（`--help` 暴露三取值）
- [x] 1.5 RED：写 TC-ISO-002（无 `--isolate` + 无配置 ⇒ 零漂移：**不得调用 git**、**不得写配置**）
- [x] 1.6 RED：写 TC-ISO-015（`isolation.default: worktree` 被消费；显式参数压过配置）
- [x] 1.7 RED：写 TC-ISO-016（配置缺失 / YAML 坏 / 取值非法 / 结构不符 ⇒ 均回落 none）
- [x] 1.8 GREEN + 跑 `test_new.py` / `test_new_coverage.py` / `test_init.py` 确认无回归 ⇒ **28 passed**（12 新 + 16 既有）
- [x] 1.9 **BUILD 分期守卫**：`worktree`/`branch` 尚未实现 ⇒ 出声拒绝 `exit 1`，且不留 change 目录（Slice 3/4 实现后删除）

**片内实测发现（记录）**：`utils.fix_windows_encoding()` 会用
`io.TextIOWrapper(sys.stdout.buffer, ...)` **替换 `sys.stdout`** ⇒ 进程内调用 `main()` 时
help 输出绕过 capsys 捕获（实测 `out` 为空），且该替换会**残留影响后续用例**。
故 TC-ISO-003 改为**子进程调真 CLI**（同时也是更强的端到端证据）。

**RED 证据形态**：新 API 切片的 RED 表现为 collection error
（`ImportError: cannot import name '_load_isolation_config'`）。行为级 RED 自 Slice 2 起才有意义。

**计划调整**：原属 Slice 6 的「收尾提示行」（6.1）已**前移到本片**（`_print_isolation_hint`），
以免出现「参数已注册但无人使用」的中间态；Slice 6 只剩 init 配置写入。

**失败模式检查**：配置读取失败回落方向已验证为 `none`（TC-ISO-016b/d 专门断言**不是** `worktree`）。

## 2. 失败前置与 git 前置检查（P0）✅ 已完成 — commit `5e8953f`

- [x] 2.1 新增 `_git_worktree_root(project_root) -> Path | None`（`git rev-parse --show-toplevel`）
- [x] 2.2 新增 `_branch_exists(project_root, branch) -> bool`（`git rev-parse --verify`）
- [x] 2.3 新增 `_is_worktree_dirty(project_root) -> bool`（`git status --porcelain`，**含未跟踪文件**）
- [x] 2.4 把三类前置检查串成 `_preflight_isolation(...)`，**任一失败即非 0 退出**，且保证此时尚未创建 change 目录
- [x] 2.5 RED：TC-ISO-006（非 git 仓 ⇒ 非 0 退出 **且 `.fstdd/changes/<dir>` 不存在**）
- [x] 2.6 RED：TC-ISO-007（脏工作区 + branch ⇒ 非 0 退出、提示 worktree、**分支未变**）
- [x] 2.7 RED：TC-ISO-008（分支已存在 / 目标路径已存在 ⇒ 非 0 退出、输出清理命令、**不删既有路径**）
- [x] 2.8 GREEN ⇒ **38 passed in 106.80s**（22 新 + 16 既有）

**RED 证据形态（本片首次出现行为级 RED）**：实现落地前 `10 failed, 12 passed`，
其中 TC-ISO-006 为**行为级**失败 —— 断言「未说明真实原因」时抓到的是 Slice 1 的分期守卫文案
`隔离形态 'worktree' 尚未实现（本 change 仍在 BUILD 中）`，证明用例确实打在真实执行路径上。

**片内实测发现（重要环境根因，已回写用户级记忆）**：
本机 `C:\Users\Administrator` **本身就是一个 git 仓**，而 pytest 的系统临时目录位于其内
⇒ `temp_project` 被判为「在祖先仓内」，导致 4 例误报（**含 1 例假绿**：前置检查未生效却判通过）。
实测三组对照：

| `GIT_CEILING_DIRECTORIES` | `git rev-parse --show-toplevel` 结果 |
|---|---|
| 不设 | `rc=0` → `C:/Users/Administrator` ❌ |
| 设为 `<tmp_path>.parent` | `rc=128 fatal: not a git repository` ✅ |
| 设为**搜索起点自身** | `rc=0` **无效** ❌ |

⇒ 对策：新增 `_no_git_ancestor(monkeypatch, project)`，ceiling 必须设在**父级或更高**；
`_init_git_repo` 改为 `add -A` 后再 commit，产出**干净起点**的仓（否则 seed 前的工作区即脏）。
另：`@pytest.mark.skipif(not _GIT_OK, ...)` 在**模块加载时**求值 ⇒ git 工具函数必须上移到模块前部，
否则 NameError。

**失败模式检查（已核）**：非 git 仓走**显式拒绝**而非静默降级 `none`；
失败路径**不含任何删除动作**，清理命令仅打印不执行。

## 3. worktree 创建 + 脚手架落点切换（P0）

- [ ] 3.1 新增 `_resolve_worktree_root(project_root, cfg) -> Path`（默认 `<project_parent>/<project_name>.worktrees`，可被 `isolation.worktree_root` 覆盖）
- [ ] 3.2 新增 `_branch_name(cfg, dir_name) -> str`（`<branch_prefix><dir_name>`，**显式**构造，不走 git 隐式派生）
- [ ] 3.3 新增 `_create_worktree(project_root, path, branch) -> bool`：`git worktree add -b <branch> <path> HEAD`
- [ ] 3.4 把 `cmd_new` 的脚手架目标根改为变量 `target_root`（worktree 模式 = worktree 路径；否则 = `project_root`）
- [ ] 3.5 `cmd_canon_init` 改读 `getattr(args, "project_root", None) or Path.cwd()`；`new.py` 调用时传入 `target_root`
- [ ] 3.6 RED：TC-ISO-001（骨架落在 worktree 内、主仓 `.fstdd/changes/` 不含该 dir）
- [ ] 3.7 RED：TC-ISO-004（分支名精确等于规则值，无 `-explore`/`-research` 后缀）
- [ ] 3.8 RED：TC-ISO-009（worktree 在项目根之外、主仓 `git status --porcelain` 为空）
- [ ] 3.9 RED：TC-ISO-010（`isolation.worktree_root` 生效）
- [ ] 3.10 GREEN + 跑 `test_canon.py` 确认 `canon init` 向后兼容

**失败模式检查**：顺序必须「先 worktree 后脚手架」；`canon init` 不传 `project_root` 时行为必须与改动前逐字一致。

## 4. branch 形态（P1）

- [ ] 4.1 新增 `_create_branch(project_root, branch)`：`git checkout -b <branch>`（**不**建 worktree）
- [ ] 4.2 RED：TC-ISO-005（`git branch --show-current` == 规则分支名；`git worktree list` 仍 1 条）

## 5. 门禁随 worktree 生效（P1，裁定 ISO-1）

- [ ] 5.1 新增 `_propagate_guard_hooks(project_root, worktree_path) -> bool`：复制 `.claude/settings.local.json` / `.codebuddy/settings.local.json`（**文件级整份拷贝，不解析结构**）
- [ ] 5.2 源文件均不存在时输出明确告警（不得静默通过），且不改变 exit code
- [ ] 5.3 RED：TC-ISO-019（worktree 内存在同名文件且内容一致）
- [ ] 5.4 RED：TC-ISO-020（无源文件 ⇒ stdout 含告警、exit 仍 0）

**失败模式检查**：这是「隔离不得变成绕过门禁的通道」的唯一保障，必须留证（见 Slice 8 的 agent_spec）。

## 6. 提示行 + init 配置写入（P1）

- [ ] 6.1 `cmd_new` 收尾输出一行隔离提示（当前形态 + 如需隔离的完整命令），**零交互**
- [ ] 6.2 新增 `_post_init_isolation(project_root)`：读 `project.yaml` → `setdefault` 补 `isolation` 块（`default`/`worktree_root`/`branch_prefix`）→ 写回；**不覆盖任何既有取值**
- [ ] 6.3 挂到 `cmd_init` 的 `_post_init_*` 序列之后
- [ ] 6.4 RED：TC-ISO-011（提示行随形态变化）
- [ ] 6.5 RED：TC-ISO-012（monkeypatch `input` 抛异常，全程不触发）
- [ ] 6.6 RED：TC-ISO-013（init 后 `project.yaml` 含 `isolation` 三键）
- [ ] 6.7 RED：TC-ISO-014（既有 `isolation.default: branch` 与用户键 `project.name` 均保留；连续 init 幂等）

**失败模式检查**：写回不得用 `yaml.dump` 整体重写丢掉用户注释/顺序——需评估「定向文本插入」与「safe_load+setdefault+dump」两种写法的取舍，并在片内记录选择理由。

## 7. 死代码移除 + CHANGELOG（P1）

- [ ] 7.1 删除 `new.py:120-121` 的 `getattr(args, "parallel", False)` 调用点
- [ ] 7.2 删除 `_setup_parallel_worktrees`（`new.py:128-159`）
- [ ] 7.3 CHANGELOG 记录移除原因与它当时的 V2.8「双 Agent Kickoff」语义
- [ ] 7.4 RED：TC-ISO-017（`parallel` / `_setup_parallel_worktrees` 在 `upstream/fstdd/` 零命中）
- [ ] 7.5 RED：TC-ISO-018（CHANGELOG 含条目）
- [ ] 7.6 刷新吞异常哨兵（删除函数会使其后行号前移，可能超 ±5 容差）

## 8. 质量验证与交付证据（P0）

- [ ] 8.1 TC-ISO-021：`test_new.py` / `test_new_coverage.py` / `test_init.py` 全绿（16 例）
- [ ] 8.2 TC-ISO-022：`tools/audit_silent_except.py --check` + `test_guard_silent_except.py` 通过
- [ ] 8.3 TC-ISO-023：`test_guard.py` 51 例全绿（确认未触碰判定链）
- [ ] 8.4 **agent_spec 端到端**：沙箱仓 + 双 worktree 互不干扰（真 CLI + 真 git，单独执行并留证）
- [ ] 8.5 `stdd validate 2026-09-25-new-isolate-flag` ⇒ 0 error
- [ ] 8.6 全量套件回归：`upstream/tests` 0 failed（基线 **802 passed / 0 failed / 2614.06s @ `4eec636`**）
- [ ] 8.7 写 `test-report.md`（含 per-slice 证据链 + 失败模式检查结论）
- [ ] 8.8 待 Gate 3 确认

---

<!--
优先级说明：
- P0：阻塞性任务，完成前无法进入下一阶段
- P1：重要任务，应在当前阶段完成
- P2：可延后到后续版本的任务
依赖标注：(依赖 #N.M) 表示此任务依赖第 N 组第 M 个任务完成后才能开始
-->

## 遗留与连带项（不在本 change 范围，另行立项）

- CLI 审计链 5 项缺陷（`amend-audit` 不持久 / `traceability` 恒 0 / `approve`→`advance` 首次误报 / `canon generate --type` 死选项 / `gate.py` 无效补救提示）
- W5 与本次改动均**未 push**（待授权）
