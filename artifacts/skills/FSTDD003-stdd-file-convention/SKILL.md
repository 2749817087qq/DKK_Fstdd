---
name: stdd-file-convention
description: STDD V3.0.5「文件约定式」项目的 Phase 4 DELIVER 落地手册（适用于无 bin/stdd CLI 的项目）。当需要把已通过 Gate 3 的 change 归档、合并规范到 specs/ 与 canonical/ 双轨、更新 .canon-index.yaml、同步知识图谱、打版本标签时使用。含 Gate 文件落盘格式、归档目录命名、canonical 双轨一致性校验、提交范围纪律（只暂存变更相关文件）、以及无 CLI 时的等价脚本。
agent_created: true
version: unknown
license: unknown

---

# STDD「文件约定式」Phase 4 DELIVER 落地手册

**适用**：项目有 `.stdd/` 但没有 `bin/stdd` CLI（`ls bin/` 为空）。此时 `skills/deliver.md` 里的
`python bin/stdd canon verify` / `structure merge` / `knowledge merge` / `experience share`
**全部无法执行**，必须按「文件约定」手工等价实现。

**不适用**：有 CLI 的项目 —— 直接跑 CLI，不要手工拼。

---

## 与 `stdd-deliver` 的关系（边界声明，勿混用）

两者都覆盖 Phase 4，但**不是替代关系，是「流程定义」与「无 CLI 落地」的关系**：

| | `stdd-deliver` | 本技能 |
|---|---|---|
| 定位 | 上游流程定义（what / 步骤顺序 / 产出物清单） | 该流程在**无 `bin/stdd` 项目**下的可执行落地（how） |
| 命令形态 | `python bin/stdd canon verify` / `structure merge` / `knowledge merge` / `stdd gate approve` | 手工文件操作 + `scripts/*.py` 等价脚本 |
| 是否可改 | **不要改**（`stdd-upgrade` 会从 GitHub raw 覆盖 `.stdd/skills/deliver.md`） | 可自由维护（`agent_created`，升级不受影响） |
| 何时用 | 项目有 `bin/stdd` | 项目**没有** `bin/stdd`（先 `ls bin/` 确认） |

**判定顺序**：先 `ls bin/stdd`。存在 → 用 `stdd-deliver`；不存在 → 用本技能。

**Gate 3 的通道归属**（`.stdd/config.d/gates.yaml` 的 `confirmation.channels` 官方定义三种）：

| 通道 | 载体 | 谁负责 |
|---|---|---|
| `dialog` | 对话确认 | `stdd-build` 的 Gate 3 段（展示确认框） |
| `cli` | `stdd gate approve --gate 3` | `stdd-build`（**无 CLI 项目不可用**） |
| `file_token` | `GATE3_APPROVED` 文件 | **本技能 Step 1**（无 CLI 项目的唯一通道） |

→ 本技能 Step 1 的 Gate 3 落盘，**是 `stdd-build` Gate 3 在 `file_token` 通道下的实现**，
不是另立一道门。确认框内容（TC 覆盖率 / 切片完成度 / 失败模式 / E2E）由 `stdd-build` 定义，
本技能只负责把它落成文件。

**步骤编号映射**（本技能 Step N ↔ `stdd-deliver` 的 Step）：

| 本技能 | `stdd-deliver` | 说明 |
|---|---|---|
| Step 0 版本自检 | Step 0 | 同一份 `_shared/version-check.md` |
| Step 1 Gate 3 落盘 | （`stdd-build` Gate 3 的 file_token 实现） | 无对应 Step |
| Step 2 归档 | Step 1 归档变更 | 等价 |
| Step 3 合并规范 | Step 2 合并规范 | 等价（本技能补双轨一致性校验） |
| Step 4 跳过项 | Step 2.5 / 2.8 | 等价（本技能明确「默认跳过」） |
| — | Step 2.9 知识图谱 | 本技能 Step 4 表格中说明 + `scripts/stdd_knowledge_merge.py` |
| Step 5 版本标记 | Step 3 版本标记 | 等价（本技能补「提交范围纪律」） |
| — | Step 4 部署 | 本技能未覆盖，按项目实际走 |

---

## Step 0 · 版本自检（不阻断）

读 `.stdd/version.yaml` 的 `stdd_version`，与当前技能 frontmatter 的 `stdd_version` 比。
相等 → 静默继续；项目落后 → 告警但不阻断。

---

## Step 1 · Gate 3 落盘（**硬防线，不得自批**）

