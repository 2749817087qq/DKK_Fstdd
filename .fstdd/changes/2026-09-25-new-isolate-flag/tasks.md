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

## 3. worktree 创建 + 脚手架落点切换（P0）✅ 已完成 — commit `30756ea`

- [x] 3.1 新增 `_resolve_worktree_root(project_root, cfg) -> Path`（默认 `<project_parent>/<project_name>.worktrees`，可被 `isolation.worktree_root` 覆盖）— Slice 2 已落地
- [x] 3.2 新增 `_branch_name(cfg, dir_name) -> str`（`<branch_prefix><dir_name>`，**显式**构造，不走 git 隐式派生）— Slice 2 已落地
- [x] 3.3 新增 `_create_worktree(project_root, path, branch) -> bool`：`git worktree add -b <branch> <path> HEAD`
- [x] 3.4 把 `cmd_new` 的脚手架目标根改为变量 `target_root`（worktree 模式 = worktree 路径；否则 = `project_root`）
- [x] 3.5 `cmd_canon_init` 改读 `getattr(args, "project_root", None) or Path.cwd()`；`new.py` 调用时传入 `target_root`
- [x] 3.6 RED：TC-ISO-001（骨架落在 worktree 内、主仓 `.fstdd/changes/` 不含该 dir）
- [x] 3.7 RED：TC-ISO-004（分支名精确等于规则值，无 `-explore`/`-research` 后缀）
- [x] 3.8 RED：TC-ISO-009（worktree 在项目根之外、主仓 `git status --porcelain` 为空）
- [x] 3.9 RED：TC-ISO-010（`isolation.worktree_root` 生效）
- [x] 3.10 GREEN + 跑 `test_canon.py` 确认 `canon init` 向后兼容
- [x] 3.11 GREEN ⇒ **51 passed / 0 failed / 76.64s**（isolate 27 + 既有 new/canon/init 24）

**片内裁定 ISO-4（总工裁定）：模板源始终取主仓，不取 `target_root`。**
理由：模板是**项目级**资源，worktree 只是 change 的落点；且 worktree 是 HEAD 的签出，
主仓里**未提交**的模板不会随行 —— 若源改取 `target_root`，这类模板会被
`if tmpl.exists()` **静默跳过**，产出缺 `design.md` / `test-plan.md` 的半成品骨架。
落地方式即「`templates_dir` 一行不动」，零漂移；并由 TC-ISO-001b 锚定（断言复制到的
`design.md` 内容 = 主仓未提交版本，可区分两种实现）。

**实测（决定实现方式的三条事实）**：
| 探针 | 结论 |
|---|---|
| `git worktree add -b <b> <多级/父目录/不存在> HEAD` | **自动创建多级父目录**（rc=0），无需 `mkdir -p` |
| worktree 内 `.fstdd/templates/` | **随行**（因该目录已被 git 跟踪，18 个文件） |
| 建完 worktree 后主仓 `git status --porcelain` | **空**（worktree 在仓外，不污染主仓） |

**端到端验证（真 CLI + 真 git，独立于 pytest）**：`tmp/e2e_worktree_probe.sh`
1. `stdd new e2e-a --isolate worktree` ⇒ rc=0；worktree 建出、分支 `fstdd/2026-09-26-e2e-a`、
   `.fstdd.yaml` / `specs/` / `canonical/` / `design.md` / `test-plan.md` 全部落在 worktree 内；
   主仓 `.fstdd/changes/` **不含**该 dir、主仓 status 全程为空。
2. 双 worktree（e2e-a / e2e-b）互不干扰：B 内看不到 A 的 change，主仓仍为空。
3. 同名重复 ⇒ 由**分支名冲突**兜住（rc=1，输出 `git branch -D` 建议）。
   注意此处**不是**「change 目录已存在」拦下的 —— 隔离后主仓看不到该目录，
   重复创建的防线自然落在分支名上，符合预期语义。
4. 非 git 仓 ⇒ 走前置检查出声拒绝（`需要当前目录位于 git 工作树内`），rc=1，无残留。

