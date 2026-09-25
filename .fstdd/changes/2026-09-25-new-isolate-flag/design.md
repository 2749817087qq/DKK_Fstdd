# 让「一 change 一隔离环境」可选且可见 - 技术设计

## Context

**现状（改动前，观测于 base_git_sha `4eec636`）**：

| 事实 | 证据位置 |
|---|---|
| `stdd new` 只有 `name` 与 `--task-type` 两个参数，**argparse 里根本没有 `--parallel`** | `upstream/fstdd/cli/__init__.py:126-130` |
| 调用点靠 `getattr(args, "parallel", False)` 取值 ⇒ 恒 False ⇒ 下游函数**永不可达** | `upstream/fstdd/cli/commands/new.py:120-121` |
| 该死函数把 worktree 建在**项目根之内**（`.claude/worktrees/`），且 `git worktree add <path>` 不带 `-b` ⇒ 由 git 按路径末段隐式建同名分支 | `new.py:128-159` |
| 它一次建**两条** worktree（`-explore` / `-research`），语义是 V2.8 的「双 Agent Kickoff」，与「一 change 一隔离」不是同一件事 | `new.py:137-141` |
| `stdd init` / `stdd new` 全流程无 `input()` ⇒ 用户无从得知可以隔离 | `new.py` / `init.py` 无交互调用点 |
| `git worktree list` 只有主工作区一条 ⇒ 隔离能力从未被使用过 | 实测 |

**技术栈与约束**：
- CLI 为 argparse 单入口，`--dry-run` 由父解析器统一提供（`_init_parent_parser()`），子命令靠 `getattr` 读取。
- `.fstdd/config.d/project.yaml` 是**既有**的项目级配置，`guard.py` 已在读它（`:796` 读 `enforce_stdd`，`:389` 读 `guard.exempt_paths`）⇒ 新增 `isolation` 块不会与既有读取冲突（均为 `.get()`）。
- `stdd init` 复制配置文件的策略是「已存在则跳过，除非 `--force`」（`init.py:143`），且 `CONFIG_MERGE_FILES`（`init.py:82`）声明 `project.yaml` 在 upgrade 时**合并**而非覆盖 ⇒ 任何写入都必须是非破坏性的。
- `canon.py:113` 用 `Path.cwd()` 作 `project_root` ⇒ 想在工作区之外建骨架，必须解决这个 cwd 依赖。
- Guard 的路径判定链（W5 落地后）：硬阻断 → `exclude_dirs` → **项目外放行**（`guard.py:822-827`）→ agent runtime 豁免 → YAML-first 产物 → 可编辑相位 → scope 判定。

**范围外（本 change 不做）**：`--isolate auto`、隔离环境的自动清理/回收、多 change 并发的调度、`archive` 对 worktree 的联动回收。

---

## 裁定记录（总工裁定，2026-09-26）

> **授权依据**：D哥 2026-09-26 01:48 明确「你现在就是 fstdd skill 的总工，我全权授权你处理这些事情，
> 有技术分歧你把决定与理由发出来就行了，我看了觉得有问题会给你说」。
> 本表三条即原设计中的三个待议点，**已裁定，不再阻塞 Gate 2**。

| 裁定 | 结论 | 理由 |
|------|------|------|
| **ISO-1**（原决策 10） | **采纳**：worktree 内复制 hook 注册，保持 Guard 门禁有效 | 它是 SC-001 的**必要条件**而非新增功能——不采纳则已批准的成功判据 #1 在 worktree 侧不可验证，且隔离会**静默变成绕过门禁的通道**。安全性缺口不因「超出 Gate 1 五条变更」而降级处理 |
| **ISO-2**（原决策 8 备选 A） | **维持原方案**：写入 `.fstdd/config.d/project.yaml`，以 `setdefault` 只补缺失键 | 备选 A（独立 `isolation.yaml`）的收益是「不碰用户文件」，而该风险已被**非破坏性合并**写法覆盖（只补缺失键、不覆盖既有值、幂等）；改用 A 则要修改 Gate 1 已确认的成功判据，**扩大变更面却无实证收益** |
| **ISO-3**（原决策 5） | **维持拒绝**：脏工作区下 `--isolate branch` 拒绝执行 | 静默带着无关改动切分支 = 制造「看起来隔离了」的假象。不加 `--force`：逃生路径已存在（commit/stash 或改用 `worktree`），且 `--force` 与 `init --force`（覆盖文件）同名不同义，会造成误解 |

