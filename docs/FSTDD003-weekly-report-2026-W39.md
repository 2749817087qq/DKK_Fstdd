# FSTDD 产物周汇总报告（2026-W39）

> **统计窗口**：2026-09-21（周一）~ 2026-09-27（周日），共 7 个完整自然日
> **报告生成日**：2026-09-28（周一 15:47）
> **前周报告**：[2026-W38](FSTDD003-weekly-report-2026-W38.md)

---

## 一、概览

| 指标 | 数值 | 环比 W38 |
|------|------|----------|
| 新增 skill（去重唯一名） | **4** | ↓ 16（W38=20） |
| 新增经验文档 | **22** | ↓ 5（W38=27） |
| 经验文档 severity 分布 | high **17** / medium **5** | high 占比 77%（W38=37%） |

**判定说明**：
- skill 目录 mtime 全落在窗口内（09-21 ~ 09-23），反映的是该周内实际产出。
- 经验文档按文件名日期 `FSTDD003-EXP-20260921` ~ `FSTDD003-EXP-20260927` 计入，共 22 篇。
- 09-28 11:43 的 `FSTDD003-EXP-20260927-SCPLEAK-1.md` 文件名日期为 09-27，落在窗口内；`FSTDD003-EXP-20260927-ANDLIMIT-1.md` 同理。

---

## 二、新增 Skill 清单

| # | 目录名 | mtime | 来源 | 一句话说明 |
|---|--------|-------|------|-----------|
| 1 | `FSTDD003-memory-detail-sink` | 09-21 00:13 | skills-archive | MEMORY.md 超限后的「专题沉 DETAIL」流程：把单工作区模块实现细节整块搬到 `DETAIL-<主题>.md`，主档只留跨领域铁律 + 一行指针。 |
| 2 | `FSTDD003-windows-junction-selfcontained` | 09-21 09:10 | skills-archive | Windows 目录联接做「代码自包含 + 数据留原地」，含三大静默坑的完整可复用实现（删联接、NT 前缀、git 入库）。 |
| 3 | `FSTDD003-silent-failure-guards` | 09-22 00:15 | skills-archive | 静默失败：不报错但功能不生效——九个高发模式 + 「守卫要能咬人」的变异测试纪律。 |
| 4 | `FSTDD003-electron-renderer-web-mount` | 09-23 03:53 | skills-archive | 把 Electron 桌面应用渲染层搬进普通 Web 服务里跑起来，用于「照真实界面重写」而非照记忆手搓。 |

**来源分布**：全部来自 `skills-archive/`，`artifacts/skills/` 本周无新增。

---

## 三、问题与改善方法清单

按主题聚类，每条摘要取自经验文档的「现象 / 根因 / 处理（本次规避） / 建议修法」。

### 3.1 参数被解析但不被消费（7 篇 · 全 severity=high）

> **核心模式**：CLI 参数被父 parser 接住、传递到 handler，但 handler 内零引用。不报错、不警告、打印正常成功文案。

