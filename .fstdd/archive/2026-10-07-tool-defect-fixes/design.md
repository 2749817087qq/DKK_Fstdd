# 工具链契约保真（6 个既有缺陷修复）- 技术设计

> change: `2026-10-07-tool-defect-fixes` ｜ mode: thorough ｜ task_type: code
> observed_at: `2026-10-06T17:25:33+00:00` ｜ observed_base_git_sha: `0710d5462f973164f83f5096cdf739380e579fb8`

## Context

**当前状态**：FSTDD 的 CLI（`upstream/fstdd/`）与工具（`tools/`）有 6 处「**声明与行为不一致**」。
它们不是功能缺失，而是**契约断层** —— 工具的 docstring / 参数名 / 参数语义 / 检查判据
与其实际可执行形态不一致，使用者据声明作出的判断会被误导。

**技术栈**：Python 3.13（本机 `workbuddy default env`，含 PyYAML / Jinja2 / requests）；
Windows 10（本机），仓库 `.gitattributes` 为 `* text=auto eol=lf`。

**约束条件**：
- 只修工具行为，不改业务数据 / 凭证判定规则 / 知识图谱 / 经验条目内容。
- 不删除任何既有测试用例。
- 既有测试面较大且全部为绿，改动必须零回归：
  `test_ci.py`(516 行) / `test_phase.py`(258) / `test_experience.py`(930) /
  `test_experience_v29.py`(352) / `tools/test_verify_notices.py`(489)。

**外部输入（Phase 2 Step 2 / 2.5）**：

| 来源 | 命中 | 转化为设计约束 |
|---|---|---|
| **EXP-2026-0013** 契约断层（high） | 声明与实现分处两处，无参数化测试用「声明样例」校验 | **D1 / D4**：声明与实现**同源**，并用**声明形态**做参数化测试输入 |
| **EXP-2026-0016** 文本扫描假阳性（low） | CLI 用文本出现次数而非结构化映射判定 TC-ID | **D5**：改结构化「定义点」判定 |
| **EXP-2026-0015** 隔离=移动（high） | 工具以隔离为默认处置，移走合法文件 | **D6**：破坏性默认改 opt-in |
| **EXP-2026-0021** 审计工具假绿（high） | 审计器匹配面比声称的窄，且自身无自检 | **D7**：每个扫描/断言类测试**自带自检** |
| **KG-093**（high, 跨项目 12 次） | 「声明了约束，但从未生效」 | **D1 / D4**：单一事实源，声明即实现 |
| **KG-092**（high） | 「失败静默腐烂，直到有人偶然查看才发现」 | **D1 / D6**：不允许静默忽略；失败须出声 |
| **KG-094**（critical） | 「字段错位，测试全绿因为断言只覆盖少数几个字段」 | **D7**：断言须覆盖**全部**字段/条目，不得抽检 |
| **KG-095**（medium） | 「第二层防线天然不可观测」 | **D6**：破坏性操作改 opt-in 后须保留**可观测**输出 |

**现场取证（自指）**：本次 Phase 2 的 Step 1 / Step 2 本身就在缺陷现场 ——
`extract-proposal` 返回 `capabilities: {new: [], modified: []}` 并把 5 条 capability 泄漏进
`what_changes`；`experience list --format json`（无过滤）以 `TypeError: date is not JSON serializable`
退出 1。故 Phase 2 全程改用 canonical YAML 与文本模式取数。

---

## Decisions

### D1. `--dry-run` 契约同源：从「命令各自实现」改为「有写操作的命令必须处理，且由测试锚定」

**方案**：
1. `phase.py::cmd_phase` 按**既有范式**补实现：`dry_run = getattr(args, "dry_run", False)`，
   为真时打印将发生的变更（from → to、将写入的文件）并 `return`，不落盘。
2. 新增**契约扫描测试**：遍历 `upstream/fstdd/cli/commands/*.py`，凡含写操作
   （`write_text` / `open(...,"w")` / `shutil.move|copy` / `os.replace` / `mkdir` / `yaml.dump`）
   的模块**必须**出现 `dry_run` 处理，否则 FAIL。