> ⛔ AI **禁止**静默自跑 approve。必须先展示确认框（TC 覆盖率 / 切片完成度 / 失败模式 / E2E / 设计调整 / 测试报告路径），
> 等用户明确确认后，**把用户确认原文逐字引用为 evidence** 写进 Gate 文件。不得伪造 evidence。

Gate 文件位置：`{change_dir}/GATE<N>_APPROVED`（见 `.stdd/config.d/gates.yaml` 的 `file_token_dir`）。

格式（照抄这个骨架）：

```
APPROVED by <用户> via <渠道> <ISO 时间> (+0800):

- 用户确认原文（evidence，逐字引用）：**「<原话>」**

> STDD V3.0.5 硬防线：本门由 AI 展示确认框后、经用户明确确认才落盘；
> 确认原文如上，未伪造、未静默自批。

Gate 3 (BUILD 质量验收) approved → proceed to Phase 4 (DELIVER).

## 本门锁定内容（实测，非推算）
| 项 | 值 |
|---|---|
| TC 覆盖率 | N/N 断言全通过（`RESULT: PASS`，退出码 0） |
| 权威日志 | `logs/<...>.log` |
| 切片完成度 | S1 x/x · S2 x/x ... |
| E2E | <日志路径 + ok/bad> |
| 设计调整 | ADJ-001..NNN（`requires_re_spec=false` / `requires_re_build=false`） |
| 测试报告 | `{change_dir}/test-report.md` |

## 与 Phase 3 附加约束的符合性（Gate 2 锁定项）
- ✅ <逐条对应 Gate 2 写下的约束>

## 已知问题（登记在册，不阻塞归档）
K1 ... / K2 ...
```

**同时更新 change 内的 `.stdd.yaml`**：

```yaml
gates:
  gate3_build: approved       # <用户> <时间>「<原话>」（evidence 见 GATE3_APPROVED）
gate3_confirmed_at: "<ISO>"
phase: deliver
phase_status: done
phases:
  build:
    confirmed_at: "<ISO>"     # ← 与 slices_completed 同级
```

> 坑：`phases.build.confirmed_at` 必须与 `slices_completed` **同级**缩进，不是它的子键。

---

## Step 2 · 归档

```bash
cd .stdd && mkdir -p archive
mv changes/<change> archive/<YYYY-MM-DD>-<change>
```

- 目录命名 `archive/<created日期>-<change_id>`（change 目录本身若没带日期前缀，用 `.stdd.yaml` 的 `created`）
- **被取代的 change 一并归档**：`archive/<date>-<old>-superseded/`（`changes/` 只留活跃变更）
- 归档后在归档件 `.stdd.yaml` 追加：

```yaml
status: archived
archived_at: "<ISO>"
archive_path: .stdd/archive/<date>-<change>
```

> 坑：`agent_tests/` 里的测试脚本**不随变更移动**（它留在 `.stdd/agent_tests/`），
> `.stdd.yaml` 的 `artifacts.test_script` 指向的路径保持不变。

---

## Step 3 · 合并规范（双轨）

先看 `.stdd/templates/canonical/` 下的三个模板（`proposal.yaml` / `spec.yaml` / `agent_spec.yaml`），
**按模板的字段名生成**，不要自创结构。

产出 4 个文件 + 1 个索引：

| 轨道 | 路径 |
|---|---|
| Human View | `specs/<capability>/spec.md` |
| Canonical proposal | `canonical/proposals/<date>-<change>.yaml` |
| Canonical spec | `canonical/specs/<capability>.yaml` |
| Canonical agent_spec | `canonical/specs/agent/<capability>.yaml`（验证检查点 CP-1..CP-N） |
| 索引 | `.canon-index.yaml` |

用 `scripts/stdd_canon_merge.py` 生成（见下），然后**必须做双轨一致性校验**：

```python
# REQ / SC 集合在 canonical 与 Human View 之间必须完全相等
req_c = {r["id"] for r in canon["requirements"]}
req_h = set(re.findall(r"^### (REQ-[0-9-]+)", hv_text, re.M))
assert req_c == req_h
```

