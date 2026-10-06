# 上游基线对齐：固化基线快照 / 消除版本口径漂移 / 经验库对标 — 技术设计

> change: `2026-10-05-upstream-baseline-alignment` ｜ mode: standard ｜ task_type: documentation
> 上游依赖：无（不升级上游；不引入新依赖）

## Context

### 当前系统状态

本仓库自我定位为「上游 `leonai42/stdd`（MIT）的 WorkBuddy 适配层与金融扩展」。仓库里同时存在
**三个不同对象的版本号**，而对外声明把它们混为一谈：

| 轴 | 含义 | 机器可读事实源（实测值） |
|----|------|--------------------------|
| **R — 发行版** | 本仓 FSTDD 的发布版本 | `.fstdd/config.d/project.yaml: stdd_version` = `3.3.4`；`.fstdd/version.yaml: fstdd_version` = `3.3.4` |
| **K — vendored 内核** | `upstream/` 目录（上游代码 + 本仓衍生改动）的实际版本 | `.fstdd/version.yaml: upstream_version` = `3.1.0`；`upstream/pyproject.toml: version` = `3.1.0`；`upstream/CHANGELOG.md` 有 V3.1.0（2026-09-26） |
| **E — 外部上游发布** | 上游项目 `leonai42/stdd` 的最新发布（外部锚点，非本仓产物） | tag `v3.0.5`；master HEAD `b9a4af62b5f4fd2747884c0a61febbc341792ac2`；pushed_at `2026-08-17T15:25:43Z`；Releases 空 |

关键事实：**K（3.1.0）≠ E（v3.0.5）**。`upstream/` 不是逐字节冻结的上游快照，它被本仓按 change
流程持续修改并**在本仓内单独编版本**，因此内核版本**领先**于上游最新发布。任何把 K 写成 E 的
声明都是错的。

### 现行漂移点（实测，行号为准）

| 位置 | 现状 | 问题 |
|------|------|------|
| `NOTICE.md:33` | 「故上游版本号见 `upstream/pyproject.toml`（`3.0.5`）」 | 直读该文件得 `3.1.0`；且把 K 称作「上游版本号」——同节内与 `NOTICE.md:15`（E 轴 V3.0.5）互相打架 |
| `NOTICE.md:15` | 表格「版本 \| V3.0.5（master 分支）」 | 描述 E 轴本身正确，但未标明轴，与 :33 混读即矛盾 |
| `README.md:5` | 徽章 `upstream-leonai42/stdd v3.0.5` | E 轴数字未标轴，易被读成「本仓/内核 = 3.0.5」 |
| `skills/fstdd-fin/SKILL.md:10` | `stdd_version: "3.0.5-fin.2"` | `stdd_version` 语义 = 内核轴 K，写成了 E |
| `skills/fstdd-fin/SKILL.md:17` | sources「方法论基底: FSTDD V3.0.5 (MIT)」 | 方法论基底实为内核 K |
| `docs/WORKBUDDY_INSTALL_NOTES.md:5` | 「来源仓库 …（master 分支，V3.0.5，MIT License）」 | 未标轴的 E 数字 |
| `docs/WORKBUDDY_INSTALL_NOTES.md:89` | 「Gate 3，V3.0.5 三阶段合一」 | 指称的是内核/方法学形态，非 E |
| `tools/install_workbuddy_skills.py:2` | docstring「把 FSTDD (leonai42/stdd V3.0.5) 的 skill 层安装为…」 | 未标轴的 E 数字 |
| `tools/install_workbuddy_skills.py:304-305` | `version: "3.0.5"` / `stdd_version: "3.0.5"` **硬编码** | 生成 skill 同带两个错号；同脚本 `:80` 已可读到 `REPO_VERSION`（=3.3.4） |
| `tools/install_workbuddy_skills.py:377` | 来源横幅「…FSTDD (Spec+Test Driven Development) V3.0.5…」 | 写死 E；skill 正文实际来自内核 K |

### 约束条件

- **MIT 署名忠于事实**：`upstream/` 内描述**上游自身**为 V3.0.5 的上游自有文档
  （`upstream/README.md`、`upstream/README_EN.md`、`upstream/FSTDD.md`、`upstream/EXTENDING.md`、
  `upstream/V3.0_SLIM_PLAN.md`、`upstream/WORKBUDDY_INSTALL_NOTES.md`）**保持原样**，不属于本次漂移。