**ISO-1 的记录要求**：由于该条为 SPEC 阶段新增，其验收证据必须在 BUILD 阶段显式留证
（TC-ISO-019/020 + agent_spec），不得只凭「已写入设计文档」结案。

---

## Decisions

### 1. 开关形态：`--isolate {none|worktree|branch}`，默认 `none`

**方案**：在 `p_new` 上注册 `--isolate`，`choices=["none","worktree","branch"]`，`default=None`（`None` 时回落到配置值，配置缺失回落 `none`）。

**为什么**：
- 三态是**语义上真实存在的三种状态**，而不是为了扩展性预留的枚举：`none` = 现状（同一工作区）、`worktree` = 独立工作树（独立文件系统视图 + 独立 ACTIVE_CHANGE）、`branch` = 同一工作树换分支（只隔离提交历史，不隔离文件系统）。
- `default=None` 而非 `default="none"`，是为了让「未显式指定」与「显式指定 none」可区分——前者要读配置，后者必须无视配置。若都用 `"none"`，`isolation.default: worktree` 这个配置项就永远无法生效。

**备选方案及排除原因**：
- 备选 A：布尔 `--isolate`（有/无）。排除：无法表达 `worktree` 与 `branch` 的区别，而这两者对「工作区脏不脏」的要求完全不同（见决策 5），布尔开关必然导致其中一种形态被迫接受另一种的前提条件。
- 备选 B：`--isolate auto`（按仓库状态自动选）。排除：违背本 change 的立意（**可见**且**显式**）。自动选择意味着用户事后必须反查「我这次到底隔离了没有」，正是要消除的失败模式。
- 备选 C：只加 `--worktree` / `--branch` 两个独立布尔。排除：两个布尔可同时为真，需要额外校验互斥；且 `--help` 里看不出「不指定时是什么」。

### 2. `worktree` 模式下，change 骨架**落在 worktree 内**，不在主工作区

**方案**：`worktree` 模式把「创建 worktree」提到「脚手架落盘」**之前**；脚手架的目标根目录整体改为 worktree 路径。主工作区的 `.fstdd/ACTIVE_CHANGE` 与 `.fstdd/changes/` **不被触碰**。

**为什么**：
- 隔离的定义就是「这个 change 住在自己的环境里」。若骨架留在主工作区、只在 worktree 里放一份副本，就产生了**两份 change 状态**——而两份状态必然漂移（Gate 确认写哪一份？`ACTIVE_CHANGE` 指哪一份？）。这正是本 change 要消灭的那类问题。
- 顺序「先 worktree、后骨架」还带来一个免费的**原子性收益**：worktree 创建失败时，`.fstdd/changes/` 里不会留下任何半成品（见决策 6）。

**备选方案及排除原因**：
- 备选 A：主工作区建骨架 → 复制进 worktree。排除：双份状态，必然漂移；且复制时机一旦被中断就是半完成态。
- 备选 B：主工作区建骨架，worktree 仅作临时草稿区。排除：这不叫隔离，叫多开一个目录；`ACTIVE_CHANGE` 仍指向主工作区，阶段劫持照旧。

### 3. 分支名显式构造为 `<branch_prefix><change_dir_name>`，用 `-b` 创建

**方案**：`git worktree add -b <branch> <path> HEAD`（worktree 模式）／`git checkout -b <branch>`（branch 模式）；`branch_prefix` 默认 `fstdd/`。

