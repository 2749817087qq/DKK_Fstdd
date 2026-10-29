# 反漂移三道闸 - 技术设计

## Context

### 现状：门禁查「做完没」，不查「说得对不对」

FSTDD 现有 `ci check-failures` 聚合 15 项检查，其中与「漂移」相关的只有 (b) 范围蔓延。
实测该项对本仓**恒为 PASS/WARN，从未 FAIL 过一次**，根因有三层：

| 层 | 缺陷 | 位置 |
|---|---|---|
| 判据锚点错配 | 判「文件路径是否含 `specs/<cap>/` 或 `commands/<cap>`」，而本仓代码在 `upstream/fstdd/cli/commands/<module>.py`，与 capability 名无路径关系 | `ci.py:452` |
| 白名单过宽 | `common_dirs = {".fstdd/", "tests/", "docs/", ".github/"}` 把 change 产出物全放过 | `ci.py:450` |
| diff 范围错配 | `git diff --stat HEAD~1` 只看**最近一次 commit**；change 刚开始时 `HEAD~1` 不存在 ⇒ 直接 SKIP | `ci.py:432` |

### 已就位但未接线的能力

`guard.py` 已实现一套**扎实**的 scope 机制（V3.0.7），但只用于「相位封锁」，`ci` 侧完全没用：

```python
_load_change_scope(change_dir) -> list[str] | None
    # 读 canonical/proposals/*.yaml 的 scope.paths；任何失败路径都返回 None（fail-closed）

_is_in_change_scope(project_root, file_path, scope_patterns) -> bool
    # Path(normpath) -> 若相对则拼 project_root -> resolve(strict=False).relative_to(root)
    # 匹配：目录模式（尾 /）走前缀，其余走 fnmatch
```

**关键**：它已做 `resolve()` 归一化，`..` 逃逸在字符串层就挡得住（EXP-2026-0027 的教训已被吸收）。

### 数据源缺失的根因

只有 2 个 change 声明过 `scope`（2026-09-25 的两个），其后 40+ 个全无 —— 因为
`.fstdd/templates/canonical/proposal.yaml` **模板里没有 scope 段**。这是「范围锁从未生效」的
真正起点：不是没人想声明，是模板没给位置。

---

## Decisions

### 1. 范围锁复用 guard 的 helper，不新造

**方案**：`check_scope_creep` 直接 `from .guard import _load_change_scope, _is_in_change_scope`。

**为什么**：
- 二者已通过 EXP-2026-0027 的检验（resolve 归一化 + 输入层拒绝）；
- 同一份判据只应有**一个**实现（EXP-2026-0026：判据必须落在统一实现上，否则各写一套必然分叉）；
- 新造一套等于给未来的自己埋「两处判据不一致」的雷。

**备选方案及排除原因**：
- 备选 A：在 `ci.py` 里重写一份 scope 匹配 → 排除。两份判据必然漂移，且 `..` 归一化容易漏。
- 备选 B：把 helper 上提到 `utils.py` 让两边都 import → 排除。改动面更大（要动 guard 的 import 与测试），本轮聚焦「接线」，重构另立 change。

### 2. 严格度按「是否声明 scope.paths」自然分界

**方案**（D哥 裁决）：

| 情形 | 结论 |
|---|---|
| 已声明 `scope.paths` + 改动超范围 | **FAIL** |
| 已声明 `scope.paths` + 改动在范围内 | **PASS** |
| 未声明 `scope.paths` | **WARN** + 提示「范围锁未生效」 |
| 未声明 + `ci check-drift --strict` | **FAIL**（收尾自查口径） |
| scope 过宽（命中 `upstream/`、`tests/`、空串） | **WARN** + 提示收窄 |

**为什么**：
- 要求「只对新建 change 生效，老 change 走 WARN」⇒ 声明与否本身就是最自然的分界线，无需引入时间基准（时间基准会因机器时钟、跨时区、补建 change 而失真）；
- 与决策 7（模板补 scope 段）配合后，新 change 从模板生成即带声明 ⇒ 自动进入严格模式；
- `--strict` 给收尾自查一个更严的口径，弥补「AI 删掉 scope 段就能绕过」的漏洞。

**备选方案及排除原因**：
- 备选 A：按 change `created` 时间戳 vs 某个基准时间 → 排除。时钟不可信（本仓 MEMORY 有「出口 IP 飘」「clock_source: system」的实测坑），且补建/回填 change 的时间不可靠。
- 备选 B：按 `baseline.base_git_sha` 是否包含某个标记 commit → 排除。需要先有一个「分界 commit」，但分界本身要靠人记，不如声明自然。
- 备选 C：一律 FAIL → 排除。40+ 历史 change 全爆红，门禁立刻变噪声（正是 (b) 现在的死法）。