- **禁改区**：`.fstdd/archive/**`、`skills-archive/**`、`_scratch/**`、`artifacts/**`、`.fstdd/_notices/**`
  （历史证据 / 非发布物）。
- **网络**：本机不可直连 `github.com:443`；一切上游查询须经服务器 `ssh fstdd-hub`
  （见 `docs/DISTRIBUTED_ACCESS.md`）。
- **既有门禁不得动摇**：四自检（`verify_rename` / `verify_eol` / `verify_skill_standards` /
  `verify_workbuddy_skills`）+ 全量 `pytest upstream/tests` 须保持全绿。特别地
  `verify_rename.ALLOWED_OLD_MENTIONS` 含 `"STDD V3.0.5"`，其判定语义不得被本次改动破坏。

### 技术栈

Python 3.10+（本机解释器 3.13.14，含 PyYAML / Jinja2 / requests）；文档为 Markdown；
规范为 YAML-first（`canonical/` → `canon generate` 渲染 Human View）。

---

## Decisions

### 1. 版本口径三轴显式化（E / K / R）

**方案**：把仓库内所有「版本」表述按**对象**而非按数字拆成三轴，并在每个声明面标明轴：

- **R（发行版轴）**：本仓 FSTDD 发布号，源 = `.fstdd/config.d/project.yaml: stdd_version`
  / `.fstdd/version.yaml: fstdd_version`（当前 `3.3.4`）。随本仓 release 漂移。
- **K（vendored 内核轴）**：`upstream/` 内核版本，源 = `.fstdd/version.yaml: upstream_version`
  / `upstream/pyproject.toml: version`（当前 `3.1.0`）。随内核改动漂移，**不随本仓 release 漂移**。
- **E（外部上游锚）**：上游项目最新发布（当前 `v3.0.5`，附 tag / HEAD sha / pushed_at）。
  **只是对标锚，永不冒充 K 或 R**。

落点规则（BUILD 据此逐处判定）：
- 指称 `upstream/` 内核或其产物（skill 正文、模板、CLI）的版本 → **K**；
- 指称上游外部项目本身的最新发布 → **E**，须标注为「上游最新发布」并连到基线快照；
- 指称本仓发布 → **R**。

**为什么**：漂移的根因不是「数字抄错了」，而是「同一节里同时谈两个对象却只用一个数字」。
只改数字（3.0.5 → 3.1.0）会在下一次 release 或下一次内核改动时立刻复发；标注轴才能让
「哪个对象、哪个号」自证。

**备选方案及排除原因**：
- 备选 A：把 K 也归一为 E（即宣称内核 = 3.0.5）→ 与 `upstream/pyproject.toml` 事实冲突，
  且抹掉本仓对内核的衍生改动记录（`upstream/CHANGELOG.md` 有 V3.1.0 条目），排除。
- 备选 B：全仓把 「3.0.5」替换为 「3.1.0」→ 会误改 `upstream/` 内描述上游自身的文档，
  破坏 MIT 署名忠于事实，且触发 `verify_rename` 报警，排除。
- 备选 C：只修 `NOTICE.md:33` 一处 → 其余声明面继续各说各话，不满足「活体声明面零矛盾」，排除。

### 2. 基线快照单一事实源：新增 `docs/UPSTREAM_BASELINE.md`

**方案**：新增 `docs/UPSTREAM_BASELINE.md`，作为**上游基线快照证据的唯一出处**，固化：

1. 观测时点（`observed_at`，带时区）+ 观测时本仓 base git sha；
2. E 轴全套证据：tag `v3.0.5` / HEAD `b9a4af62…` / pushed_at `2026-08-17T15:25:43Z` / Releases 空 /
   仅 master 分支 / 未归档；
3. 通道排除结论：Gitee 404；PyPI `stdd` 为同名无关包（LiiraGH 的 PyQt6 模板）、`fstdd` 404；
4. **本仓领先量清单**（K 与 R 相对 E 的增量，供对标直接引用）；
5. 上游经验库对标格子（见决策 4）。

**为什么**：漂移的第二个来源是「数字散落多处、各自维护」。把**易变的快照证据**
（sha / pushed_at / Releases）收敛到单一文件后，其余声明面只**链接**、不复制，未来再改
只需改一处。

**备选方案及排除原因**：
- 备选 A：把快照写进 `NOTICE.md` → NOTICE 是合规声明，混入易变的探针结果会再制造双源，排除。
- 备选 B：只留 `.fstdd/canonical/` 内的机器记录、不写人类可读文档 → 外部读者（协作节点）无法引用，排除。