**为什么**：
- 死代码的 `git worktree add <path>`（无 `-b`）会让 git 依据路径末段**隐式**建同名分支（`<change>-explore` / `<change>-research`）。分支名由文件系统路径推导，既不可预测也无法在配置里表达，且一旦 worktree 目录改名，分支名与目录名就脱钩。
- 显式 `-b` 把「分支名从哪来」变成一条可读的规则，也让 SC-004 可断言。

**备选方案及排除原因**：
- 备选 A：沿用隐式同名分支。排除：不可预测（如上）。
- 备选 B：加 `--isolate-branch <name>` 允许覆盖。排除：覆盖需求无实证（YAGNI），而每多一个参数就多一组必须覆盖的用例；命名规则已确定，用户需要别的名字时自行 `git branch -m` 即可。**若 Gate 2 认为需要覆盖能力，这是唯一需要改动的决策点。**

### 4. worktree 默认建在项目根**之外**

**方案**：默认 `<project_parent>/<project_name>.worktrees/<change_dir_name>`；`isolation.worktree_root` 可覆盖。

**为什么**：
- 建在项目根之内，`git status` 立刻变脏。这不是洁癖问题：仓库里存在断言「工作区除 `.fstdd/changes/` 外干净」的测试（`test_a6_d_repo_worktree_clean`，本次 W5 提交前就曾因此判红），一个隔离功能把回归测试搞红是自相矛盾。
- 建在项目根之外，Guard 的**项目外放行**分支（`guard.py:822-827`）会自然生效，不需要把 worktree 目录塞进任何豁免名单。
- 为什么不走 `guard.exempt_paths`（`guard.py:389-400`）：它是**按目录名做祖先匹配**的钝器——为豁免 `<root>/worktrees` 而加进去，会同时豁免文件系统上任何位置同名目录，豁免面不可控。用一个可控的路径，比放宽一个不可控的名单好。

**备选方案及排除原因**：
- 备选 A：`<project_root>/.fstdd/worktrees/`。排除：`.fstdd/` 虽被大量工具读写，但它**在 git 管辖内**，会污染 `git status`；且会让「`.fstdd/` 是流程元数据」的语义变模糊。
- 备选 B：沿用死代码的 `.claude/worktrees/`。排除：同上，且 `.claude/` 是 agent 平台目录，把 change 工作树塞进去会让「平台配置」与「流程产物」混居。
- 备选 C：`guard.exempt_paths` 豁免一个仓内目录。排除：钝器，见上。

### 5. `branch` 模式在**脏工作区**下拒绝执行

**方案**：`--isolate branch` 前检查 `git status --porcelain`（含未跟踪文件），非空则以非 0 退出，提示改用 `--isolate worktree`。`worktree` 模式**不做**此检查。

**为什么**：
- `git checkout -b` 会把未提交改动**带到新分支上**。这意味着新 change 的提交里会混进与本 change 无关的改动——用户以为自己隔离了，实际拿到的是「换了个分支名的同一堆改动」。这是典型的静默失效。
- 两种模式对脏树的容忍度本就不同：worktree 不动主工作区，脏树无害；branch 动主工作区，脏树有害。这个差异正是决策 1 拒绝布尔开关的原因。
- 拒绝而非告警放行，是延续本 change 的立意：宁可让用户多打一条命令，也不制造「看起来隔离了」的假象。

**备选方案及排除原因**：
- 备选 A：告警后继续切分支。排除：制造上述假象。
- 备选 B：自动 `git stash`。排除：stash 是**用户的**状态，工具替用户 stash 却不负责恢复，是在制造更难排查的问题。
- 备选 C：加 `--force` 逃生口。排除：`init` 已占用 `--force` 语义（覆盖文件），同名不同义会造成误解；且逃生路径已有（用户自己 `git stash` 或改用 worktree）。

### 6. 失败一律发生在创建 change 目录**之前**；失败后**不自动删除**