**⚠️ 探针脚本自身的坑（已修，与产品无关）**：Git Bash 的 `/tmp` 是 MSYS 虚拟路径，
Windows 原生 git **不认** ⇒ `GIT_CEILING_DIRECTORIES=/tmp` **静默失效**，沙箱被误判为
「在 `C:\Users\Administrator` 仓内」（该目录本身是 git 仓），首跑因此出现 1 处假绿
（`git -C /tmp/...` 报 `fatal: cannot change to`，`wc -l` 得 0 被当成通过）。
修法：ceiling 用 `cygpath -w -l` 转 Windows 路径；`git -C` 改用 `( cd <dir> && git ... )`。

**失败模式检查（已核）**：
- 顺序「先 worktree 后脚手架」已由 `target_root` 在 `(change_dir/"specs").mkdir()` **之前**
  赋值保证；worktree 创建失败即 `sys.exit(1)`，不留任何骨架。
- `canon init` 不传 `project_root` 时回落 `Path.cwd()`，`test_canon.py` 全绿 ⇒ 向后兼容成立。
- 分期守卫收窄为仅 `branch`（Slice 4 实现后删除），`worktree` 不再被拦。

## 4. branch 形态（P1）✅ 已完成 — commit `30e9f70`

- [x] 4.1 新增 `_create_branch(project_root, branch)`：`git checkout -b <branch>`（**不**建 worktree）
- [x] 4.2 RED：TC-ISO-005（`git branch --show-current` == 规则分支名；`git worktree list` 仍 1 条）
- [x] 4.3 GREEN ⇒ **51 passed / 0 failed / 56.69s**（isolate 26 + 既有 new/canon/init 25）
- [x] 4.4 **删除 BUILD 分期守卫**及其用例（worktree / branch 均已实现）

**关键语义差异（worktree vs branch）**：
| | worktree | branch |
|---|---|---|
| `target_root` | = worktree 路径 | = `project_root`（**不变**） |
| 骨架落点 | worktree 内 | 主仓 |
| 隔离来源 | 目录 | 分支 |
| 同名重复被谁拦 | **分支名冲突**（主仓看不到 change 目录） | **change 目录已存在**（主仓可见） |

**端到端验证（真 CLI + 真 git）**：`tmp/e2e_branch_probe.sh`
1. 脏树 + branch ⇒ 出声拒绝（引用 ISO-3 裁定原文），rc=1，**分支未变**、无残留目录。
2. 干净后 ⇒ rc=0，分支切到 `fstdd/2026-09-26-e2e-br`，**worktree 条数仍为 1**，
   骨架与 canonical 均落在主仓，主仓未出现 `proj.worktrees/` 目录。
3. 同名重复 ⇒ 被「Change 目录已存在」拦下（rc=1），分支保持不动。

**分期守卫移除说明**：Slice 1–3 期间 `test_unimplemented_mode_fails_loud` 断言
`worktree|branch` 在实现前必须出声拒绝（防「参数已注册、实则永不生效」）。
两种形态现已全部落地，守卫及其用例一并删除，并在测试文件内留注释：
**后续若新增隔离形态（如 `container`），必须重新加回等价守卫。**

**失败模式检查（已核）**：branch 失败路径同样 `sys.exit(1)` 且不留骨架；
`target_root` 在 branch 分支下**不被改写**，落点语义与 none 一致。

## 5. 门禁随 worktree 生效（P1，裁定 ISO-1）✅ 已完成 — commit `e89c0ab`

- [x] 5.1 新增 `_propagate_guard_hooks(project_root, worktree_path) -> bool`：复制 `.claude/settings.local.json` / `.codebuddy/settings.local.json`（**文件级整份拷贝，不解析结构**）
- [x] 5.2 源文件均不存在时输出明确告警（不得静默通过），且不改变 exit code
- [x] 5.3 RED：TC-ISO-019（worktree 内存在同名文件且内容一致）
- [x] 5.4 RED：TC-ISO-020（无源文件 ⇒ stdout 含告警、exit 仍 0）
- [x] 5.5 GREEN ⇒ **54 passed / 0 failed / 41.40s**（isolate 29 + 既有 25）

