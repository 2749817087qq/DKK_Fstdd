# FSTDD 安装层去 WorkBuddy 硬编码：一套共享正文 + 每平台薄清单 + 参数化 installer - 技术设计

## Context

本仓库（`e:/FSTDD/stdd-repo`）是 FSTDD skill 的分发仓库，安装层目前**写死了 WorkBuddy**：

- `tools/install_workbuddy_skills.py` 没有 platform 参数，输出目录由 `tools/_skill_install_env.py`
  的 `resolve_skill_dir()` 按 WorkBuddy 内核判据（`WORKBUDDY_CONFIG_DIR || ~/.workbuddy`）解析，
  front-matter 用固定模板渲染（含 `version` / `trigger_keywords` / `stdd_version`）。
- `install.sh` / `install.ps1` 默认 `~/.workbuddy-ai/skills`，无平台参数。
- `tools/verify_workbuddy_skills.py` 只校验 WorkBuddy 安装点与 WorkBuddy front-matter 规则。

而上游 `upstream/.fstdd/platforms/` 已带 6 平台适配（aider / claude-code / copilot / cursor /
trae / workbuddy），各含 6 个 skill 文件；实测平台差异**仅在 front-matter**，正文逐字节相同：

- trae vs workbuddy：仅差 `version` / `trigger_keywords` 两行；
- claude-code vs workbuddy：仅差 3 行（description 带引号、无/有 `version`、无/有 `trigger_keywords`）。

技术栈：Python 3.13（PyYAML / Jinja2 / requests），POSIX shell（`install.sh`）与 PowerShell（`install.ps1`）。

约束：

- `proposal.md` 已定稿（`source_hash: 76a26617e3384428`），本设计不得改变其含义。
- 产物口径：一套共享 skill 正文 + 每平台薄清单（`platforms.yaml`）+ 参数化 installer
  （增 `--platform`，默认 `workbuddy` 且行为逐字节不变）。**禁止**产出 N 份手写适配分支。
- 铺平台顺序：Claude Code → Trae → Cursor →（Copilot / Aider 缓）；**Qoder 暂不做**。
- 上游已有的 `fstdd install <platform>` 分发口径与本仓库适配层相反（目标目录、单文件格式、
  旧名 `stdd-*`、缺少本地安全策略），**不委派**给它，只借鉴平台名与 front-matter 规则。

## Decisions

### 1. 采用平台薄清单（数据驱动），不采用 N 份手写适配分支

**方案**：新增 `platforms.yaml` 作为多平台适配的**唯一事实源**，每平台一条清单，声明：显示名、
skill 根目录解析规则、front-matter 规则（是否写 `version` / `trigger_keywords`、description 形态、
文件形态）。安装器读取清单渲染，平台差异全部数据驱动。

**为什么**：实测平台差异只在 front-matter，正文同源；把差异收敛为声明式清单，可避免正文随版本
漂移（多副本必然跑偏），并满足 success criteria「新增平台只改 platforms.yaml，不加代码分支」。

**备选方案及排除原因**：
- 备选 A：为每个平台生成一份完整手写 skill 目录（复制正文 + 手改 front-matter）。排除：
  正文出现 N 份副本，随上游/本仓库改版必然漂移，且违反 proposal「禁止产出 N 份手写适配分支」。
- 备选 B：直接复用上游 `fstdd install <platform>`。排除：实测其 workbuddy 目标目录为
  `~/.workbuddy/skills`（正是本仓库安装层修掉的错路径，复用即回归「装 10 天全无效」事故）；
  claude-code 落到**项目内** `.claude/skills` 而非用户级；输出为单文件 `stdd-*.md`（非本仓库
  `<name>/SKILL.md` 目录格式）；且不含本仓库本地安全策略（静默回传哨兵）。仅借鉴其平台名与
  front-matter 规则。

### 2. front-matter 差异全部来源于清单规则，正文只做一次适配替换

