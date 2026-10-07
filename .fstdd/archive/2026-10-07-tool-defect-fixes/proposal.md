# 工具链契约保真：6 个既有缺陷修复（声明 = 行为）

<!-- source_hash: 8be04ae641046ce6 -->
<!-- generated_at: 2026-10-07T12:17:43+00:00 -->
<!-- canonical: canonical/proposals/2026-10-07-tool-defect-fixes.yaml -->

## Why

FSTDD 工具链有 6 处**声明与行为不一致**的既有缺陷 —— 工具的文档 / 参数 / 默认行为
与其实际动作不符，使用者据声明作出的判断会被误导。逐条（均为实测复现，非推测）：

1) `fstdd phase advance <change> --dry-run` **会真实推进阶段**。
   `--dry-run` 在 `upstream/fstdd/cli/__init__.py:13` **全局注册**（help 写「预览操作，
   不实际修改文件系统」），对**所有**子命令可见；其余命令均已按统一范式实现
   （`dry_run = getattr(args, "dry_run", False)` + 早返回，如 archive.py:22,42 / init.py:108,109），
   **唯独 `phase.py` 全文 0 处 `dry_run`**（198 行）⇒ 该参数被静默忽略后**落盘**
   （实测把 `understand` 推到 `spec` / `in_progress`）。
   危害：使用者以为「先预览一下」，实际已经改了状态 —— 且因为别的命令都能用，
   更不会怀疑 phase 不行。

2) `experience verify` 会把 `.fstdd/experiences/.experience-index.yaml` 写成 **CRLF**。
   `_save_index()`（experience.py:274）用 `open(tmp, "w", encoding="utf-8")` 未传 `newline=""`，
   Windows 上按平台默认写成 CRLF ⇒ 与仓库 `.gitattributes`（`* text=auto eol=lf`）冲突，
   撞 `tools/verify_eol.py` 的 TC-EOL-003「混合态文件清零」（实测该文件 CRLF=322 / LF=0）。

3) `fstdd extract-proposal <change>` 的 `capabilities` / `impact` / `constraints` **恒返回空**。
   渲染器（canon.py:360-370）把 `### New/Modified Capabilities` 挂在 `## What Changes` 之下，
   而解析器（extract_proposal.py:41）找的是 `## Capabilities` h2 ⇒ 永远匹配不到。
   连带后果：capability 条目被当作 `what_changes` 解析出来（实测 4 条 capability 混入 what_changes）。
   危害：任何依赖 extract-proposal 的自动化（Phase 1 Step 3.5 提案审查等）拿到的是空 / 错数据。

4) `fstdd ci check-failures` 的 (d) 检查把**任何重复提及**判为「重复 TC-ID」。
   ci.py:317-323 用 `re.findall` + `count > 1`，而项目约定是在「案例标题 + 优先顺序 +
   回归矩阵 + 证据表」多处引用同一 ID ⇒ **41 份 test-plan 中 25 份（60%）被判 FAIL**。
   危害：门禁的 ❌ 变成噪声，真正的 ID 冲突反而被淹没。

5) `fstdd experience list --format json` **直接崩溃**。
   experience.py:468 `json.dumps(experiences, ...)` 未传 `default=str`，
   而条目含 `date` 对象 ⇒ `TypeError: Object of type date is not JSON serializable`。
   危害：`--format json` 完全不可用（只有文本模式能用）。

6) `tools/verify_notices.py` 的默认处置是**移动文件**（隔离 = 破坏性副作用）。
   CLI（第 295-299 行）**只有 `--json` / `--strict`，没有 dry-run 或显式开关**
   ⇒ 在任何目录上跑一次就会把命中的文件 `shutil.move` 走（第 220 行，主流程内无条件执行）。
   实测（EXP-2026-0015 二次命中）：对仓库根运行会把 `README.md`（**带未提交改动**）等
   3 个已跟踪文件移走。危害：有丢失未提交工作的风险，且与 docstring 自述「不写业务文件」矛盾。

共同主线：**契约断层** —— 声明形态（docstring / 参数名 / 参数语义 / 检查判据）与
实际可执行形态不一致。与经验库 EXP-2026-0013「(k) 契约断层」同族。


## What Changes