| EXP | 缺陷 | 根因 | 建议修法 |
|-----|------|------|---------|
| `20260923-GATE-1` | `gate approve --dry-run` 预览即真确认，把「防 AI 自批」的最后人工门一起放行 | `gate.py` 中 `grep dry_run` → 0 命中；父 parser 的 `--dry-run` 从未被子命令消费 | ① `gate approve` 消费 `--dry-run`：只打印「将写入哪些字段」后 `return`；② 分发层统一拦截写盘函数，漏判时**抛异常** |
| `20260924-CANON-1` | `canon generate --dry-run` 不 dry（真写 `proposal.md`） | `canon.py` 的 handler 不读 `dry_run`，与 GATE-1 同型 | 让 `--dry-run` 真的 dry；与全命令参数审计合并 |
| `20260924-CANON-2` | `--type {proposal,design,spec}` **被静默忽略**，无论传什么都只写 `proposal.md`；`--all` 复活已归档 change | `gen_type` 传了但不用；`--all` 扫项目级 canon 而非 change 级 | `_generate_one` 按 `gen_type` 分派，宁可报「未实现」也不能静默给错东西 |
| `20260924-PHASE-1` | `phase advance` 把已过门阶段的 `status` 从 `completed` 静默降回 `in_progress`，且 `target_phase` 位置参数被完全忽略 | `setdefault(nxt, {})["status"] = "in_progress"` 无条件覆盖；`args.target_phase` 从不被读取 | ① `advance` 加「禁止降级」守卫（一行）：已 `completed` 的不许改回；② 读取 `target_phase` 或明确报错 |
| `20260924-MODE-1` | `complexity_score` / `mode` / `score_confidence` 三字段**没有任何 CLI 写入端**，Phase 1 走完仍为 null | `new.py` 硬编码默认值 + 注释承诺「set by Phase 1 Step 3.5」；`gate.py` 中 `grep mode` → 0 命中 | 给 Gate 1 加 `--mode` / `--complexity-score` 参数；skill 正文必须给可复制命令 |
| `20260926-DRYRUN-1` | `phase advance --dry-run` / `phase record-slice --dry-run` 也是「预览即执行」 | 与 P44/P52 同型：`--dry-run` 是父 parser 全局开关，handler 不读 | 父 parser 的 `--dry-run` 改成显式分发给 handler；或在 handler 不读的命令上直接删掉这个参数 |
| `20260924-DELIVER-1` | Phase 4 DELIVER 三处「门在但走不通」：① 校验器查陈旧 skills 目录假 FAIL ② `structure delta` 路径基准漏 `.fstdd/` ③ `canon verify` 归档后必失败 | 三处独立的实现缺陷：默认值写错 / 同一 CLI 两套路径基准 / `verify` 与 `generate` 的兜底不对称 | 校验器自报它查的是哪里；`structure.py` 改走布局感知路径；`verify` 接上兜底 |

### 3.2 测试假绿 / 假红（3 篇 · 全 severity=high）

> **核心模式**：测试结论与原因不对应——「绿的没绿对」或「红的原因错了」。

| EXP | 缺陷 | 根因 | 建议修法 |
|-----|------|------|---------|
| `20260921-DRIFT-1` | 测试绿着但被测分支根本没执行：合取结论里藏着「无关维度」短路 | `rc=1` 是 `links_ok and files_ok and not drifted` 的合取；测试只 patch 了 `ENGINE`/`REAL`，没摘掉无关的 `LINK_DIRS`/`HARDLINK_FILES` | ① 隔离函数里显式置空无关维度；② 变异自检后必须检查「哪些保持绿」；③ CI 注入空实现验证测试有效性 |
| `20260926-FAKERED-1` | 变异自检的「假红」：`env={"PYTHONPATH": ""}` 清空整个 OS 环境 → pytest 启动即崩（WinError 10106），`rc=1` 看着像守卫咬到，实际红的理由完全错了 | `subprocess` 的 `env=` 语义是「替换」而非「叠加」，不会报错 | ① 用 `os.environ.copy()` 后改单键；② 变异夹具加「harness 自检」：先跑一条必定通过的用例 |
| `20260923-CI-1` / `20260925-CI-1` | `ci check-failures` 的四项检查口径漂移在第二个 change 上全量复发 | (d) 把「字符串出现次数」当「TC-ID 唯一性」；(b)/(j)/(l) 检查器路径与工具链布局不一致 | ① `check_tcid_unique` 改「定义唯一」；② (l) 加 change 级回退；③ SKIP 与 PASS 分开统计 |

### 3.3 工具口径漂移（3 篇 · medium/high）

> **核心模式**：检查器与脚手架/模板的约定各自演进、无人核对。