**为什么**：`--dry-run` 在 `cli/__init__.py:13` **全局注册**（help 写「预览操作，不实际修改文件系统」），
对**所有**子命令可见；既有 8 个命令已实现，**唯独 `phase.py` 全文 0 处 `dry_run`**。
只修 phase 会留下「下一个新命令又忘」的复发口子 —— 用测试把契约钉死（对应 EXP-2026-0013 / KG-093）。

**备选方案及排除原因**：
- 备选 A：只修 `phase.py`，不加扫描测试 —— 复发无防线，KG-093 的形态会重现。
- 备选 B：把全局 `--dry-run` 删掉，只给已实现的命令注册 —— 会让 8 个已实现命令的用法变更（破坏兼容），且 `phase` 仍缺该能力。
- 备选 C：为全部 26 个写操作命令逐一实现 dry-run —— 超出本 change 范围，且多数命令的 dry-run 语义需逐个定义。
- 备选 D：`dry-run` 时用 monkeypatch 拦截所有写系统调用（"写屏障"）—— 侵入性强、对 `os.replace`/`shutil` 覆盖不全，易造成假安全。

### D2. 索引写盘：显式 `newline=""` + 显式换行符

**方案**：`_save_index()`（experience.py:274）的两处 `open(...)` 补 `newline=""`，
`yaml.dump` 输出经显式换行符拼接后写入。

**为什么**：`open(..., "w", encoding="utf-8")` 在 Windows 上按平台默认把 `\n` 翻译成 `\r\n`，
与 `.gitattributes` 的 `eol=lf` 冲突；实测该索引文件 CRLF=322 / LF=0，直接撞
`tools/verify_eol.py` 的 TC-EOL-003「混合态文件清零」。本 change 的上一版（3.3.6）
刚把行尾治理做干净，不能让它从工具侧回流。

**备选方案及排除原因**：
- 备选 A：只改 `.gitattributes` 把该文件排除 —— 治标，且 `.gitattributes` 是门禁基准文件，不宜为单个文件开洞。
- 备选 B：写完再读回做 `replace(b"\r\n", b"\n")` —— 多一次 IO，且掩盖了根因（写的时候就不该产生 CRLF）。
- 备选 C：不动（靠 git 的 `text=auto` 在 add 时归一）—— 工作树仍是 CRLF，`verify_eol` 的 `w/crlf` 判定照样红。

### D3. JSON 输出：统一经可序列化归一，而非逐处补 `default=str`

**方案**：在 `experience.py` 内引入模块级 `_json_default(o)`（`date`/`datetime` → `.isoformat()`，
其它 → `str(o)`），并把该文件内**全部** `json.dumps` 调用点（468 / 539 / 638 / 1186 / 1253）
统一传 `default=_json_default`。

**为什么**：实测无过滤 `experience list --format json` **EXIT=1**，
`TypeError: Object of type date is not JSON serializable`；根因是 **57/74 条**经验的
`exported_at` 以未加引号的 `2026-09-26` 形式存盘，`yaml.safe_load` 解析为 `datetime.date`。
逐处补 `default=str` 会漏（同文件有 5 个 `json.dumps`）—— 统一入口才不复发。

**备选方案及排除原因**：
- 备选 A：只补 468 行（报错那一处）—— 同类缺陷在 539/638/1186/1253 会原地复发。
- 备选 B：改经验条目的存盘格式（给日期加引号）—— 要改历史数据，且不解决「任意 date 对象」的通用问题。
- 备选 C：`--format json` 走 `yaml.safe_dump(..., default_flow_style=True)` —— 语义漂移，且 YAML 不是 JSON。

### D4. 解析器与渲染器**锚点同源**：渲染器补出 h2，解析器兼容 h2/h3

**方案**：
1. **渲染器**（`canon.py`）：在 `## What Changes` **之后**补出独立的
   `## Capabilities`（含 `### New Capabilities` / `### Modified Capabilities`）与 `## Impact`
   （`**代码层面**` / `**配置层面**` / `**基础设施**` 三段），即解析器所期望的形态。