**缺口根因（本片实测，即 ISO-1 的实证）**：
| 探针 | 结果 |
|---|---|
| `ls .claude/`（stdd-repo） | `settings.local.json` 存在，1088 B |
| `ls .codebuddy/`（stdd-repo） | **不存在** |
| `git ls-files .claude .codebuddy` | **空**（两者均未被跟踪） |
| 未跟踪文件能否随 `git worktree add` 签出 | **不能** |

⇒ 新 worktree 里**没有任何门禁**。若不做传播，`--isolate worktree` 就是一个
**绕过 Guard 的官方通道** —— 比不提供隔离更危险。

**设计取舍（本片记录）**：采用**文件级整份拷贝**，不解析 JSON 结构。
理由：这两个文件是宿主（Claude Code / CodeBuddy）的私有格式，解析会让 FSTDD 与
宿主版本耦合；整份拷贝语义最直白，宿主日后增删字段也自动跟随。
单文件复制失败**不中断**（另一宿主可能仍可成功），逐个打印告警。

**端到端验证（真 CLI + 真 git + stdd-repo 的*真实* hook 配置）**：`tmp/e2e_guard_hook_probe.sh`
1. 主仓放真实 `settings.local.json`（1088 B，未跟踪，`git status` 显示 `?? .claude/`）
   ⇒ `new --isolate worktree` 后 worktree 内该文件存在、**逐字节一致**、含 guard 命令。
2. 无 hook 项目 ⇒ 输出 `⚠️ 未发现门禁 hook 注册文件…该 worktree 内 Guard 门禁**不会生效**`，
   **rc 仍为 0**，change 正常建成（降级而非失败）。

**失败模式检查（已核）**：传播动作紧跟 worktree 创建之后，无中间失败窗口；
告警文案明确写出「门禁不会生效」，非静默通过；exit code 不受影响。

## 6. 提示行 + init 配置写入（P1）✅ 已完成 — commit `40075e9`

- [x] 6.1 `cmd_new` 收尾输出一行隔离提示（当前形态 + 如需隔离的完整命令），**零交互**
      —— 已于 Slice 1 前移落地（`_print_isolation_hint`），本片补测试锚定
- [x] 6.2 新增 `_post_init_isolation(project_root)`：读 `project.yaml` → 补 `isolation` 块（`default`/`worktree_root`/`branch_prefix`）→ 写回；**不覆盖任何既有取值**
- [x] 6.3 挂到 `cmd_init` 的 `_post_init_*` 序列（`_post_init_constitution` 之后、`_post_init_self_check` 之前，让自检能看到完整配置）
- [x] 6.4 RED：TC-ISO-011（提示行随形态变化）
- [x] 6.5 RED：TC-ISO-012（monkeypatch `input` 抛异常，全程不触发）
- [x] 6.6 RED：TC-ISO-013（init 后 `project.yaml` 含 `isolation` 三键）
- [x] 6.7 RED：TC-ISO-014（既有 `isolation.default: branch` 与用户键 `project.name` 均保留；连续 init 幂等）
- [x] 6.8 GREEN ⇒ **61 passed / 0 failed / 41.23s**（isolate 36 + 既有 25）

**写回策略取舍（本片核心决策，已记录）**：**采用 `safe_load + setdefault + yaml.dump`，
放弃「定向文本插入」**。判据是实测事实：

| 探针 | 结果 |
|---|---|
| `project.yaml` 是否被 git 跟踪 | **是** |
| 是否有注释 / 非字母序键 | **无**（纯 `yaml.dump` 产物，键序 `isolation→paths→project→stdd_version`） |
| 其他 config（guard/gates/lite） | 有注释 —— 但**本函数只碰 project.yaml** |