### 3. 适配层去硬编码：版本字段与横幅由机器可读源派生

**方案**：`tools/install_workbuddy_skills.py` 内：

- 新增一个**本文件内**的最小读取函数（如 `_vendored_kernel_version()`），从
  `.fstdd/version.yaml: upstream_version` 读 K（读不到回落 `unknown`）；
- `_build_frontmatter()`：`version:` → `REPO_VERSION`（R，脚本 `:80` 已具备）；
  `stdd_version:` → K；
- 来源横幅（`:377`）与 module docstring（`:2`）不再写死 E 数字，改为引用 K（skill 正文的真实来源）。

**为什么**：同一脚本已经能读到 `REPO_VERSION`，却把两个版本字段写死为 `3.0.5` —— 属于
纯本地欠账（上游 `fstdd install` 本身就是从项目配置派生 `stdd_version`，见
`upstream/tests/commands/test_install.py::test_install_frontmatter_has_stdd_version`）。
派生后生成 skill 的两个字段各自指向正确的轴，且随源自动更新，不再需要人肉同步。

**约束**：`stdd_version` 必须是纯 `[\d.]+` 形态（既有测试与 `_skill_install_env.frontmatter_version`
的读取口径），故 K 取裸版本号 `3.1.0`，不追加 `-fin.N` 之类的限定后缀。

**备选方案及排除原因**：
- 备选 A：保持硬编码、只加注释提醒 → 注释不会被执行，漂移必复发，排除。
- 备选 B：`version` 与 `stdd_version` 都取 R（3.3.4）→ 丢失内核轴，生成 skill 无法再表达
  「基于哪个内核」，且与 `stdd_version` 的既有语义冲突，排除。
- 备选 C：把读取函数放进 `tools/_skill_install_env.py` → 会扩大代码面到第二个文件；
  本文件只有单一消费者，YAGNI，暂不外提（如需复用再另立 change）。

### 4. 上游经验库对标 = 只读核对，不接入回传链路

**方案**：`docs/UPSTREAM_BASELINE.md` 记录 `leonai42/stdd-experiences` 的**只读**对标结论：
我方回传目标是 `2749817087qq/Fstdd-experiences`（`tools/share_experience.py: DEFAULT_EXP_REPO`），
故 `leonai42/stdd-experiences` **不是我方回传目标**；同时给出「其清单中是否含我方 node 前缀条目
（如 `FSTDD003-EXP-*`）」的**只读核对实测值** + 可借鉴增量。

**为什么**：唯一仍在活跃推送的上游资产就是这个经验库（pushed_at 2026-10-05T00:31:25Z），
对标必须覆盖它，否则「基线对标」不完整；但它包含**外部数据**，只读核对即可，不修改、
不外发、不接入回传实现。

**备选方案及排除原因**：
- 备选 A：把 leonai42/stdd-experiences 设为我方回传目标 → 改动回传链路行为与目标，
  超出本 change 范围（且属数据外发方向的实质变更），排除。
- 备选 B：不做经验库对标 → 遗漏唯一活跃上游资产，不满足 proposal 的对标范围，排除。

### 5. 改动边界：只动活体声明面

**方案**：仅改「活的」声明面 —— `NOTICE.md`、`README.md`、`skills/fstdd-fin/SKILL.md`、
`docs/WORKBUDDY_INSTALL_NOTES.md`、`tools/install_workbuddy_skills.py`（+ 新增 `docs/UPSTREAM_BASELINE.md`）。
`upstream/` 内上游自有文档、`.fstdd/archive/**`、`skills-archive/**`、`_scratch/**`、`artifacts/**`
一律不动。

**为什么**：上游自有文档里的 V3.0.5 是**关于上游自身的事实**（MIT 署名须忠于事实）；
历史归档是冻结证据，改写即篡改历史。

**备选方案及排除原因**：
- 备选 A：全仓统一替换 → 见决策 1 备选 B，排除。
- 备选 B：连归档一起改（求「全仓一致」）→ 破坏历史证据链与门禁，排除。

### Anchoring 评估（Step 4.5）

proposal 的 `critical.is_critical = false`，`risk_assessment` 三项（safety_critical / financial /
cross_system）均为 `false` ⇒ **Step 4.5 锚定评估不触发**，维持 proposal 既定的 `anchoring.level = L1`
（无需参考实现锚）。本 change 无安全关键 / 金融 / 跨系统风险面。