2. **解析器**（`extract_proposal.py`）：`_parse_capabilities()` 锚点放宽为
   「h2 `## Capabilities` **或** h3 `### New/Modified Capabilities`」；
   `what_changes` 的解析在遇到 `### New/Modified Capabilities` 时**截断**（消泄漏）。
3. 两者共用一个模块级锚点常量元组，避免再次分叉。

**为什么**：现状是**双向不通** —— 解析器找 `## Capabilities`（渲染器从不输出），
渲染器把 `### Modified Capabilities` 挂在 `## What Changes` 下（解析器又看不到）。
实测 `extract-proposal` 返回空 capabilities，且 5 条 capability 泄漏进 `what_changes`。
另实测 `canon.py` 中 grep `Impact` = **0 命中** ⇒ `_parse_impact` 同样永远拿不到数据。
这正是 KG-093「声明了约束但从未生效」与 EXP-2026-0013 的形态。

**备选方案及排除原因**：
- 备选 A：只改解析器兼容 h3 —— `## Impact` 仍永不出现，`_parse_impact` 依旧恒空（半修）。
- 备选 B：只改渲染器输出 h2 —— 已有归档 change 的 proposal.md 仍是 h3 形态，`extract-proposal` 对历史 change 仍失败（向后不兼容）。
- 备选 C：让 `extract-proposal` 改读 canonical YAML 而不解析 MD —— 更根本，但会改变该命令的契约（它现在读 MD），且影响未知的既有调用方；记为**后续 change** 的候选。

### D5. `ci` (d) 判据：从「文本出现次数」改为「**定义点**唯一」

**方案**：`check_tcid_unique()` 不再用 `re.findall` + `count > 1`，改为按**定义点**判定：
在 `test-plan.md` 中，一个 TC-ID 的「定义点」= ① markdown 表格行里 **ID 单元格**恰为该 ID
（如 `| **ID** | TC-RTA-001 |`），或 ② 以该 ID 开头的标题/加粗行（如 `#### 案例 2.1 — …` 后的
`| **ID** | … |`）。同一 ID 出现在 **≥2 个定义点** 才判 FAIL；纯引用（优先顺序、回归矩阵、证据表）不计。

**为什么**：实测 41 份 test-plan 中 **25 份（60%）** 被现判据误判为 FAIL —— 因为项目**约定**
就是在「案例标题 + 优先顺序 + 回归矩阵 + 证据表」多处引用同一 ID。
门禁的 ❌ 因此变成噪声，真正的 ID 冲突反被淹没。EXP-2026-0016 已把该现象记为「已知假阳性」，
本次把它**真正修掉**（而不是继续记着）。

**备选方案及排除原因**：
- 备选 A：维持现状，在文档里声明「(d) 是假阳性」—— 门禁长期带 ❌，削弱「绿灯可信」。
- 备选 B：把 (d) 降级为 WARN —— 会同时放过真正的重复定义。
- 备选 C：改为「全文件只允许出现一次」并**反向要求项目改文档约定** —— 需改动 25 份历史 test-plan（含归档），代价与风险都远超收益。

### D6. `verify_notices`：破坏性默认改 **opt-in**，但保留可观测性

**方案**：
1. 默认**只报告**：`verify_notices()` 增加 `quarantine: bool = False` 形参；为 `False` 时
   命中项**不移动**，仅计入 `would_quarantine` 并打印显式告警。
2. CLI 新增 `--quarantine`（`action="store_true"`）才执行 `shutil.move`。
3. `--json` 顶层在既有四键（`results`/`quarantined`/`warnings`/`exit_code`）之外**新增**
   `would_quarantine` 键（默认模式下 `quarantined` 恒为 `[]`）。
4. docstring 与 `--help` 与行为对齐。