### 3. diff 范围用 `baseline.base_git_sha..HEAD`

**方案**：从 `.fstdd.yaml` 的 `baseline.base_git_sha` 起算，而非 `HEAD~1`。

**为什么**：
- `HEAD~1` 只覆盖**最后一次 commit**，而一个 change 通常有 2-5 个 commit ⇒ 范围蔓延只要分散在不同 commit 里就查不出；
- change 刚开始时 `HEAD~1` 可能不存在 ⇒ 静默 SKIP（当前实现的死因）；
- `baseline.base_git_sha` 由 Gate 1 时写入（`established_by: gate1`），是**本 change 的起点**，语义正确。

**备选方案及排除原因**：
- 备选 A：`git diff --name-only HEAD`（未提交改动）→ 排除。只覆盖工作区，已提交的蔓延全漏。
- 备选 B：`merge-base master HEAD` → 排除。本项目直接在 master 上开发，merge-base 就是 master tip，等于全量历史。

### 4. DELIVER 冻结只拦「新增」源文件

**方案**：`phase == deliver` 且 `phases.build.status == completed` 时，若 `baseline..HEAD` 含
`upstream/fstdd/**` 或 `upstream/tests/**` 的 **A（新增）** 状态文件 ⇒ FAIL。`M`（修改）不拦。

**为什么**：
- 收尾阶段「补个新模块 / 新测试文件」正是形态 C 的典型表现，而「修 typo / 补一行文档」是正常收尾；
- 用 git 的 `--diff-filter=A` 精确区分，不靠启发式。

**逃生阀**：`--allow-late-change "理由"` 显式放行，并写入 `.fstdd.yaml` 的 `design_adjustments`。
没有逃生阀的硬门最后一定会被人肉绕过（改判据 / 加 `|| true`），留一个**留痕**的口子更安全。

**备选方案及排除原因**：
- 备选 A：拦所有改动（含 M）→ 排除。收尾修文档、补 CHANGELOG 都是 M，会被全拦。
- 备选 B：只拦 `upstream/fstdd/**`，不拦测试 → 排除。「收尾补一堆测试」同样是范围膨胀，且测试文件也是交付物。

### 5. evidence 标签判据收为 `utils.has_fact_tag()` 单一事实源

**方案**：新增 `utils.has_fact_tag(text) -> bool`，匹配 `[F]` 或 `[F:来源]` 形态；
`gate approve` 调用它，缺标签时**默认拒绝**（D哥 裁决：强制）。

**为什么**：
- 形态判据只应有一处（EXP-2026-0026 / 本仓 v3.3.7 的 `_proposal_anchors.py` 都是这个范式）；
- 若散落在 `gate.py` 里内联正则，未来 `ci` 想复用时会写第二份 ⇒ 分叉；
- 默认强制而非 `--strict` 可选：Gate 是人工确认点，本来就该有据；给开关等于默认不设防。

**约束**：仅作用于 `gate approve`；`gate amend-audit`（补历史审计）不受约束 —— 那是事后追认，
不该要求当时的证据格式。

### 6. backlog 用单文件 `.fstdd/backlog.md`

**方案**（D哥 裁决）：全局一个文件，条目按 `[<change-id>]` 前缀归属来源；`fstdd new` **不**生成
per-change 的 `discoveries.md`。

**为什么**：
- per-change 的池子会随 change 归档散落进 `archive/`，下次没人会去翻 50 个归档目录找待办；
- 单文件让「还有多少债」一眼可见，也便于 grep 归属。

**格式**：
```markdown
## 未处理
- [ ] [2026-10-28-anti-drift-gates] 发现内容（发现于 BUILD）—— 建议处置

## 已处理
- [x] ...
```

### 7. 模板补 `scope:` 段是范围锁生效的前提

**方案**：`.fstdd/templates/canonical/proposal.yaml` 与 `upstream/.fstdd/templates/canonical/proposal.yaml`
**双份**增补：

```yaml
scope:
  mode: strict        # strict | advisory
  paths: []           # 本 change 允许改动的路径（目录以 / 结尾；其余按 fnmatch）
```

**为什么**：40+ change 全无声明的根因就是模板没这段。补模板比写一百遍「记得声明」有效。

**双份一致性**：本仓的模板双源（`.fstdd/` 与 `upstream/.fstdd/`）是既有约定，且
`tests/test_finance_content.py` 已有「双源逐字节一致」的断言范式（`test_L1_08` 等），沿用。

---

## Architecture

### 数据流

