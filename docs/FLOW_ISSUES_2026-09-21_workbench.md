# FSTDD 流程侧问题报告 · 工作台引擎副本漂移变更

- **日期**：2026-09-21
- **工作区**：`<project_root>/工作台`（Windows 11 / Python 3.13.14 / pytest 9.1.1）
- **change**：`2026-09-20-engine-drift-warn-only`（FSTDD V3.0.5 · **lightweight** 模式）
- **节点**：DESKTOP-TBJSQ5（FSTDD003）
- **本次新缺陷**：**P40 / P41 / P42**（3 条，均为「门在但没关」族）
- **配套经验**：`experiences/FSTDD003-EXP-20260921-FLOW-1.md`（P40–P42 合并条目）、
  `experiences/FSTDD003-EXP-20260921-DRIFT-1.md`（测试设计类，非 CLI 缺陷）

---

## 0. 本轮背景（为什么值得记）

本轮变更本身很小（1 个函数三态化 + 8 条测试 + 文档），
但**首次在 lightweight 模式下完整走完 Phase 1 → Phase 3**，
于是把三处「配置声明了门、实际没在执行」暴露了出来。

🔴 三条的共同形状：**声明 ≠ 事实**。配置里写着 `enabled: true` /
`lint: <命令>` / 「检查 version.yaml」，但**没有任何机制验证它真的跑起来了**。
这与本项目反复踩的「静默失效」同族（见 skill `silent-failure-guards` §6
「诊断字段报错，比没有诊断更坏」）—— 只不过这次坏的是**流程门**本身。

---

## P40（中）· `experience add` 的分类枚举**没有「测试设计」类**

### 复现

```bash
$ fstdd experience add --category test-design --pattern "…" --severity high …
  无效的 category: 'test-design'
  有效值: hallucination, scope_creep, cascading_errors, context_loss, tool_misuse,
          runtime_deviation, pipeline_break, content_quality, instruction_decay,
          coverage_vacuum, contract_gap, anchor_missing, agent_cp_failure,
          spec_ambiguity, cross_system_mismatch
```

### 分析

15 个有效值**全部**是「过程/协作失败模式」（幻觉、范围蔓延、级联错误、
上下文丢失、工具误用……）。**没有**一个是「测试本身写错了 / 断言设计有问题」这一类。

本次那条经验（**测试绿着，但被测分支根本没执行 —— 合取结论里藏着无关维度短路**）
只能塞进 `coverage_vacuum`。语义勉强对得上（都是「看起来覆盖了、实际没覆盖」），
但 `coverage_vacuum` 的常见含义是「写了测试但没测到」，而本条是
「**测到了错误的维度**」—— 不同构。归档时已在正文里显式标注这层勉强。

### 影响

- 分类失去检索价值：同类经验散进语义不匹配的桶里，`search` 出来的结果会误导。
- 迁移成本随时间上升（条目越多越不敢重编分类）。

### 建议

- 增加 `test_design` / `engineering_practice` 两个 category；或允许
  **自定义 category + 自由 tag**（现在 `--tags` 已经是自由文本，说明放开的成本不高）。
- 若坚持闭集，至少在报错信息里给出「最接近的 2 个候选 + 理由」，减少乱塞。

---

## P41（高 · 静默）· `fstdd init` **不生成** `.fstdd/version.yaml`

### 复现

```bash
$ cd <新工作区根> && fstdd init
$ ls -l .fstdd/version.yaml
ls: cannot access '.fstdd/version.yaml': No such file or directory

$ grep -rn "version.yaml" …/fstdd/cli/commands/init.py
（无输出）                       # init 完全不碰这个文件

$ grep -rln "version.yaml" …/fstdd/
…/fstdd/cli/commands/upgrade.py
…/fstdd/cli/utils.py
```

### 分析

`.fstdd/version.yaml` 的**写入方只有 `upgrade`**。而 Phase 1 Step 0 的
版本自检（`_shared/version-check.md`）明确要「检查项目 `.fstdd/version.yaml`
与技能版本是否一致」。

→ **读取方与写入方不在同一条链上**：读者假定文件存在，作者从没被要求创建它。
→ 于是**全新项目**上这道自检**从来没生效过**。

### 为什么这条算「静默」

`version-check.md` 规定「落后时**告警但不阻断**执行」。
于是「文件根本不存在」与「版本轻微落后」这两种**性质完全不同**的状态
被压成同一个「告警 + 继续跑」。本次就是被这么跳过的 ——
看起来像「轻微漂移」，实际是「门没装」。

### 建议

- **【推荐】`init` 补写 `.fstdd/version.yaml`**（哪怕只写 `version: "3.0.5"`）。
- 或退一步：版本自检把「文件不存在」与「版本落后」分成两种结论，
  前者应报「版本自检未生效」，而不是「版本漂移」。

---

## P42（高 · 静默）· `quality.yaml` 的 lint / coverage 两道门**不可执行**

### 复现