> 坑：Human View 里若在「增量 Scenario」表格中重复列出 SC，正则计数会偏大 —— **比对集合，不要比计数**。
>
> ⛔ **坑（实测）：先确认 Human View 的 REQ 标题里到底有没有 REQ 编号。** 上式正则只匹配
> `### REQ-001 · ...` 这种标题。若本项目的 Human View 生成器写的是
> `### Requirement: <描述文本>`（**标题里没有编号**），`req_h` 会是**空集**，
> `assert req_c == req_h` 就会**假 FAIL**（canonical 5 条 vs human 0 条），而双轨其实完全一致。
> 此时改用**数量 + 描述逐条相等**：
>
> ```python
> # Human View 标题无编号时的等价校验：按顺序逐条比对描述文本
> h_reqs = re.findall(r"^### Requirement:\s*(.+)$", hv_text, re.M)
> assert len(h_reqs) == len(canon_reqs), (len(h_reqs), len(canon_reqs))
> for (rid, desc), hline in zip(canon_reqs, h_reqs):
>     assert desc.strip() == hline.strip(), (rid, desc, hline)
> # SC 用编号，仍然比集合：
> h_sc = set(re.findall(r"^#### Scenario:\s*(SC-\d+)", hv_text, re.M))
> c_sc = {s["id"] for r in canon_reqs for s in r["scenarios"]}
> assert c_sc == h_sc
> ```
>
> 先 `head -20` 看一眼 Human View 的标题长什么样，再决定用哪种校验 —— 不要照抄上式就跑。

**MODIFIED capability**（`specs/<capability>/` 已存在）→ 合并新增 REQ，并在文件里标注
「变更日期 + change 名称」，不要覆盖。

---

## Step 4 · 跳过项（默认行为，不要反问用户）

| 步骤 | 默认 | 说明 |
|---|---|---|
| Step 2.5 structure merge | **跳过** | 项目若无 structure 索引文件 → 该能力未启用，输出一行说明即可 |
| Step 2.8 经验上传 | **跳过** | `stdd experience share` 会 POST 到外部站点，属数据外发。仅用户**显式要求**时才做，且需二次确认 |
| Step 2.9 知识图谱 | 照常（仅本地+只读拉取） | 用 `scripts/stdd_knowledge_merge.py` |

---

## Step 5 · 版本标记（**提交范围纪律**）

```bash
git status --short          # 先看清楚有多少无关改动
```

**只暂存本次变更相关的文件**，逐个显式列出：

```bash
git add <新脚本> <改动的编排文件> \
        .stdd/agent_tests/test_<change>.py \
        .stdd/archive/ .stdd/experiences/<change>.md \
        .stdd/specs/ .stdd/canonical/ .stdd/.canon-index.yaml .stdd/knowledge/
```

**先看仓库既有约定**再决定要不要带 `.stdd/`：

```bash
git log --oneline -5 --name-only     # 看历史提交是否包含 .stdd/changes/**
```

- 历史提交含 `.stdd/` → 本次也带
- 历史提交不含 → 只提交代码，`.stdd/` 保持本地

> 坑：**不要把 `.stdd/` 脚手架**（`config.d` / `onboarding` / `platforms` / `skills` /
> `standards` / `templates` / `version.yaml`）顺手一起提交 —— 那是安装器产物，
> 若历史从未提交过，单独作为一次决策，不要夹带进变更提交。

提交信息沿用仓库既有风格（先 `git log` 看），常见 `<type>(<scope>): <描述>(STDD)`：

```bash
git commit -F <msg_file>      # 中文多行信息写文件，避免 shell 转义问题
git tag -a <change>-<YYYYMMDD> -m "<变更摘要 + 归档路径>"
# 不自动 push，由用户决定
```

---

## 附：本机踩过的坑（通用性较高）

1. **解释器路径大小写**：项目 `daily_etl.py` 里写死的是 `~/.workbuddy/binaries/python/...`，
   而系统提示给的是 `~/.workbuddy-ai/...`。**两个目录可能都存在**，但跑项目脚本要用项目自己那个。
   → 永远 `grep -n "VENV_PY\|MANAGED_PY" <项目脚本>` 确认真实路径，不要凭系统提示猜。
