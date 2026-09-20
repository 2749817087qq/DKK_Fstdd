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