```yaml
# .fstdd/config.d/quality.yaml
quality:
  lint: "ruff check app/ tests/"       # ← app/ 在本项目不存在（工作台是 app.py 单文件）
  coverage:
    enabled: true                      # ← 声称开着
    tool: pytest-cov
    fail_under: 0
```

```bash
$ .venv/Scripts/python.exe -m ruff --version
No module named ruff

$ .venv/Scripts/python.exe -m pytest tests -q --cov=tools.setup_engine --cov-report=term
pytest: error: unrecognized arguments: --cov=tools.setup_engine --cov-report=term
```

### 分析

两处叠加：

1. **配置是跨项目模板残留** —— `lint` 指向 `app/`，而工作台的布局是 `app.py`
   + `modules/`（`app/` 是别的项目的）。
2. **工具没装** —— `.venv` 里既没有 `ruff` 也没有 `pytest-cov`。

于是 `coverage.enabled: true` 是一句**无法被证伪的声明**：门开着，但没接电。

### 🔴 真正的危害：模板会**诱导编数字**

`test-report.md` 模板 §1.1 是一张**要求填覆盖率百分比**的表：

```markdown
| 变更文件 | 行覆盖率 | 分支覆盖率 | 状态 |
```

「模板要数字 + 工具给不出数字」= **人会编一个数字填进去**。
这比「没有覆盖率」危险得多：它把一个**未知**伪装成**已知**。

### 本次处理（拒绝编数字）

在 `test-report.md` 里明写 `N/A` + **原因 + 实测的失败命令输出**，
并改用**变异测试**作为「守卫强度」的实测诊断：

```
把 ensure_engine_files 的漂移分支 if sync: → if True:（退回旧的「无条件覆盖」）
  TC_SC_060/063/064/066/067  ❌ 红   ← 该红的红了
  TC_SC_061/062/TC_SC_034    ✅ 绿   ← 该绿的绿了（同等重要）
```

**「该绿的保持绿」与「该红的红了」同等重要** —— 只报「5 条变红」
不足以证明咬对了位置（另见 `FSTDD003-EXP-20260921-DRIFT-1.md`）。

### 建议

1. **【最高】给质量门加「可执行性自检」**：Gate 3 前把 `quality.yaml` 里的
   `lint` / `coverage` 命令**试跑一次**，不可执行就**报错**，而不是静默标 N/A。
2. **【高】`test-report.md` 模板的覆盖率表补一条填法**：
   「工具缺失时填 `N/A`，并写出缺失的包名与失败命令」。
3. **【中】`quality.yaml` 按项目类型生成**：`init` 时探测项目布局
   （`app.py` vs `app/`），别把模板原样带过来。
4. **【中】覆盖率数字旁强制标注测量工具与命令**（没标注的数字一律视为未测）。

---

## P43（🔴 高）· lightweight 模式**没落地到 CLI** —— 该模式的 change 永远过不了 `validate`

### 复现

```bash
$ fstdd validate 2026-09-20-engine-drift-warn-only
 验证失败 (2 个错误):
   - 缺少必需文件: design.md
   - 缺少必需文件: test-plan.md

$ fstdd status 2026-09-20-engine-drift-warn-only
   Change: 2026-09-20-engine-drift-warn-only
    状态: active
    当前阶段: understand
    执行模式:   普通交互模式（默认）      # ← .fstdd.yaml 里明明写着 mode: lightweight
```

而 `.fstdd/config.d/lite.yaml` 对 lightweight 的规定是：

```yaml
lightweight:
  spec:
    skip_design: true          # ← 不该要 design.md
    skip_test_plan: true       # ← 不该要 test-plan.md
    canonical: "proposal_only"
    gate2: "auto_pass"
```

### 定位到源码

```python
# fstdd/cli/commands/validate.py:24
required_files = ["proposal.md", "design.md", "test-plan.md", ".fstdd.yaml"]   # ← 硬编码
```

```bash
$ grep -rln "lightweight\|skip_design" fstdd/
./cli/commands/batch.py
./cli/commands/bootcamp.py
./cli/commands/new.py
./cli/__init__.py
```

→ `validate.py` **不在**这个列表里，`phase.py` / `gate.py` / `status` 也不在。

### 分析

`lite.yaml` 里那张 `scaling` 表（lightweight 跳过 design / test-plan、
gate2 自动放行、单切片、review_agents=1 …）**目前只是技能文档里的约定**，
CLI 侧只有 `new.py` 会写 `mode`，**没有任何校验器/执行器读它**。

后果是**自相矛盾**：按流程文档走 lightweight（不产出 design.md / test-plan.md）
是**正确的**，但 `validate` 会判它**不合格**。
于是执行者面临两个都不对的选择：① 为了过 `validate` 硬造两份空壳文档
（文档从此变成噪声，且 `test-plan.md` 还会触发
`validate.py:96` 的「TC 案例数少于 Spec Scenario 数」检查 → 又一条假失败）；
② 明知 `validate` 会红而跳过它 —— **主动训练执行者忽略校验器**。