⇒ 该文件不存在「丢失用户注释/顺序」的语义，定向插入需自行处理缩进、插入位置与幂等，
复杂度高而收益为零。三道保护替代之：
1. 顶层非映射 ⇒ 出声跳过；
2. `isolation` 存在但非映射（`isolation: banana`）⇒ 出声跳过、**不覆盖**（TC-ISO-014b 锚定）；
3. 三键齐备 ⇒ **完全不写文件**（幂等，且不动 mtime）。

**单源约束**：默认值不在 init.py 重复定义，而是函数内
`from .new import _DEFAULT_BRANCH_PREFIX, _DEFAULT_ISOLATE_MODE` —— 避免两处常量各自漂移。
`worktree_root` 写**空串**表示「用内置默认」（项目根父目录下的 `<项目目录名>.worktrees`），
写死路径会在项目移动/改名后失效。

**端到端验证（真 CLI `stdd init`）**：`tmp/e2e_init_probe.sh`
1. 首次 init ⇒ `[STDD] 隔离配置: 已补 3 个键`，`project.yaml` 出现
   `isolation: {branch_prefix: fstdd/, default: none, worktree_root: ''}`，三键齐备。
2. 再跑一次 init ⇒ `已就绪（未改动 project.yaml）`，文件**逐字节未变**（幂等）。
3. 预置 `isolation.default: branch` + `project.name: keepme` 后再 init
   ⇒ 两者**均保留**，缺失的 `branch_prefix` 被补齐。

**失败模式检查（已核）**：不覆盖既有取值（TC-ISO-014/014b 双向锚定）；
幂等（逐字节比对）；`stdd new` 零交互（TC-ISO-012 用 input 抛异常反证）。

## 7. 死代码移除 + CHANGELOG（P1）✅ 已完成 — commit `85383bd`

- [x] 7.1 删除 `new.py` 的 `getattr(args, "parallel", False)` 调用点
- [x] 7.2 删除 `_setup_parallel_worktrees`（34 行实现）
- [x] 7.3 CHANGELOG 记录移除原因与它当时的 V2.8「Two-Instance Kickoff」语义
- [x] 7.4 RED：TC-ISO-017（`parallel` / `_setup_parallel_worktrees` 在 `upstream/fstdd/` 零命中）
- [x] 7.5 RED：TC-ISO-018（CHANGELOG 含条目）
- [x] 7.6 刷新吞异常哨兵
- [x] 7.7 GREEN ⇒ **66 passed / 0 failed / 51.19s**；哨兵 **通过（0 条提示）**

**⚠️ 连带删除（计划外，本片发现）**：`upstream/tests/commands/test_new_coverage.py`
整个文件（2 例，`TC-PAR-001`）测的**正是被删的死代码** —— 它直接构造
`Namespace(name=..., dry_run=False, parallel=True)` 调用 `cmd_new`，断言输出含
`Two-Instance Kickoff` / `Explorer` / `Researcher`。被测功能已不存在 ⇒ 删除，
否则会留下「测试绿、功能无」的假象。
其中 dry-run 那例的覆盖已由 `test_new.py::test_new_dry_run` 承担（已核实）。
⇒ 已同步 `test-plan.md`：测试文件清单去掉该行、TC-ISO-021 既有回归例数 16 → **14**。

**哨兵状态（本片实测，与预判不同）**：
| 探针 | 结果 |
|---|---|
| `new.py` 的吞异常点 | **零命中**（`_load_isolation_config` 用的是具名异常元组，不匹配 `_SWALLOW`） |
| ⇒ 删除 new.py 死代码是否影响哨兵 | **否**（删除段在文件末尾，前面行号不动） |
| 但 `audit_silent_except.py --check` 当时**已红** | 2 条提示：`init.py:385` 未覆盖 + `init.py:322` 失效 |
| 根因 | **Slice 6** 在 `_post_init_self_check` 前插入 63 行 ⇒ 其内吞异常点 322 → 385，超 ±5 容差 |