```
                         ┌─────────────────────────────┐
                         │ .fstdd.yaml                 │
                         │   baseline.base_git_sha ────┼──┐
                         │   current_phase ────────────┼─┐│
                         │   phases.build.status ──────┼─┼┤
                         └─────────────────────────────┘ ││
                                                          ││
  canonical/proposals/*.yaml                              ││
    scope.paths ──► _load_change_scope() ──┐              ││
                                            │              ││
                                            ▼              ▼▼
                                    ┌──────────────────────────────┐
  git diff --name-status            │  check_scope_creep   (b)     │
    baseline..HEAD ────────────────►│  check_deliver_freeze (n)    │
                                    │  check_claims         (o)    │
                                    └──────────────┬───────────────┘
                                                   │
                          ┌────────────────────────┼────────────────────────┐
                          ▼                        ▼                        ▼
                 ci check-failures         ci check-drift            gate approve
                 （聚合 18 项）            （三闸报告）              （evidence 标签）
```

### 模块改动

| 文件 | 改动 |
|---|---|
| `upstream/fstdd/cli/commands/ci.py` | 重写 `check_scope_creep`；新增 `check_deliver_freeze` / `check_claims` / `_iter_changed_files` / `_is_scope_too_broad`；新增 `cmd_check_drift` 子命令 |
| `upstream/fstdd/cli/utils.py` | 新增 `has_fact_tag(text)` |
| `upstream/fstdd/cli/commands/gate.py` | `approve` 增 evidence 校验（调用 `utils.has_fact_tag`） |
| `.fstdd/templates/canonical/proposal.yaml` | 增 `scope:` 段 |
| `upstream/.fstdd/templates/canonical/proposal.yaml` | 同上（双份一致） |
| `.fstdd/templates/backlog.md` + `upstream/.fstdd/templates/backlog.md` | 新增（双份一致） |
| `.fstdd/skills/build.md` + `upstream/.fstdd/skills/build.md` | 反漂移硬规则章节 |
| `.fstdd/skills/deliver.md` + `upstream/.fstdd/skills/deliver.md` | 同上 |

### 豁免白名单（集中定义，不散落）

范围锁的**允许路径**（即使不在 scope.paths 内也不算蔓延）：

```python
SCOPE_EXEMPT_PREFIXES = (
    ".fstdd/changes/",      # 本 change 产出物（proposal/spec/test-plan/report）
    ".fstdd/archive/",      # 归档产出物
    ".fstdd/experiences/",  # BUILD C5 要求更新既有经验条目
    ".fstdd/specs/",        # DELIVER 合并的全局 spec
    "docs/",                # 文档
)
SCOPE_EXEMPT_EXACT = {
    "README.md", "CHANGELOG.md", "NOTICE.md",
    ".fstdd/version.yaml", ".fstdd/config.d/project.yaml", ".fstdd/backlog.md",
}
```

---

## Risks / Trade-offs

| 风险 | 缓解措施 |
|---|---|
| **范围锁误报把正常改动判成蔓延** ⇒ 人开始习惯性忽略红灯（正是 (b) 现在的死法） | ① 未声明 scope 一律 WARN；② 上述豁免白名单覆盖所有正常产出物；③ 每条判据配反例测试，证明「真蔓延」能红、「正常改动」能绿 |
| **AI 把 scope.paths 写宽**（如 `upstream/`）让范围锁形同虚设 | `_is_scope_too_broad()` 检测：paths 命中 `upstream/`、`tests/`、`""`、`"."` 时 WARN 并提示收窄 |
| **scope.paths 自身含 `..`** 造成匹配歧义 | 读入时校验：含 `..` 的 pattern 直接剔除并 WARN（EXP-2026-0027 输入层拒绝原则） |
| **`baseline.base_git_sha` 缺失**（老 change 或手工建） | 缺失时降级为 WARN「无法确定 change 起点，范围锁跳过」，不 FAIL |
| **`git diff` 在浅克隆 / 无 git 环境下失败** | 捕获异常返回 SKIP，不崩 |
| **evidence 强制标签让 Gate 变啰嗦** | 错误提示直接给可复制示例；`amend-audit` 豁免 |
| **改 `check_scope_creep` 影响既有归档 change 的 ci 结果** | check 仅对活跃 change 生效，历史归档不回溯 |
| **双份模板 / skill 不一致** | 测试断言 `a.read_bytes() == b.read_bytes()`（沿用 `test_finance_content` 既有范式） |
| **DELIVER 冻结误伤「收尾补文档」** | 只拦 `--diff-filter=A` 的 `upstream/fstdd/**` + `upstream/tests/**`，`.fstdd/` 与 `docs/` 全豁免 |