**方案**：安装器先对**共享正文**做一次既有的适配替换（`_shared` 绝对路径、CLI 入口、解释器绑定、
deliver/upgrade 本地安全策略），再按清单的 front-matter 规则渲染头。workbuddy 的 front-matter
规则即「现状模板」，其它平台由清单关闭/改写相应字段。

**为什么**：正文与 front-matter 是两个正交关注点；剥离后，正文永远单一来源，平台差异只落在
声明层，逐字节回归（workbuddy）也只在「正文+现状头」这一条路径上被复用，天然可保一致。

**备选方案及排除原因**：
- 备选 A：正文内嵌平台条件（Jinja2 `{% if platform %}`）。排除：把平台逻辑重新写进模板，
  等价于隐藏的多分支，且会让正文随平台分化，违背「一套正文」。
- 备选 B：对每个平台各存一份 front-matter 模板文件。排除：模板文件会散落、与清单重复定义同一事实
  （历史事故根因即「同一事实出现在两处」）。

### 3. skill 根目录解析遵循「平台内核同源 + 显式覆盖优先」，不写死任一路径

**方案**：把 `_skill_install_env.resolve_skill_dir()` 泛化为「平台感知解析」：先看显式覆盖
（`FSTDD_OUT`），再按平台内核环境变量解析，最后按平台惯例兜底；解析规则本身写进 `platforms.yaml`。
workbuddy 分支保持既有顺序（`WORKBUDDY_CONFIG_DIR`/`CODEBUDDY_CONFIG_DIR` → `~/.workbuddy-ai` →
`~/.workbuddy`），claude-code 为 `~/.claude/skills`，trae 同构 workbuddy。

**为什么**：写死任何一侧都是同一错误的重演（`.workbuddy` 是内核兜底、`.workbuddy-ai` 是启动器覆盖）；
跟随内核解析顺序才是稳定解。解析规则集中到清单后，安装器/校验器/体检脚本共用同一事实源。

**备选方案及排除原因**：
- 备选 A：把每个平台的解析逻辑继续写成代码 if/else。排除：违反「无平台分支代码」，且新增平台需改代码。
- 备选 B：只支持显式 `--out`，不做平台默认解析。排除：破坏「一键安装」体验，且 workbuddy 既有默认
  行为会改变，违反逐字节回归。

### 4. 默认值兼容策略：缺省即 workbuddy，且行为逐字节不变

**方案**：`--platform` 默认值为 `workbuddy`；不传该参数与显式 `--platform workbuddy` 走**完全相同**
的渲染路径与输出目录解析，产出与变更前基准逐字节一致。默认值在清单/参数声明中集中定义。

**为什么**：现有用户的安装入口（`install.sh` / `install.ps1` 无参调用）必须零感知升级；逐字节一致
是本变更唯一的强回归保护（success criteria[0]）。

**备选方案及排除原因**：
- 备选 A：缺省时要求用户先选平台（无默认）。排除：破坏既有入口的兼容性，属破坏性变更。
- 备选 B：缺省改为 claude-code。排除：改变既有用户行为，且 workbuddy 是本机当前部署平台。

### 5. 铺平台顺序与 Qoder 排除

**方案**：按 Claude Code → Trae → Cursor →（Copilot / Aider 缓）铺开；先期以 claude-code 与 trae
端到端实测。**Qoder 暂不做**。

**为什么**：claude-code 上游 6 文件已齐、路径标准；trae 与 workbuddy 同构且本机装有 Trae，可端到端
自验；cursor 规则形态（`rules/*.md`）与 skill 目录不同，需单独清单化，排在第三。Qoder 上游零适配、
装载约定未知、本机未安装，盲写等于产出不可验证的伪适配。

**备选方案及排除原因**：
- 备选 A：一次性铺齐 6 平台（含 Qoder）。排除：Qoder 无可验证落点，会引入不可验证的伪适配；
  copilot/aider 形态差异大，缓做以缩小首轮验证面。