| EXP | 缺陷 | 根因 | 建议修法 |
|-----|------|------|---------|
| `20260923-DIFF-1` | `stdd diff` 两条解析口径不匹配：① 按连字符找 TC 引用而 Python 函数名只能带下划线 ⇒ 覆盖率假 0% ② 案例标题正则不接受字母 | 语言约束（Python 标识符不允许连字符）造成的必然错配 | TC 引用比对改成「规范化后比对」（去掉分隔符再比）；案例标题正则放宽到 `[\w.]+` |
| `20260927-ANDLIMIT-1` | `validate.py` 的 AND 数量上限是硬编码绝对值 5、且不归属到具体 Scenario | 上限无来源、无配置；全文计数而非按 Scenario 归一化 | 改成按 Scenario 归一化计数；上限提为配置项 |
| `20260926-NEWNAME-1` | `fstdd new` 自动补日期前缀 ⇒ 传全名会建出双前缀目录，不报错 | 工具假设传纯 slug，人假设传完整目录名——两个隐含约定对撞 | 检测到 name 已以 `YYYY-MM-DD-` 开头时当完整名用或报错 |

### 3.4 Windows 文件系统（2 篇 · 全 severity=high）

| EXP | 缺陷 | 根因 | 建议修法 |
|-----|------|------|---------|
| `20260921-JUNCTION-1` | 目录联接三坑：① `Remove-Item -Recurse` 删联接会删掉目标真文件 ② `readlink` 返回 NT 前缀导致幂等失效 ③ 联接不能进 git | ① 递归删除穿透联接 ② NT 命名空间路径前缀未剥离 ③ 联接是重解析点，非普通文件 | 删联接只用 `os.rmdir()`；比较目标时剥 NT 前缀 + `normcase`；联接进 `.gitignore`；判据用 reparse tag |
| `20260921-LIFECYCLE-1` | 配置兜底只在「进程启动时」生效：服务跑起来后再拆联接，运行中的进程静默返回空 | 路径常量在导入时算出，不运行时重新探测 | 提供运行期重新探测入口（`live_status()`）；告警文案按「谁在什么时刻看到的」分叉；验证时一定跑「坏掉」的分支 |

### 3.5 对账 / 履约盲区（2 篇 · high/medium）

| EXP | 缺陷 | 根因 | 建议修法 |
|-----|------|------|---------|
| `20260921-RECUR-1` | 对账机制的结构性盲区：周期性义务未物化为独立回执文件名，22 轮「0 待补」全是假阴 | 对账单位是文件名不是义务；条款级对账能力为零；「只从收找复」的规则把盲区焊死 | ① 给周期性义务独立文件名契约（最高性价比）；② 对账增加条款级第二层；③ 区分「任务」与「观察项」 |
| `20260927-SCPLEAK-1` | `scp -r` 批量传输窗口（4-6min）内的并发写丢失，靠下一轮对账兜底 30-60s 闭环 | `scp -r` 是快照式传输（先列目录再传），无增量语义；对账兜底在下一轮而非本轮 | ① 收尾追加差集比对（⭐⭐⭐⭐⭐，本节点侧自解）；② 切 rsync + 断点续传；③ 降低并发窗口 |

### 3.6 发布 / 版本管理（1 篇 · severity=high）

| EXP | 缺陷 | 根因 | 建议修法 |
|-----|------|------|---------|
| `20260921-RELEASE-1` | commit message 声称升版，但版本 blob 未被任何提交引用（对象库存在 ≠ 已发布） | `git cat-file -e` 验证的是「对象存在性」而非「对象可达性」；版本号来源不唯一 | ① 验版本必须解析树里引用的 blob，不读 commit message；② 加可达性断言；③ 版本号单一来源（SSOT） |

### 3.7 脚本改写错误（1 篇 · severity=high）

| EXP | 缺陷 | 根因 | 建议修法 |
|-----|------|------|---------|
| `20260923-SCRIPT-1` | `re.sub` 回调返回 `m.group(0) + 后续上下文`，内容被重复插入，脚本仍打印「已改写 19 处」 | `re.sub` 回调返回的是替换文本，不是从匹配点开始的整段新文本 | ① 机械改写脚本必须自带量纲校验（命中处数 / 行数 / 静态检查条数）；② 能用结构化手段就别用正则 |