**为什么**：EXP-2026-0015 二次命中 —— 对仓库根运行会把带未提交改动的 `README.md` 等
3 个已跟踪文件 `shutil.move` 走，有**丢失未提交工作**的风险；而第 9 行 docstring 自称
「不写业务文件」，与「移动业务文件」的实际行为相矛盾（KG-092 静默腐烂的形态）。
隔离本身是**凭证防线**，不应取消 —— 故改为「默认报告 + 显式 opt-in 移动」，
既消除静默破坏，又保留能力。

**备选方案及排除原因**：
- 备选 A：彻底移除隔离能力 —— 会削弱凭证防线，且不符合「只改触发条件」的约束。
- 备选 B：默认改为「移入隔离区并在原地留 `.quarantined` 标记文件」—— 仍是默认写业务目录。
- 备选 C：加 `--dry-run` 而非 `--quarantine` —— `--dry-run` 是全局语义（"不改文件系统"），
  而这里需要的是「选一个**不同的**破坏性动作」，语义不匹配；用独立开关更清晰。

### D7. 全部新增断言**自带自检**，且**覆盖全部条目**而非抽检

**方案**：
- 每个新增的扫描/审计类测试，必须同时包含**正向样本**（能抓到违例）与**反向样本**（合法形态不误报），
  且反向样本须覆盖**声明形态的全部变体**（如 dry-run 的 `getattr` 与 `args.` 两种写法、
  capability 锚点的 h2 与 h3）。
- 对「枚举类」断言（如 6 个缺陷、5 个 `json.dumps` 调用点），断言**集合相等**而非「非空 / 抽检」。

**为什么**：EXP-2026-0021（审计工具假绿）与 KG-094（断言只覆盖少数几个字段，测试全绿）
都指向同一件事 —— **测试的覆盖缺口本身就是缺陷的藏身处**。
本 change 修的正是「工具骗人」，若新测试也是抽检式，等于用一个不可信的工具去证明另一个可信。

**备选方案及排除原因**：
- 备选 A：只写正向断言（能抓到就行）—— 会重演 EXP-2026-0021 的「0 命中即假绿」。
- 备选 B：只写反向断言（不误报就行）—— 会重演 D5 的「判据放宽过度 ⇒ 假阴性」。

---

## Architecture

### 缺陷 → 修复点 → 断言 的映射

```
 缺陷                     capability                        修复点                         Scenario
 ──────────────────────────────────────────────────────────────────────────────────────────────
 1 phase dry-run 落盘 →  dry-run-fidelity                phase.py::cmd_phase           SC-001..003
                                                          (+ 契约扫描测试)
 2 索引写 CRLF        →  experience-io-contract          experience.py::_save_index    SC-004..005
 5 json 崩溃          →  experience-io-contract          _json_default + 5 个调用点     SC-006..007
 3 extract-proposal 空 →  proposal-extraction-fidelity   canon.py 渲染器 +              SC-008..010
                                                          extract_proposal.py 解析器
 4 ci (d) 误判        →  ci-check-accuracy               ci.py::check_tcid_unique      SC-011..012
 6 隔离=移动          →  quarantine-opt-in-safety        verify_notices.py             SC-013..015
                                                          + main() 的 --quarantine
```

### 关键调用链（修复后）

```
 fstdd phase advance <change> [--dry-run]
   └─ cli/__init__.py 全局 --dry-run  →  args.dry_run
        └─ phase.cmd_phase
             ├─ dry_run=True  → 打印 "would: understand → spec"；不写 .fstdd.yaml
             └─ dry_run=False → 既有路径（写盘 + 打印），行为与修复前逐字节一致

 fstdd experience verify <id>
   └─ _load_index → 改条目 → _save_index(newline="") → LF 落盘
 fstdd experience list [--format json]
   └─ json.dumps(experiences, default=_json_default)   # 57/74 条含 date，必须归一

 fstdd canon generate <change>
   └─ 渲染 proposal.md：… ## What Changes … ## Capabilities … ## Impact … ## Success Criteria
 fstdd extract-proposal <change>
   └─ _parse_capabilities: 锚点 = ("## Capabilities", "### New Capabilities", "### Modified Capabilities")
        └─ what_changes 解析在首个 capability 锚点处截断

 fstdd ci check-failures <change>
   └─ check_tcid_unique：按「定义点」计数（表格 ID 单元格 / 加粗 ID 行），引用不计

 tools/verify_notices.py <dir> [--quarantine]
   └─ verify_notices(directory, strict, quarantine=False)
        ├─ 默认：命中 → would_quarantine（不动文件）+ 告警 + 非零退出码
        └─ --quarantine：命中 → shutil.move 到 tools/_quarantine/
```