本次选了 ② 并在报告里登记，但这条路本身是有害的先例。

### 附带影响

`status` 打印「执行模式: 普通交互模式（默认）」是**事实错误**
（`.fstdd.yaml` 里是 `lightweight`）。用 `status` 判断该走哪条流程会直接走错。

### 🔴 Phase 4 期间补到的两条新证据（同一 P43 家族）

**(a) `lite.yaml` 与 `gates.yaml` 直接打架** —— 走到 Gate 3 才暴露：

```bash
$ fstdd gate approve <change> --gate 3 --confirmed-by dialog --evidence "…"
  Gate 3 cannot be confirmed: Gate 2 (spec) is not yet confirmed
```

因为 `gates.yaml` 写着：

```yaml
gates:
  phase2_spec:
    required: true                     # ← 必须人工确认
```

而 `lite.yaml` 写着：

```yaml
lightweight:
  spec:
    gate2: "auto_pass"                 # ← 自动放行
```

→ 两个配置文件对**同一道门**给出相反规定，且**没有任何校验发现它们矛盾**。
只能先手工 `--gate 2 --confirmed-by cli` 放行，再批 Gate 3。
（本次已在 Gate 2 的 `--evidence` 里写明「这是模式配置自动放行，非人工确认」，
不伪造用户确认。）

**(b) `archive` 的「Specs 已合并到 specs/」是「无条件打印」的** ——

```bash
$ fstdd archive 2026-09-20-engine-drift-warn-only
 归档完成: archive/2026-09-20-engine-drift-warn-only
 Specs 已合并到 specs/          # ← 本次根本没有 specs（lightweight 是 proposal_only）
```

实测：`find .fstdd/specs -type f` → **0 个文件**；`find .fstdd/canonical -type f` → **0 个**。
即那句「已合并」**没有任何对象**。属 P20 同族（文案与实际不符，极易被误读成「已全部合并」）。
建议：无 spec 时打印「本次无 specs，跳过合并」，而不是无条件报成功。

### 建议

1. **【最高】`validate.py` 读模式**：从 `.fstdd.yaml` 的 `mode` 取
   `skip_design` / `skip_test_plan`，据此调整 `required_files`。
2. **【高】`status` 显示真实模式**（现在是硬编码的「普通交互模式（默认）」）。
3. **【中】`lite.yaml` 的 `scaling` 表变成可被 CLI 消费的结构**
   （而不是只写在 YAML 里供 AI 阅读），否则「模式」永远只是提示词里的君子协定。
4. **【中】若坚持 `validate` 一律要求两个文件**，那就把 `lite.yaml` 里
   `skip_design` / `skip_test_plan` 删掉 —— **不要让配置与校验器互相打架**。

---

## 附：本轮**确认正常**的部分（避免把工具判死）

| 项 | 结果 |
|---|---|
| `fstdd gate approve --gate 1` | ✅ 正常；YAML → `proposal.md` 自动生成成功（`source_hash` 落盘） |
| 中文证据经 Git Bash 传入 CLI | ✅ **未乱码**（`confirmed_evidence` 原样落盘） |
| `fstdd experience add`（分类合法时） | ✅ 正常生成 `EXP-2026-0001.md`，frontmatter 字段齐全 |
| `fstdd experience add` 的**报错信息** | ✅ 质量高：直接列出全部有效值（P40 只是枚举本身缺类，不是报错问题） |
| `.fstdd.yaml` 的 baseline 机制 | ✅ 自动记录 `base_git_sha` / `node_id` / `clock_source`，可追溯 |
| Git Bash 调 CLI（经 `cygpath -m`） | ✅ 一次通过，**未**复现 P15 |

---

## 遗留项（本轮新增）

- [ ] **P40 待修（中）**：`experience` 分类枚举无「测试设计 / 工程实践」类。
- [ ] **P41 待修（🔴 高 · 静默）**：`init` 不生成 `.fstdd/version.yaml`
      → 版本自检在新项目上**从来没生效过**，且被「告警不阻断」掩盖。
- [ ] **P42 待修（🔴 高 · 静默）**：`quality.yaml` 的 `lint` / `coverage`
      两道门不可执行（配置指向不存在的 `app/` + 工具未装），
      而 `enabled: true` + 模板要覆盖率数字 → **诱导编数字**。
- [ ] **P43 待修（🔴 高）**：lightweight 模式**没落地到 CLI** ——
      `validate.py:24` 的 `required_files` 硬编码要 `design.md` + `test-plan.md`，
      而 `lite.yaml` 规定 lightweight 跳过这两份；且 `lightweight`/`skip_design`
      只被 `new.py`/`batch.py`/`bootcamp.py` 读，`validate`/`phase`/`status` 都不读。
      → **该模式的 change 永远过不了 `validate`**，逼执行者要么造假文档、
      要么学会忽略校验器（后者更糟）。`status` 还硬编码显示「普通交互模式（默认）」，
      与 `.fstdd.yaml` 里的 `mode: lightweight` 不符。