**方案**：`worktree` 模式预检顺序为：git 工作树 → 分支名是否已存在（`git rev-parse --verify`）→ 目标路径是否已存在 → `git worktree add`。任一失败：非 0 退出 + 输出可直接执行的清理命令，**不**自行 `rm`/`git worktree remove`。

**为什么**：
- 先建目录后建 worktree，失败时必然留下半成品 change；顺序反过来，最坏情况只是一个空 worktree 目录。
- 不自动删除的理由：`git worktree remove --force` 是**破坏性**操作。虽然那个路径是我们刚创建的，但「工具在失败路径上自动执行破坏性命令」这件事本身需要极强的理由；而此刻用户就在终端前面，打印一条清理命令的代价是零，误删的代价不是。
- 预检冲突（分支已存在／路径已存在）先于 `git worktree add`，是为了让绝大多数失败在**没有副作用**的情况下被拦下。

**备选方案及排除原因**：
- 备选 A：失败时 `git worktree remove --force` 回滚。排除：破坏性，见上。
- 备选 B：不预检，靠 `git worktree add` 报错。排除：git 的错误信息对「分支已存在」与「路径已存在」给不出下一步该做什么；且某些失败会留下已注册的 worktree 元数据。

### 7. `canon init` 接受可选 `project_root`，以参数传递取代 `os.chdir`

**方案**：`cmd_canon_init` 改读 `getattr(args, "project_root", None) or Path.cwd()`；`new.py` 调用时把目标根目录放进 `Namespace`。

**为什么**：
- 这是决策 2 的直接后果：骨架要落在 worktree 里，而 `canon.py:113` 把根目录硬绑在 cwd 上。
- 两条路：`os.chdir()` 包 `try/finally`，或把根目录做成参数。前者是**全局可变状态**——`cmd_new` 体内任何依赖 cwd 的代码（日志、相对路径、后续函数）都会被静默影响，且异常路径漏掉 `finally` 就会把进程留在错误目录；后者是显式数据流，可测、可读。
- 改动是**向后兼容**的：不传 `project_root` 时行为与现状完全一致。

**备选方案及排除原因**：
- 备选 A：`os.chdir` + `try/finally`。排除：全局可变状态，见上。
- 备选 B：不动 `canon.py`，改为在 worktree 里起子进程跑 `fstdd canon init`。排除：为一次函数调用付一个进程的代价，且子进程的错误传播、退出码映射、输出捕获都要重新处理。

### 8. 隔离配置：`init` 用「只补缺失键」的单机制写入，不改源模板

**方案**：新增 `_post_init_isolation(project_root)`，挂在既有 `_post_init_*` 序列（`init.py:174-177`）之后。实现为「读 YAML → `setdefault` 补 `isolation` 块及其子键 → 写回」，**不覆盖任何已有取值**。**不**修改源模板 `upstream/.fstdd/config.d/project.yaml`。

**为什么**：
- 只用一个机制，新项目与既有项目都覆盖：新项目的 `project.yaml` 从模板复制而来（`init.py:143`），随后被 `setdefault` 补上；既有项目跳过复制，同样被补上。若同时在源模板里加一遍，就有了**两个真相来源**——模板与写入逻辑一旦不一致，只能靠对比两份文件才能发现。
- `setdefault` 而非赋值，是为了满足 `CONFIG_MERGE_FILES`（`init.py:82`）所隐含的契约：`project.yaml` 是用户可编辑的文件，工具不得抹掉用户的取值。重复 `init` 幂等（SC-014）。
- 配置结构：
  ```yaml
  isolation:
    default: none                  # none | worktree | branch
    worktree_root: null            # null => <project_parent>/<project_name>.worktrees
    branch_prefix: "fstdd/"
  ```

**备选方案及排除原因**：
- 备选 A：独立文件 `.fstdd/config.d/isolation.yaml`。排除：更干净（完全不碰用户文件），但 proposal（Gate 1 已确认）明确要求写入 `project.yaml`，且成功判据写的就是 `project.yaml` 含该字段。**已由裁定 ISO-2 维持原方案**（见上方「裁定记录」）。
- 备选 B：在源模板里写死 `isolation` 块。排除：两个真相来源，见上。