### 兼容性边界

| 面 | 修复前 | 修复后 | 兼容性 |
|---|---|---|---|
| `phase advance`（无 dry-run） | 写盘 | 写盘（逐字节一致） | ✅ 不变 |
| `phase advance --dry-run` | **写盘**（缺陷） | 不写盘 | ⚠️ 行为变更（即修复） |
| `experience` 索引行尾 | CRLF | LF | ✅ 与 `.gitattributes` 一致 |
| `experience list --format json` | 崩溃 | 合法 JSON | ✅ 由「不可用」变「可用」 |
| `proposal.md` 结构 | 无 `## Capabilities` / `## Impact` | 新增两个 h2 | ⚠️ 结构变更；`extract-proposal` 对**历史** change 的 h3 形态仍兼容 |
| `ci` (d) 判据 | 文本计数 | 定义点计数 | ⚠️ 25 份历史 test-plan 由 FAIL 转 PASS |
| `verify_notices` 默认 | 移动文件 | 只报告 | ⚠️ 行为变更（即修复）；`--quarantine` 恢复原行为 |
| `verify_notices --json` 顶层键 | 4 键 | 5 键（+`would_quarantine`） | ⚠️ 新增键；既有 4 键语义不变 |

---

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| **R1** dry-run 判定放错位置，把非 dry-run 路径也变成只打印（真实推进失效） | dry-run 只加「早返回 + 打印」分支；既有 `test_phase.py`(258 行) 全量回归；新增「dry-run 后 `.fstdd.yaml` **字节与 mtime 均不变**」断言 |
| **R2** (d) 判据放宽过度 ⇒ 漏掉真正的 TC-ID 冲突（假阴性） | 保留反向断言：构造「同一 ID 出现在两个**定义点**」的样本必须 FAIL；并把 41 份既有 test-plan 的判定结果纳入回归对照 |
| **R3** `verify_notices` 默认不再移动 ⇒ 凭证形状命中的文件留在原地 | 默认仍以**非零退出码 + 显式告警**呈现命中；`--json` 增 `would_quarantine` 保持可观测（KG-095）；`--quarantine` 一键恢复原行为；`tools/test_verify_notices.py`(489 行) 全量回归 |
| **R4** 改 `newline` 后忘记显式换行符 ⇒ Windows 上写出单行文件 | 写盘时显式拼接换行符；断言同时要求「无 CRLF」**且**「行数 > 1」 |
| **R5** 渲染器新增两个 h2 后，历史归档 proposal.md 与新建的形态不一致 | 解析器**双向兼容**（h2 与 h3 都认）；`canon verify` 的 DC-HASH 只校验 YAML↔MD 的 `source_hash`，不受结构影响；对既有归档执行 `extract-proposal` 抽样验证 |
| **R6** `json.dumps` 的 `default=` 改变既有输出（如 date 变成 ISO 串） | 只在**无法原生序列化**时才调用 `default`；既有可序列化字段逐字节不变（断言：对 `--language python` 子集，修复前后 JSON 文本一致） |
| **R7** 新增的契约扫描测试本身有假阳性（把已实现的命令误判为未实现） | 该测试**自带自检**：构造一个「已实现」与一个「未实现」的最小样本模块，断言判定正确（D7）；扫描器须同时识别 `getattr(args,"dry_run",…)` 与 `args.dry_run` 两种写法 |
| **R8** 本 change 修改 `upstream/`（vendored 内核）代码，未来上游升级可能覆盖 | 属本仓已接受的既有模式（3.3.1–3.3.6 均如此）；改动点与理由在 CHANGELOG 与 design 中留档 |