### 3.8 流程 / 运维（2 篇 · medium）

| EXP | 缺陷 | 根因 | 建议修法 |
|-----|------|------|---------|
| `20260921-FLOW-1` | `fstdd init` 不生成 `.fstdd/version.yaml`；新 change 的 `--help` 与 skill 命令示例不一致 | 初始化步骤遗漏 | 补入版本文件生成步骤 |
| `20260923-DAEMON-1` | 轮询守护 499 canceled：前台 scp/ssh 耗时超网关超时 → 自动转后台 → 网关报 499 | 前台阻塞调用超过网关超时阈值 | 所有远程传输 `run_in_background=true` + `TaskOutput(block=true)` 等待；判成败只看文件系统 |

---

## 四、趋势与待改善项

### 4.1 与 W38 对比

| 维度 | W38 | W39 | 趋势 |
|------|-----|-----|------|
| 问题总数 | 27 篇 | 22 篇 | ↓ 19% |
| high 占比 | 37% (10/27) | 77% (17/22) | ↑ 40pp |
| 主题集中度 | 6 大主题分散 | 3 大主题突出（参数静默忽略 / 测试假绿假红 / 口径漂移） | → 更聚焦 |
| FSTDD 工具链相关 | 12/27 (44%) | 18/22 (82%) | ↑ 38pp |

**结论**：问题数量下降但严重度上升。W39 的问题高度集中在 FSTDD CLI 工具链自身——「参数被解析但不被消费」是贯穿 7 篇经验文档的核心模式，占全部问题的 32%。这是系统性问题，不是偶发。

### 4.2 本周新沉淀的通用教训

1. **「红了」不是证据，「红的理由」才是**——变异自检不仅要验「变了就红」，还要验「红的理由正确」（FAKERED-1）。
2. **「0 错误」可能是假象**——SKIP 与 PASS 同权时，3 项检查可能从来没跑过，但汇总显示全绿（CI-1 系列）。
3. **「描述一条不存在的代码路径的注释，比没有注释更贵」**——`new.py:61` 的「set by Phase 1 Step 3.5」和 `canon.py:309` 的「from template or direct mapping」都在描述不存在的逻辑（MODE-1 / CANON-1）。
4. **规避手段写在文档里，换一个工作区就会全量复发**——CI 口径漂移在两个 change 上逐条复现，教训是：用户侧规避必须落成上游源码修复或项目模板默认值（CI-1-25 元结论）。
5. **对账覆盖 = 有独立命名契约的义务集合**——嵌在正文里的周期性承诺必须物化为独立文件名，否则对账永远看不见它（RECUR-1）。

### 4.3 值得沉淀为 Skill 的改善方法

| 候选 Skill | 来源 | 优先级 | 说明 |
|------------|------|--------|------|
| **`fstdd-parameter-audit`** | GATE-1 + CANON-1/2 + PHASE-1 + MODE-1 + DRYRUN-1（7 篇） | **最高** | 全命令参数审计 SOP：grep 每个参数名在 handler 中是否被引用，凡定义在父 parser 但 handler 不读的一律补上或删掉 |
| **`mutation-harness-selftest`** | DRIFT-1 + FAKERED-1 | **高** | 变异夹具三道自证：① 变异体自证（文件真变了）② harness 自证（必定通过的用例先跑）③ 失败归因自证（打印失败断言，排除环境级异常） |
| **`scp-diff-check`** | SCPLEAK-1 | **高** | `scp -r` 前后各 `ssh ls` 做差集比对，非空则单文件循环补拉——本节点侧自解，实测 3 次漏拷全部 10s 内补齐 |
| **`windows-fs-safety`** | JUNCTION-1 + LIFECYCLE-1 | **中** | Windows 目录联接操作纪律（删联接只用 `os.rmdir` / NT 前缀剥离 / reparse tag 判据 / 配置兜底作用域声明） |
| **`fstdd-ci-workaround`** | CI-1(23) + CI-1(25) + DIFF-1 | **中** | CI/diff 口径漂移的手工补做清单（SKIP 逐项手工补做 + 结论写进 test-report） |

