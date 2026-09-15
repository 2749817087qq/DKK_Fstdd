# FSTDD — WorkBuddy 适配层与金融扩展

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Upstream](https://img.shields.io/badge/upstream-leonai42%2Fstdd%20v3.0.5-lightgrey.svg)](https://github.com/leonai42/stdd)

> 上游 [leonai42/stdd](https://github.com/leonai42/stdd) V3.0.5（MIT）的衍生作品。
> 本仓库只放**我们自己的改动层**——不复制上游那 900 多个文件，也不包含任何无许可的第三方原文。
> 完整版权与来源说明见 [`NOTICE.md`](./NOTICE.md)。

---

## 1. FSTDD 是什么

**Spec 先行 + TDD 执行**：先定义行为规格（GIVEN/WHEN/THEN），再写测试，最后实现代码。
四阶段 + 三道强制用户确认门（Gate 1/2/3），把模糊需求变成有据可查、有测可验的交付。

| 阶段 | 做什么 | 产出 | 确认门 |
|------|--------|------|--------|
| **P1 UNDERSTAND** | 把模糊需求变成可验证的变更提案 | `proposal.yaml` / `proposal.md` | Gate 1 |
| **P2 SPEC** | 技术设计 + 行为规格 + 测试方案 | `design.md`、`specs/`、`test-plan.md` | Gate 2（最关键） |
| **P3 BUILD** | 切片 → 逐片 RED→GREEN→REFACTOR → 质量验证 | 实现代码、`test-report.md` | Gate 3 |
| **P4 DELIVER** | 归档、合并 specs、打 tag | `archive/`、git tag | — |

Gate 2 之后可选「全自动长程模式」：一次性预授权，P3 连续自动执行，只在 Gate 3 停下。

---

## 2. 本仓库提供什么

上游 STDD 功能完整，但**直接装到 WorkBuddy 上不好用**。本仓库解决的是这段距离：

| 问题 | 解决方式 |
|------|---------|
| 上游安装器输出到 `~/.workbuddy/skills/*.md`（单文件），而 WorkBuddy 实际加载 `~/.workbuddy-ai/skills/<name>/SKILL.md` | 改为目录格式 |
| skill 正文里的项目相对路径（`.fstdd/skills/_shared/*`、`python bin/fstdd`）全局安装后解析不了 | 安装时固化为绝对路径 |
| CLI 依赖 PyYAML / Jinja2，系统默认解释器可能没有 | 绑定到具备依赖的解释器 |
| Deliver 阶段会**自动向外部社区仓库上传项目经验**（数据外发） | 默认禁用 + 哨兵标记 + 校验脚本 |
| **升级会静默覆盖 skill，把上述策略全部抹掉** | 三层防护 + 升级后强制重跑规程 |
| 金融系统研发缺少领域约束 | 新增 `fstdd-fin` |

### 与上游的分工

| 内容 | 在哪 |
|------|------|
| 方法论、模板、CLI、`.fstdd/` 骨架 | `upstream/`（vendor 自上游，MIT 许可与版权原样保留） |
| 适配层脚本、安装文档、`fstdd-fin` 源 | 本仓库 `tools/` `docs/` `skills/` |
| 生成的 7 个 skill（`fstdd`、`fstdd-understand/spec/build/deliver/upgrade` + `fstdd-fin`） | **运行时生成物**，由安装脚本产生 |

> `fstdd-fin` 是本项目原创的金融增强层：源在仓库 `skills/fstdd-fin/`，
> 安装时随 6 个通用 skill **一起**装到 `~/.workbuddy-ai/skills/`——
> 它依赖通用层执行流程，**不单独分发**。第三方 `fintech-engineer` 为**可选**补充，未装不影响使用。

---

## 3. 目录结构

```
.
├── LICENSE                          # 本仓库原创内容的 MIT 许可
├── UPSTREAM-LICENSE.txt             # 上游 STDD 的 MIT 许可原文（合规保留）
├── NOTICE.md                        # 版权与来源声明（重要，对外分发前请读）
├── README.md
├── tools/
│   ├── install_workbuddy_skills.py  # 生成适配后的全局 skill + 施加安全策略
│   └── verify_workbuddy_skills.py   # 校验哨兵与路径适配是否仍在位
├── docs/
│   └── WORKBUDDY_INSTALL_NOTES.md   # 安装、适配、安全策略、实测验证记录
├── skills/
│   └── fstdd-fin/SKILL.md            # 金融系统版 FSTDD（原创重构）
└── upstream/                        # 上游 STDD V3.0.5 代码（vendor，MIT）
    ├── bin/fstdd                     # CLI 入口
    ├── fstdd/cli/                    # 39 个命令模块
    └── .fstdd/                       # 模板、配置、知识库骨架
```

---

## 4. 快速开始

### 前置要求

- Python **3.10+**，且已安装 `PyYAML` 与 `Jinja2`（上游 CLI 依赖）

  ```bash
  pip install pyyaml jinja2
  python -c "import yaml, jinja2; print('依赖 OK')"
  ```

- 已获取上游 STDD 源码

### 安装

```bash
# 只需克隆本仓库 —— 上游代码已 vendor 在 upstream/ 下，不必单独获取
git clone https://github.com/2749817087qq/Fstdd.git
cd Fstdd
```

**推荐：一键安装**（自动完成依赖检查 → 生成 skill → 校验三步）

```bash
./install.sh                # Linux / macOS / Git Bash
./install.sh --yes          # 非交互，自动补装缺失依赖
```

```powershell
.\install.ps1               # Windows
.\install.ps1 -Yes          # 非交互
```

若提示「禁止运行脚本」：`powershell -ExecutionPolicy Bypass -File .\install.ps1`

**或手动执行三步**：

```bash
python tools/install_workbuddy_skills.py   # 生成全局 skill
python tools/verify_workbuddy_skills.py    # 校验（输出 [PASS] 才算装好）
```

> 手动方式容易漏掉最后一步校验 —— 而缺依赖时安装脚本只会打 `[WARN]` 就继续，
> 生成的 skill 看起来正常，要等真正跑 CLI 时才失败。一键脚本就是为消除这个缺口。

### 路径说明

脚本的三个路径按以下顺序确定，一般**无需手工修改**：

| 路径 | 默认值 | 覆盖方式 |
|------|--------|---------|
| `SRC` 上游代码 | 脚本同级 `upstream/` | 环境变量 `FSTDD_SRC` |
| `OUT` skill 目录 | `~/.workbuddy-ai/skills` | 环境变量 `FSTDD_OUT` |
| `PY` 解释器 | 当前 `sys.executable` | 环境变量 `FSTDD_PY` |

若当前解释器缺 PyYAML / Jinja2，脚本会打印 `[WARN]` 并提示安装命令；
也可直接指定已装依赖的解释器：

```bash
FSTDD_PY=/path/to/python tools/install_workbuddy_skills.py
```

> 安装脚本是**幂等**的，重复运行不会叠加错乱，可放心重跑。

### 在项目里启用

进入你的项目根目录，初始化一次：

```bash
python "C:/路径/stdd/bin/fstdd" init
```

生成 `.fstdd/` 骨架、模板与项目状态文件。**未初始化的项目，流程无法完整执行。**

---

## 5. 日常使用

Skill 安装后需**重启 WorkBuddy 或执行 `/reload`** 才会出现在可用列表。之后在对话中直接说：

| 你想做的事 | 怎么说 |
|-----------|--------|
| 启动一个新变更 | 「用 FSTDD 做一个 XXX 功能」 |
| 需求理解 | 「fstdd-understand」 |
| 规格设计 | 「fstdd-spec」 |
| 切片与实现 | 「fstdd-build」 |
| 归档交付 | 「fstdd-deliver」 |
| 金融系统研发 | 「fstdd-fin」「用 FinFSTDD 做支付系统」 |

---

## 6. 安全策略

### 为什么要禁用经验上传

上游 `fstdd-deliver` 的 Step 2.8 会把项目沉淀的经验**自动上传到外部社区 Git 仓库**。
这属于数据外发，可能把项目信息带出去。本适配层将其**默认禁用**：
除非你本轮对话显式要求，一律跳过并输出「已按本机策略跳过」。

需要时手动执行：

```bash
python "C:/路径/stdd/bin/fstdd" experience share <EXP-ID>
```

### 三层防护（防止升级把策略抹掉）

升级、重装、手动覆盖 skill 文件，都会让策略**静默消失**。所以做了三层：

| 层 | 机制 | 失效时表现 |
|----|------|-----------|
| 1. 安装时插桩 | 按锚点在 Step 2.8 处插入禁用声明 | 锚点失效 → 打印 `[WARN]` 并走兜底，不静默 |
| 2. 兜底策略块 | 锚点不存在时整段前置到正文开头 | 保证哨兵必然存在 |
| 3. 写后 + 独立校验 | 安装后自检；`verify` 脚本可随时复检 | 缺失即 `[FAIL]` + 退出码 1 |

哨兵标记：`FSTDD_LOCAL_POLICY_NO_UPLOAD_V1`，`grep` 一下就知道防线还在不在。

### 升级后必做

```bash
python tools/install_workbuddy_skills.py
python tools/verify_workbuddy_skills.py   # FAIL 时禁止继续 DELIVER 相关操作
```

---

## 7. fstdd-fin：金融系统版

代号 **FinFSTDD**。把金融科技工程能力翻译成 FSTDD 流程里的**强制规格项与验收项**——
落在流程之外的知识，等于不会被执行的知识。

**P2 阶段强制新增的三份契约**（Gate 2 锁定，否则不许开工）：

1. **数据契约** — 每个数据项的来源、口径、时点、精度、**降级行为**
2. **口径定义表** — 收益率口径、复权方式、成本假设、状态机，全部写死
3. **合规与审计契约** — 审计字段、幂等约定、对账规则、数据合规、上报义务

**七条红线**（违反即 Gate 不通过）：金额用 Decimal、写操作幂等、审计不可篡改、
账实相符、**降级不静默**、数据合规、无硬编码凭据。

**八类金融特有失败模式**：重复扣款、账实不符、静默降级、精度丢失、审计缺口、
状态机漏洞、额度穿透、合规遗漏。其中**静默降级**最危险——系统看起来在正常出结果，
实际用的是过期数据。

测试维度在常规单测之外必含：幂等、对账、精度、时区/日历、降级、一致性、安全、审计、合规、恢复。

---

## 8. 故障排除

| 现象 | 原因与处理 |
|------|-----------|
| `ModuleNotFoundError: No module named 'yaml'` | 当前解释器缺 PyYAML。换装了依赖的解释器，或 `pip install pyyaml jinja2` |
| `verify` 报「残留未替换的 `python bin/fstdd`」 | skill 文件被上游原件覆盖了，重跑安装脚本 |
| `verify` 报哨兵缺失 | 同上，且说明上传防线已失效，**先修复再继续 DELIVER** |
| 提示 `.fstdd/templates/*` 不存在 | 项目未初始化，在项目根目录跑一次 `fstdd init` |
| `all registries unreachable` | 社区经验库网络不可达，非致命，不影响主流程 |
| 装完 skill 列表里看不到 | 重启 WorkBuddy 或执行 `/reload` |
| `git add` 刷出成百上千行 `LF will be replaced by CRLF` | 见下方「行尾符（EOL）治理」 |

### 行尾符（EOL）治理

仓库根 `.gitattributes` 声明了 `* text=auto eol=lf`：由 Git 自动判别文本/二进制，
文本文件统一以 LF 入库与检出。

**为什么需要它**：本机 Git 全局多为 `core.autocrlf=true`。批量新增文件（同步上游、
引入 vendor 依赖）时，Git 会对每个文本文件输出 `LF will be replaced by CRLF` 告警。
实测本仓库一次性 vendor 600+ 文件时，告警达 **637 行 / 约 95 KB**，足以把 `git commit`
的 stderr 完全淹没并导致进程被 SIGTERM 中断。

**规则不能写成 `* -text`**：`-text` 的语义是「关闭一切转换」，会把工作区的 CRLF
原样写入索引，使索引从 `i/lf` 翻转为 `i/crlf`（实测产生 494 行 diff），与「统一 LF」
的目标正好相反。正确写法是 `text=auto eol=lf`。

**批量 add 时的建议做法**：

```bash
# 一键自愈 + 校验（推荐）：先归一混合态文件，再跑 7 个用例
python tools/verify_eol.py --fix

# 只校验不自愈
python tools/verify_eol.py
```

脚本退出码非 0 表示有未通过的用例，输出中 `[FAIL]` 行会给出具体原因。
`--fix` 幂等，可重复执行。

**注意：这不是一次性问题**。FSTDD CLI（`init` / `new` / `canon generate` / `archive`）
生成的文件是 CRLF 行尾，每次执行后都会重新引入混合态。因此建议把
`verify_eol.py --fix` 作为跑完 CLI 之后的常规动作，或在提交前执行一次。

若需手工处理单个文件：

```bash
# 全库扫描，用数据确认影响面，而不是假定
git ls-files --eol | grep 'i/lf' | grep 'w/crlf'

# 对已入库文件，删掉后按规则重新检出（交给 Git 转换，不要手写脚本）
rm -f <文件> && git checkout -- <文件>
```

---

## 9. 经验回传

FSTDD 会把每个 change 中踩过的坑沉淀为「经验」。本仓库提供了一条**回传到本项目自己仓库**的链路。

### 为什么不用 `fstdd experience share`

上游的 `share` 目标仓库是**硬编码**的，且有两条路径：

| 路径 | 目标 | 问题 |
|---|---|---|
| 1 | `gh repo clone leonai42/stdd-experiences` 后直接 push | 需写权限，普通使用者必然失败 |
| 2 | `POST https://hzddyy.com/stdd/api/share-experience` | **第三方服务器**，属数据外发 |

两者都不是「回传到本项目自己的仓库」，因此本地安装策略会**跳过**该步骤。

### 本仓库的回传方式

```bash
python tools/share_experience.py --list                    # 查看可回传的经验
python tools/share_experience.py --export --from-archive   # 导出到 experiences/
python tools/share_experience.py --export --from-archive --publish   # 导出并推送
```

- **目标仓库**：`2749817087qq/Fstdd-experiences`（可用 `--repo` 或 `EXP_REPO` 覆盖）
- **经验来源**：`.fstdd/experiences/EXP-*.md`，以及已归档 change 的 `test-report.md`
- **强制脱敏**：导出前自动替换绝对路径、IP、内网域名、凭证、邮箱（`--no-sanitize` 可关闭，但不建议）

### 自动化

已配置定时任务「FSTDD 经验库自动同步」，每周一 09:00 自动导出并回传。任务在 GitHub
不通时会自动借 SSH 隧道出网（见第 8 节）。

### 其他人如何回传（自动，无需手动操作）

**一条命令即可，无需手工 fork 或提 PR**：

```bash
export GITHUB_TOKEN='你的 GitHub 令牌'      # 需 repo 权限
python tools/share_experience.py --export --from-archive --publish
```

脚本会**自动选择路径**，无需人工判断：

| 身份 | 行为 |
|---|---|
| 仓库所有者 / 协作者 | 直接推送到 `main` |
| 其他贡献者 | 自动 fork → 推送到自己的 fork → 自动创建 Pull Request |

关键点：

- 用的是**贡献者自己的 token**，本项目不持有也不需要任何人的凭证
- 外部提交以 **Pull Request** 形式进入，由维护者审核后合并
- 导出前**强制脱敏**，不含路径 / IP / 域名 / 凭证 / 邮箱

实现上采用「先尝试直推、权限不足再降级 fork+PR」，而非「先查身份」——
因为 `urllib` 不支持 socks5 代理，在需要隧道的环境下 API 调用会失败，而 git 支持代理。

> 这正是开源社区的经验蒸馏方式：全球使用者的踩坑记录汇聚到一处，
> 经审核后反哺给所有人。

---

## 10. 许可与来源

| 内容 | 许可 |
|------|------|
| 本仓库原创内容（脚本、文档、`fstdd-fin`） | **MIT**，见 [`LICENSE`](./LICENSE) |
| 上游 STDD V3.0.5 | **MIT**，版权归 杭州大道一以科技有限公司，见 [`UPSTREAM-LICENSE.txt`](./UPSTREAM-LICENSE.txt) |
| `fintech-engineer`（ClawHub，v1.0.3） | **无开源许可** — 本仓库**不含其原文**，仅参考领域分类视角并以原创形式重组，见 `NOTICE.md` |
| `wb-finance-skill`（WorkBuddy 内置） | 仅协作引用其取数规范，不含其内容 |

> 对外分发前请务必阅读 [`NOTICE.md`](./NOTICE.md)，其中列明了每一项第三方权利的来源与处理依据。