### 9. `--parallel` 死代码：**移除**，不并入 `--isolate`

**方案**：删除 `new.py:120-121` 的调用点与 `new.py:128-159` 的 `_setup_parallel_worktrees`；CHANGELOG 记录。

**为什么**：
- 它是**不可达**代码（argparse 从未注册 `--parallel`，实测 `error: unrecognized arguments: --parallel`），保留它只会让下一个人再次以为「这里有隔离功能」。
- 它的语义（一次建两条 `-explore`/`-research` 工作树的双 Agent Kickoff）**不是**本 change 要交付的东西。把「建两条工作树」塞进 `--isolate worktree`（语义是「建一条」）是把一个未经验证的功能偷渡进一个已批准的变更里——这正是 FSTDD 流程要防的事。若将来要做双 Agent Kickoff，它应当是一个独立的 change，带着自己的 proposal 与判据。

**备选方案及排除原因**：
- 备选 A：把 `--parallel` 注册进 argparse，让它变成可用功能。排除：等于在本 change 里交付一个未经 Gate 1 评审的功能。
- 备选 B：保留函数但不注册。排除：死代码原样留下。

### 10. worktree 内 Guard 门禁必须保持有效（**SPEC 阶段新增**）

**方案**：`worktree` 模式在建出 worktree 后，把主工作区存在的 `.claude/settings.local.json` / `.codebuddy/settings.local.json` 复制进 worktree；若主工作区两者皆无，则输出明确告警。

**为什么**：
- `git worktree add` 只签出**已跟踪**的文件。hook 注册文件（`settings.local.json`）通常被 gitignore ⇒ 新 worktree 里**没有**任何 hook 注册 ⇒ Guard 在该 worktree 内**完全不生效**。
- 后果是致命的：proposal 的成功判据 #1 要求「两处同时有不同 change 处于只读相位，各自只冻结自己作用域」——门禁不激活，这句话在 worktree 侧根本无法成立，隔离就成了**绕过流程管控**的通道。一个让门禁消失的「隔离」比不隔离更糟。
- 复制是无害的：目标文件在 worktree 内本就是未跟踪的本地配置。

**备选方案及排除原因**：
- 备选 A：不处理，作为已知限制记录。排除：直接使已批准的成功判据 #1 不可验证，且引入静默的安全退化。
- 备选 B：让 Guard 从主工作区读取 worktree 的状态。排除：跨工作区读 change 状态，等于把「隔离」重新耦合回主工作区，与决策 2 冲突。

> ⚠️ 决策 10 是 **SPEC 阶段新增**，不在 Gate 1 已确认的 proposal 五条变更之内。它来自 SC-001 的必要条件。
> **已由裁定 ISO-1 采纳**（见上方「裁定记录」）；其验收证据须在 BUILD 阶段显式留证（TC-ISO-019/020 + agent_spec）。

---

## Architecture

### 创建流程（worktree 模式）