---

## Architecture

### 版本数据的流向（单一事实源 → 派生 → 声明面）

```
机器可读事实源（唯一权威）
  .fstdd/config.d/project.yaml : stdd_version ─┐
  .fstdd/version.yaml          : fstdd_version ─┴─► R 发行版轴  3.3.4
  .fstdd/version.yaml          : upstream_version ─┐
  upstream/pyproject.toml      : version          ─┴─► K 内核轴    3.1.0
  docs/UPSTREAM_BASELINE.md（快照证据唯一出处）  ────► E 外部锚    v3.0.5 + sha/pushed_at
                                                          ▲
                                     （只链接，不复制数字） │
  ┌───────────────────────────────────────────────────────┘
  │  活体声明面
  ├─ NOTICE.md §1 ────────────── 标明 E 轴 + 内核轴注记指向 K，链接快照
  ├─ README.md 徽章 / 引言 ────── E 轴徽章 + K 轴徽章（两轴并列）
  ├─ skills/fstdd-fin/SKILL.md ── stdd_version = K；sources 方法论基底 = K（附 E 溯源）
  └─ docs/WORKBUDDY_INSTALL_NOTES.md ── 版本表述按轴标注

        │ 派生（读机器可读源，不写死）
        ▼
  tools/install_workbuddy_skills.py
        ├─ frontmatter version:      ← REPO_VERSION (R)
        ├─ frontmatter stdd_version: ← _vendored_kernel_version() (K)
        ├─ 来源横幅 / docstring:      ← K
        └─ 生成戳 stamp_line(REPO_VERSION)  ← R（既有，不改）
        ▼
  ~/.workbuddy-ai/skills/<name>/SKILL.md（运行时生成物）
```

### 校验链（本次改动须全部保持/达到绿）

```
tools/verify_rename.py            8/8   （排除区语义不变；ALLOWED_OLD_MENTIONS 不变）
tools/verify_eol.py               7/7
tools/verify_skill_standards.py   7/7   （只认 version 字段，不受 stdd_version 改动影响）
tools/verify_workbuddy_skills.py  PASS  （生成戳 = REPO_VERSION；哨兵/路径适配在位）
pytest upstream/tests             0 failed
```

---

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 误把 `upstream/` 内描述上游自身的 V3.0.5 当漂移一起改 → 破坏 MIT 署名、触发 `verify_rename` 报警 | 逐处先判「对象是上游项目本身 vs 本仓 vendored 内核」；改动前后各跑一次 `verify_rename` 定向核对 8/8 |
| 只改一处、留下新的自相矛盾 | 成功标准要求「活体声明面零矛盾」，并**以定向扫描断言**核验（而非人眼） |
| 改 `install_workbuddy_skills.py` 影响生成物/校验器 | `version` 取 R、`stdd_version` 取纯 `[\d.]+` 的 K，保持 `verify_workbuddy_skills` 判据（生成戳、哨兵、路径）不变；改后重跑 install + verify |
| `docs/UPSTREAM_BASELINE.md` 与 `NOTICE.md` 重复维护快照数字 → 未来再漂移 | 快照数字（sha/pushed_at/Releases）只写在 `UPSTREAM_BASELINE.md`；`NOTICE`/`README` 只链接不复制 |
| 经验库对标需联网（本机断网） | 经 `ssh fstdd-hub` 只读查询；只读、不外发、不写上游仓库 |
| 既有 906 项回归被本次文档/脚本改动波及 | 全量 `pytest upstream/tests` 0 failed 作为 Gate 3 硬条件；`test_install_source` / `test_fstdd_matrix` / `test_cross_cutting_verification` 等引用安装脚本的用例纳入回归矩阵 |
| `verify_rename` 的 `ALLOWED_OLD_MENTIONS` 中 `"STDD V3.0.5"` 条目因本改动失去匹配 → 判定语义变化 | 明确不改 `verify_rename.py`；上游自有文档保持原样，白名单条目语义不变；改后定向跑 8/8 |

---

## 关联

- proposal：`canonical/proposals/2026-10-05-upstream-baseline-alignment.yaml`
- 行为规格：`canonical/specs/code/version-nomenclature.yaml`、`canonical/specs/code/upstream-baseline-alignment.yaml`
- 验证规格：`canonical/specs/agent/2026-10-05-upstream-baseline-alignment.yaml`
- 测试方案：`test-plan.md`