## Architecture

数据流（清单 → 安装器 → 目标平台 skill 根）：

```text
                 platforms.yaml （唯一事实源）
                 ┌──────────────────────────────────────────────┐
                 │ platform:                                   │
                 │   display_name / skills_root 解析规则        │
                 │   frontmatter: {version?, trigger_keywords?, │
                 │                 description_style, file_kind}│
                 └───────────────────────┬──────────────────────┘
                                         │ 读取
                                         v
   共享正文源（upstream/.fstdd/skills/*.md）──┐
                                         │   │ 一次适配替换（_shared 绝对路径 / CLI 入口 /
                                         │   │ 解释器绑定 / deliver·upgrade 本地安全策略）
                                         v   v
                     tools/install_workbuddy_skills.py --platform <p>
                     （默认 workbuddy；无平台分支，差异全由清单驱动）
                                         │
                                         v
                 _skill_install_env.resolve_skill_dir(platform) ── 内核同源路径解析
                                         │
                                         v
                 目标平台 skill 根：<resolved>/<name>/SKILL.md
                 （workbuddy:~/.workbuddy-ai/skills；claude-code:~/.claude/skills）

   入口透传：install.sh --platform <p>   /   install.ps1 -Platform <p>
                     └──────────────► 安装器 + 校验器（同一 <p>）

   校验：tools/verify_workbuddy_skills.py [--platform <p>]（默认 workbuddy）
         └── 按平台校验安装点与 front-matter 规则，判据与安装器共用 platforms.yaml
```

组件职责：

| 组件 | 位置 | 职责 |
|------|------|------|
| 平台薄清单 | `platforms.yaml` | 声明每平台显示名、skill 根解析规则、front-matter 规则（唯一事实源） |
| 路径解析器 | `tools/_skill_install_env.py` | 按平台 + 内核同源顺序解析 skill 根目录 |
| 参数化安装器 | `tools/install_workbuddy_skills.py` | `--platform`（默认 workbuddy）；渲染 front-matter 与输出目录 |
| 平台感知校验器 | `tools/verify_workbuddy_skills.py` | `--platform`（默认 workbuddy）；校验目标平台落点与规则 |
| 入口脚本 | `install.sh` / `install.ps1` | 透传平台选择；串起「装依赖 → 安装 → 校验」 |

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 参数化改动破坏 workbuddy 既有产出（回归） | 变更前保存逐字节基准快照；`--platform workbuddy`（含缺省）比对哈希/`Compare-Object`；作为 P0 回归 |
| 平台薄清单与代码各写一份解析规则（历史事故重演：同一事实两处） | 解析规则只写进 `platforms.yaml`，安装器/校验器共用同一读取入口；用例断言二者结果一致 |
| claude-code front-matter 规则理解偏差（引号/字段取舍） | 以上游 `upstream/.fstdd/platforms/claude-code/skills/*.md` 实测差异为基准；用例断言无 `version`/`trigger_keywords` 且 description 引号形态 |
| 未知平台被静默回退，装到错误目录 | 未声明平台一律非零退出并列出可用平台；用例覆盖 `--platform qoder` 拒绝路径 |
| Trae 与 workbuddy 同构但环境变量/路径不同 | 用清单声明 trae 规则；本机装有 Trae，做端到端实测（success criteria[4]） |
| 平台分支代码悄悄回流 | 代码审查 + 用例断言「源码无平台 if/else」；平台差异全部数据驱动 |
| 本地安全策略（静默回传哨兵）只在 workbuddy 路径施加而漏到其它平台 | 策略施加步骤置于「共享正文适配」阶段，早于平台 front-matter 渲染；用例断言各平台正文均含哨兵 |
| Qoder 盲写伪适配 | 明确排除 Qoder；未验证落点前不产清单 |