- phase：按既有范式让 `--dry-run` 真的不落盘 —— `cmd_phase` 读 `getattr(args, "dry_run", False)`，为真时只打印将发生的变更并正常退出，不写 `.fstdd.yaml`；并新增**防复发契约测试**：扫描全部子命令模块，凡含写操作者必须出现 `dry_run` 处理（否则 FAIL），使「声明了 `--dry-run` 却静默忽略」不再复发
- experience：索引写盘统一 LF —— `_save_index()` 的 `open(...)` 补 `newline=""` 并显式使用换行符，消除 CRLF 污染
- experience：`--format json` 可序列化 —— 输出路径补 `default=str`（或统一经 `_jsonable()` 归一），并复核同文件其它 `json.dumps` 调用点
- extract-proposal：解析器与渲染器锚点对齐 —— `_parse_capabilities()` 同时接受 h2 `## Capabilities` 与 h3 `### New/Modified Capabilities`；并把 capability 段从 `what_changes` 解析中排除（消泄漏）
- ci：重定义 (d) 检查判据 —— 从「全文出现次数」改为「test-plan 中 TC-ID 的**定义点**唯一」（表格 ID 列 / 案例标题行），重复引用不再判 FAIL；同时评估该检查的扫描面口径
- verify_notices：破坏性默认改为显式 opt-in —— 默认只**报告**命中项（不动文件），新增 `--quarantine` 才执行移动；`--json` 输出补 `would_quarantine` 字段；docstring 与行为对齐

## Capabilities

### New Capabilities


### Modified Capabilities

- **dry-run-fidelity**：声明了 `--dry-run` 的命令必须真的不产生落盘副作用（可预览、可安全试跑）
- **experience-io-contract**：经验库的落盘与输出遵守契约：索引文件行尾为 LF；`--format json` 在任何条目上均可序列化
- **proposal-extraction-fidelity**：`extract-proposal` 能正确解析出 capabilities / impact / constraints，且不把 capability 段混入 what_changes
- **ci-check-accuracy**：`ci check-failures` 的判据与项目实际约定一致，不把正当引用判为违规
- **quarantine-opt-in-safety**：凭证隔离是显式 opt-in 的破坏性操作；默认运行只报告、不移除任何文件

## Impact

**代码层面**：
- upstream/fstdd/cli/commands/phase.py：`cmd_phase` 增加 dry-run 早返回分支（不写状态文件）
- upstream/fstdd/cli/commands/experience.py：`_save_index()` 补 `newline=""`；`--format json` 输出路径补 `default=str`（并复核第 539 / 638 / 1186 / 1253 行）
- upstream/fstdd/cli/commands/extract_proposal.py：`_parse_capabilities()` 锚点放宽到 h3；`what_changes` 解析排除 capability 段
- upstream/fstdd/cli/commands/ci.py：`check_tcid_unique()` 判据改为「定义点唯一」
- tools/verify_notices.py：默认只报告；新增 `--quarantine`；`--json` 增 `would_quarantine`；docstring 与行为对齐
- 新增测试：覆盖 6 个缺陷的 RED→GREEN 与反向样本（防判据放宽过度）；另含一条**契约扫描测试**（写操作命令必须处理 `dry_run`）

**配置层面**：
- 无：不改 .fstdd/config.d/**、不改 .gitattributes、不改 .gitignore

**基础设施**：
- 无：不动服务器、不推远端、不改 CI / hook

## Success Criteria

- [ ] `fstdd phase advance <change> --dry-run` 执行后 `.fstdd.yaml` 的内容与 mtime 均不变（字节级比对）
- [ ] `fstdd phase advance <change>`（无 --dry-run）行为与修复前完全一致（既有 test_phase.py 全绿）
- [ ] 新增契约测试：扫描全部子命令模块，凡含写操作者必须出现 `dry_run` 处理 ⇒ 违规数为 0（修复前 `phase.py` 是唯一违规者）
- [ ] `fstdd experience verify <id>` 后 `.experience-index.yaml` 不含任何 CRLF 且行数 > 1
- [ ] `fstdd experience list --format json` 在含 date 字段的条目上返回 0，且 stdout 为合法 JSON
- [ ] `fstdd extract-proposal <change>` 的 capabilities.modified 非空（对本仓任一有 modified capability 的 change），且 what_changes 不含 `**<capability>**：` 形态条目
- [ ] `fstdd ci check-failures` 在 41 份既有 test-plan 上不再报 (d) 重复 TC-ID；构造「同一 ID 两个定义行」的样本仍报 FAIL
- [ ] `tools/verify_notices.py <dir>` 默认运行后目标目录文件数与内容零变化；加 `--quarantine` 时才移动；既有 tools/test_verify_notices.py 全绿
- [ ] 全量 pytest upstream/tests 0 failed；根 tests/ 0 failed；四自检脚本全绿