```
stdd new x --isolate worktree
  │
  ├─ 1. 解析隔离形态
  │     args.isolate (None?) ──yes──> 读 project.yaml isolation.default
  │                                    （缺失/不可解析/非法 → "none"，fail-safe）
  │     └─ 校验 change 名（既有正则，new.py:18）
  │
  ├─ 2. 【隔离前置】仅在 worktree|branch 时进入
  │     ├─ git rev-parse --is-inside-work-tree   ──失败──> exit≠0（不建任何目录）  [SC-006]
  │     ├─ worktree 模式：git rev-parse --verify <branch>  ──已存在──> exit≠0 + 清理命令 [SC-008]
  │     │                 目标路径已存在                    ──已存在──> exit≠0 + 清理命令
  │     │  branch 模式：  git status --porcelain 非空       ──脏────> exit≠0 + 建议 worktree [SC-007]
  │     │
  │     └─ worktree: git worktree add -b <branch> <path> HEAD
  │        branch:   git checkout -b <branch>
  │
  ├─ 3. 脚手架（目标根 = worktree 路径 或 项目根）
  │     ├─ 建 .fstdd/changes/<dir>/ + specs/
  │     ├─ 复制 .fstdd/templates/{design,test-plan}.md
  │     ├─ 写 .fstdd.yaml（4 相位状态）
  │     └─ cmd_canon_init(Namespace(..., project_root=<目标根>))   ← 决策 7
  │        └─ 终态校验：canonical/ 是否真的在盘上（既有逻辑，new.py:110-117）
  │
  ├─ 4. worktree 模式：复制 hook 注册（决策 10）  [SC-019/020]
  │
  └─ 5. 输出：既有收尾信息 + 一行隔离提示（零交互）  [SC-011/012]
```

### 判定顺序不变式

本 change **不修改** Guard 的判定链。仅需确认新增路径与既有链相容：

```
硬阻断 → exclude_dirs → 项目外放行(guard.py:822) → agent runtime 豁免
       → YAML-first 产物 → 可编辑相位 → scope 判定(W5)
```

- worktree 位于**项目根之外** ⇒ 在主工作区上下文里，对 worktree 内文件的写入命中「项目外放行」，不误伤（决策 4）。
- 在 worktree **自己**的上下文里，`project_root` 就是 worktree 根，其内的 change 目录与 scope 判定照常工作（SC-001 的「各自只冻结自己作用域」由此成立）。

### 配置读取（fail-safe 方向）

```
args.isolate 显式给出 ──> 直接采用（无视配置）
args.isolate 为 None  ──> 读 .fstdd/config.d/project.yaml → isolation.default
                          文件缺失 / YAML 报错 / 值不在 {none,worktree,branch}
                          ──> 一律回落 "none"，不报错、不中断   [SC-016]
```

**注意方向性**：配置读取失败回落到**最保守**的 `none`（保持现状），而不是回落到 `worktree`。理由：`none` 不会对用户的仓库做任何写入，失败时的副作用最小。

---

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 决策 10（复制 hook 注册）依赖 `settings.local.json` 的具体结构，平台若换注册位置则复制落空 | 复制按**文件级**做（整份拷贝，不解析结构），并对「源文件不存在」出声告警（SC-020）；平台注册位置变化时至少是「响的失败」而非静默失效 |
| 项目根之外建目录，在只读文件系统 / 无写权限的父目录下会失败 | 失败走统一的非 0 退出 + 明确原因（决策 6）；`isolation.worktree_root` 提供配置逃生口（SC-010） |
| `worktree_root` 配置成一个已被 git 跟踪的仓内目录 ⇒ 重新引入「污染仓库」问题 | 配置值**不做**合法性拦截（避免误伤合法布局），但在 `design.md` 明确记录该后果；默认值已避开 |
| `branch` 模式的脏树拒绝可能让习惯「随手切分支」的用户感到受阻 | 错误信息直接给出两条出路（commit/stash 或 `--isolate worktree`）；决策 5 已论证这是有意的取舍 |
| 移除 `_setup_parallel_worktrees` 会连带删掉 V2.8「双 Agent Kickoff」的**唯一**实现痕迹 | CHANGELOG 记录移除原因与它当时的语义（决策 9），使将来要做该功能时能从历史里找到设计意图 |
| 新增 `isolation` 配置项后，`guard.py` 等既有读取方若用严格 schema 校验会报未知键 | 已核实既有读取方全部走 `.get()`（`guard.py:796`/`:389`）；本 change 不引入严格校验 |
| 单测无法覆盖「两处 ACTIVE_CHANGE 互不干扰」——它需要真 git + 真 CLI | 由 `canonical/specs/agent/*.yaml` 定义端到端验证（沙箱仓 + 两条 worktree），作为 BUILD 阶段的独立证据链 |