2. **`yaml.safe_dump` 写中文**必须 `allow_unicode=True`，否则变成 `\uXXXX`。
3. **`yaml.safe_load` 遇反引号开头会炸**：`ScannerError: found character '\`' that cannot start any token`。
   值以 `` ` `` 开头时必须加双引号包裹。spec.yaml 里写 ``given: `tdx_kline_daily` 为空`` 就会踩。
4. **社区知识图谱可能 404 或连接被拒** → 按降级策略转「仅本地」，不阻断 DELIVER，把错误记进 `meta.community_error`。
5. **脚本落点**：`_etl_tmp/` 之类的 scratch 目录通常被 gitignore，脚本放那里会丢 →
   要么放进技能目录，要么提交进仓库。
6. **`stdd_canon_merge.py` 有三处硬编码前提，任一不符就废**（实测，工作台项目 2026-09-27）：
   ① `BASE = os.path.join(ROOT, ".stdd")` 写死 `.stdd`（项目可能是 `.fstdd`）；
   ② 读的是 **change 根下的扁平 `spec.yaml`** —— 若项目 Phase 2 直接产出的是
      `canonical/specs/code/*.yaml` + `specs/<capability>/spec.md`，change 根下没有 `spec.yaml`，
      脚本直接 `[FATAL] 找不到 spec.yaml`；
   ③ 它把 `.canon-index.yaml` 写成 **`entries:` 列表** schema，而不少项目用的是
      `proposals:` / `specs.agent:` / `specs.code:` **三个 map**（键分别 = change_id / change_id / capability 名）。
      已有索引的项目**跑一次就会把索引整个重写成不兼容结构**。
   → 结论：先比对目标项目既有 `.canon-index.yaml` 的 schema 与 change 目录结构，
      不符时**放弃脚本，改为「整棵复制 + 文本手工 upsert」**（能保留原注释与键序）。
7. **MODIFIED capability 的 Human View 不要覆盖重写**：项目惯例通常是**新块前置**，
   用 `<!-- 合并自 <change> -->` 分隔本次增量与旧内容（实测样例：本次 change 的 scenario 块
   插在文件顶部，标记行在其后、旧 `# Spec:` 标题之前）。纯新增 capability 才是整文件新建。
8. **Gate 3 通道别自作主张**：本技能 Step 1 说 `file_token` 是「无 CLI 项目唯一通道」，
   但不少项目全程只用 **`dialog` 通道**（确认只记在 `.stdd.yaml` / `.fstdd.yaml` 的
   `phases.build.confirmed_*` 四键里，**不建** `GATE3_APPROVED` 文件）。
   → 动手前先 `find .stdd/ -name 'GATE*'` 并看既有归档件里有没有 gate 文件：
      **全仓都没有 → 沿用项目惯例，不要为了「符合技能」凭空造一个新通道文件。**
9. **归档件状态字段的两种写法，都要接受**：有的项目归档后 `phases.deliver.status` 仍停在
   `in_progress`（无 CLI 无法推进，属遗留），有的写成 `completed` 并加 `completed_at`；
   有的项目归档件**没有** `archived_at` / `archive_path`（本技能 Step 2 建议加，加了无害 ——
   前提是先 `grep -rn archived_at` 确认没有脚本在读该 key，加了不会破坏别的）。
10. **`.stdd/changes/` 通常不入库、`.stdd/archive/` 入库**：`changes/` 是临时工作区（
    未跟踪但也没被 gitignore），归档那一刻才成为版本控制对象。
    → Step 5 的 `git add` 里写 `.stdd/archive/` 是对的；但**别顺手 `git add .stdd/changes/`**
       把别的活跃 change 一起带上。提交前用 `git add -n <paths>` 干跑一遍看真实入库清单。
11. **tag 命名随项目走**：先看 `git tag --list`。有的项目用 `<change>-<YYYYMMDD>`，
    有的用 `change/<YYYY-MM-DD>-<change>`（带斜杠，与 change_id 完全同形）。照抄既有格式。
12. **知识图谱「数据不足」的判据是硬约束**：项目自有 `.stdd/skills/spec.md` 常写着
    「`knowledge-graph.yaml` 不存在或数据不足 → 跳过此步骤，不报错」。
    `nodes: []` 的空壳就是「数据不足」。此时**不要**拿本技能的 `stdd_knowledge_merge.py` 去填充它 ——
    该脚本产出 `meta` / `stats` / `nodes` 三键的 schema，会**丢掉项目原有的 `graph_version` /
    `last_merged` / `edges` 顶层键**。宁可跳过并在提交信息里写明理由。

---

## 完成输出模板

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STDD 流程完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Gate 3:   GATE3_APPROVED 已落盘（evidence 逐字引用）
✅ 变更已归档: .stdd/archive/<date>-<change>/
✅ 规范已合并: specs/<cap>/spec.md + canonical/{proposals,specs}/
✅ 双轨一致性: REQ/SC 集合相等（N / M）
✅ 知识图谱:  <已更新 +N 节点 / 仅本地（社区不可用） / 跳过>
ℹ️ 经验上传:  已跳过（默认禁用，需显式授权）
ℹ️ structure: 已跳过（项目未启用）
✅ 版本标记:  commit <sha> + tag <tag>
🚀 未 push —— 由你决定何时推送
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