⇒ 刷新审计表 `.fstdd/changes/2026-09-18-detection-silence-fixes/audit/except-points.yaml`
的 `EA-015` 行号（322 → 385，附漂移原因注释；条目语义与 justification 未变）。
刷新后哨兵 0 条提示，`test_except_audit.py` 5 passed。
**教训**：行号锚定型哨兵的容差必须在**任何插入/删除代码的切片结束时**主动复核，
不能等到「预期会影响的切片」才查 —— 本次触发者是 Slice 6 的插入，而非 Slice 7 的删除。

**CHANGELOG 落点**：写入 `upstream/CHANGELOG.md`（**框架级**），而非根 `CHANGELOG.md`
（项目级、`[未发布] — 迭代 02` 段）。`--isolate` 是 STDD 框架能力，归 upstream。
新增 `## V3.0.7 (2026-09-26)` 段，含「新增 / 安全 / 移除 / 配置」四类，
其中「移除」段**完整复述 V2.8 Two-Instance Kickoff 的原语义**（为何存在、为何现在不需要），
以防后人把同一个死开关重新加回来。

**失败模式检查（已核）**：`upstream/fstdd/` 下 `parallel` 零命中（TC-ISO-017 锚定）；
CHANGELOG 条目可被 TC-ISO-018 检索（`V3.0.7` + `Two-Instance Kickoff` 双重锚定）。

## 8. 质量验证与交付证据（P0）✅ 已完成 — commit `641a996`

- [x] 8.1 TC-ISO-021：`test_new.py`(11) + `test_init.py`(3) 全绿（**14 例**）
      —— `test_new_coverage.py`(2) 已随死代码删除，见 Slice 7
- [x] 8.2 TC-ISO-022：`tools/audit_silent_except.py --check` ⇒ **通过（0 条提示）**；
      `test_except_audit.py` ⇒ **5 passed**
- [x] 8.3 TC-ISO-023：`test_guard.py` ⇒ **51 passed / 5.13s**（Guard 判定链未受影响）
- [x] 8.4 **agent_spec 端到端**：沙箱仓 + 双 worktree ⇒ **23/23 通过**（真 CLI + 真 git + 真 Guard）
- [x] 8.5 `stdd validate 2026-09-25-new-isolate-flag` ⇒ **0 error**（1 warning 为既有约定代价，W5 同款）；
      `canon verify` ⇒ **2/2 通过**
- [x] 8.6 全量套件回归 ⇒ **838 passed / 0 failed / 1069.38s (0:17:49)**
      （基线 802 passed / 0 failed / 2614.06s @ `4eec636`；
      差值 **+36** = +38 新增 isolate 用例 − 2 删除 `test_new_coverage.py`，**与预期完全一致**）
- [x] 8.7 `test-report.md` 已写（含 per-slice 证据链 + 失败模式检查 11 项 + 端到端证据）
- [ ] 8.8 待 Gate 3 确认

**关键证据（详见 `test-report.md`）**：
| 项 | 结果 |
|---|---|
| 相关套件（isolate/new/canon/init/except_audit） | **66 passed / 0 failed / 51.19s** |
| 全量套件 `upstream/tests` | **838 passed / 0 failed / 1069.38s** |
| `test_guard.py`（判定链） | **51 passed** |
| agent_spec 端到端 | **23/23**（alpha 只读相位冻结 scope 内、scope 外 warn-only；beta build 相位同路径 exit 0） |
| `stdd validate` | **0 error** |
| 吞异常哨兵 | **0 条提示** |
| `canon verify` | **2/2** |

**agent_spec 的核心命题已证成**：两处 ACTIVE_CHANGE 各自只冻结自己 scope 内的路径，
**跨 worktree 零干扰** —— 这是主工作区单实例模型下做不到的，也是单测无法证明的部分。

**耗时说明**：全量耗时低于基线（1069s vs 2614s）系**机器负载差异**（基线那轮有外部
python 进程 PID 24520 持续占用），与用例数无关；用例数差值是确定性的，已逐项对账。

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