> **注**：`fstdd-experience-archive`（已落地）、`silent-failure-guards`（本周新增 skill）、`windows-junction-selfcontained`（本周新增 skill）已覆盖部分场景。

### 4.4 待改善项（按性价比排序）

| # | 改善项 | 优先级 | 预期收益 | 涉及 EXP |
|---|--------|--------|---------|---------|
| 1 | 全命令 `--dry-run` / 参数审计（修 FSTDD CLI 根因） | **P0** | 消除 7 篇经验文档描述的同一族问题 | GATE-1, CANON-1/2, PHASE-1, MODE-1, DRYRUN-1, DELIVER-1 |
| 2 | `gate approve --dry-run` 消费该参数 | **P0** | 安全机制不能依赖「不存在的功能」 | GATE-1 |
| 3 | `phase advance` 加「禁止降级」守卫 | **P0** | 防止已确认的门被无声撤销 | PHASE-1 |
| 4 | `check_tcid_unique` 改「定义唯一」 | **P1** | 消除 CI 误报（两篇 CI 经验文档的同一根因） | CI-1(23/25) |
| 5 | `canon verify` 接上兜底 + 支持归档后运行 | **P1** | 使 DELIVER 流程可执行 | DELIVER-1, CANON-2 |
| 6 | `new` 自动检测已含日期前缀 | **P1** | 消除静默双前缀 | NEWNAME-1 |
| 7 | 周期性义务物化为独立文件名契约 | **P1** | 消除对账结构性盲区 | RECUR-1 |
| 8 | `scp -r` 收尾追加差集比对 | **P1** | 消除传输窗口内漏拷 | SCPLEAK-1 |
| 9 | AND 数量检查按 Scenario 归一化 + 配置化 | **P2** | 消除判据密集型 spec 的误报 | ANDLIMIT-1 |
| 10 | 变异夹具加 harness 自检 | **P2** | 消除假红 | FAKERED-1 |

---

## 五、简要结论与建议

### 本周结论

**FSTDD CLI 工具链的参数消费机制存在系统性缺陷。** 本周 22 篇经验文档中有 7 篇（32%）描述了同一族问题：CLI 参数被父 parser 解析后传递到 handler，但 handler 不消费该参数。这不是偶发的编码疏忽，而是架构层面的模式问题——父 parser 的 `--dry-run` 与若干子命令参数在分发层缺乏统一的消费/拒绝机制。

**问题严重程度在上升。** high 占比从 W38 的 37% 跃升至 W39 的 77%，说明本周撞到了更深层的工具缺陷，而非表层的操作失误。

**规避手段的持久性不足。** CI 口径漂移在两个 change 上逐条复现（CI-1-23 与 CI-1-25），证明「写在文档里的规避」在换工作区后全部失效。必须落成上游源码修复或项目模板默认值。

### 建议

1. **立即（本周）**：执行 `fstdd-parameter-audit` 全命令审计，产出修复 PR 覆盖 `gate.py` / `canon.py` / `phase.py` / `new.py`。这是消除最大单族问题（7 篇经验文档）的唯一根治手段。
2. **短期（两周内）**：把 `check_tcid_unique` / `canon verify` / `new` 检测三处 P1 修复合入，消除 CI 误报与 DELIVER 阻断。
3. **中期（本月）**：在 FSTDD 项目脚手架模板中固化 CI/diff 口径的默认约定（交叉引用走案例号、TC-ID 只统计定义行等），消除「换个工作区就复发」的问题。
4. **持续**：每周一汇总报告继续生成；若下周参数审计修复落地，该族问题应显著下降。

---

*报告自动生成。全部操作限于 WorkBuddy AI 内部（本地目录与本机记忆），未触外网、未向外发送数据。*
