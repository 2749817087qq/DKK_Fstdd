# STDD — WorkBuddy 适配层与金融扩展

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Upstream](https://img.shields.io/badge/upstream-leonai42%2Fstdd%20v3.0.5-lightgrey.svg)](https://github.com/leonai42/stdd)

> 上游 [leonai42/stdd](https://github.com/leonai42/stdd) V3.0.5（MIT）的衍生作品。
> 本仓库只放**我们自己的改动层**——不复制上游那 900 多个文件，也不包含任何无许可的第三方原文。
> 完整版权与来源说明见 [`NOTICE.md`](./NOTICE.md)。

---

## 1. STDD 是什么

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
| skill 正文里的项目相对路径（`.stdd/skills/_shared/*`、`python bin/stdd`）全局安装后解析不了 | 安装时固化为绝对路径 |
| CLI 依赖 PyYAML / Jinja2，系统默认解释器可能没有 | 绑定到具备依赖的解释器 |
| Deliver 阶段会**自动向外部社区仓库上传项目经验**（数据外发） | 默认禁用 + 哨兵标记 + 校验脚本 |
| **升级会静默覆盖 skill，把上述策略全部抹掉** | 三层防护 + 升级后强制重跑规程 |
| 金融系统研发缺少领域约束 | 新增 `stdd-fin` |

### 与上游的分工

| 内容 | 在哪 |
|------|------|
| 方法论、模板、CLI、`.stdd/` 骨架 | `upstream/`（vendor 自上游，MIT 许可与版权原样保留） |
| 适配层脚本、安装文档、`stdd-fin` | 本仓库 `tools/` `docs/` `skills/` |
| 生成的 6 个 skill（`stdd`、`stdd-understand/spec/build/deliver/upgrade`） | **运行时生成物**，由安装脚本产生 |

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
│   └── stdd-fin/SKILL.md            # 金融系统版 STDD（原创重构）
└── upstream/                        # 上游 STDD V3.0.5 代码（vendor，MIT）
    ├── bin/stdd                     # CLI 入口
    ├── stdd/cli/                    # 39 个命令模块
    └── .stdd/                       # 模板、配置、知识库骨架
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
git clone https://github.com/2749817087qq/DKKstdd.git
cd DKKstdd

# 生成全局 skill
python tools/install_workbuddy_skills.py

# 校验（输出 [PASS] 才算装好）
python tools/verify_workbuddy_skills.py
```

### 路径说明

脚本的三个路径按以下顺序确定，一般**无需手工修改**：

| 路径 | 默认值 | 覆盖方式 |
|------|--------|---------|
| `SRC` 上游代码 | 脚本同级 `upstream/` | 环境变量 `STDD_SRC` |
| `OUT` skill 目录 | `~/.workbuddy-ai/skills` | 环境变量 `STDD_OUT` |
| `PY` 解释器 | 当前 `sys.executable` | 环境变量 `STDD_PY` |

若当前解释器缺 PyYAML / Jinja2，脚本会打印 `[WARN]` 并提示安装命令；
也可直接指定已装依赖的解释器：

```bash
STDD_PY=/path/to/python tools/install_workbuddy_skills.py
```

> 安装脚本是**幂等**的，重复运行不会叠加错乱，可放心重跑。

### 在项目里启用

进入你的项目根目录，初始化一次：

```bash
python "C:/路径/stdd/bin/stdd" init
```

生成 `.stdd/` 骨架、模板与项目状态文件。**未初始化的项目，流程无法完整执行。**

---

## 5. 日常使用

Skill 安装后需**重启 WorkBuddy 或执行 `/reload`** 才会出现在可用列表。之后在对话中直接说：

| 你想做的事 | 怎么说 |
|-----------|--------|
| 启动一个新变更 | 「用 STDD 做一个 XXX 功能」 |
| 需求理解 | 「stdd-understand」 |
| 规格设计 | 「stdd-spec」 |
| 切片与实现 | 「stdd-build」 |
| 归档交付 | 「stdd-deliver」 |
| 金融系统研发 | 「stdd-fin」「用 FinSTDD 做支付系统」 |

---

## 6. 安全策略

### 为什么要禁用经验上传

上游 `stdd-deliver` 的 Step 2.8 会把项目沉淀的经验**自动上传到外部社区 Git 仓库**。
这属于数据外发，可能把项目信息带出去。本适配层将其**默认禁用**：
除非你本轮对话显式要求，一律跳过并输出「已按本机策略跳过」。

需要时手动执行：

```bash
python "C:/路径/stdd/bin/stdd" experience share <EXP-ID>
```

### 三层防护（防止升级把策略抹掉）

升级、重装、手动覆盖 skill 文件，都会让策略**静默消失**。所以做了三层：

| 层 | 机制 | 失效时表现 |
|----|------|-----------|
| 1. 安装时插桩 | 按锚点在 Step 2.8 处插入禁用声明 | 锚点失效 → 打印 `[WARN]` 并走兜底，不静默 |
| 2. 兜底策略块 | 锚点不存在时整段前置到正文开头 | 保证哨兵必然存在 |
| 3. 写后 + 独立校验 | 安装后自检；`verify` 脚本可随时复检 | 缺失即 `[FAIL]` + 退出码 1 |

哨兵标记：`STDD_LOCAL_POLICY_NO_UPLOAD_V1`，`grep` 一下就知道防线还在不在。

### 升级后必做

```bash
python tools/install_workbuddy_skills.py
python tools/verify_workbuddy_skills.py   # FAIL 时禁止继续 DELIVER 相关操作
```

---

## 7. stdd-fin：金融系统版

代号 **FinSTDD**。把金融科技工程能力翻译成 STDD 流程里的**强制规格项与验收项**——
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
| `verify` 报「残留未替换的 `python bin/stdd`」 | skill 文件被上游原件覆盖了，重跑安装脚本 |
| `verify` 报哨兵缺失 | 同上，且说明上传防线已失效，**先修复再继续 DELIVER** |
| 提示 `.stdd/templates/*` 不存在 | 项目未初始化，在项目根目录跑一次 `stdd init` |
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

**注意：这不是一次性问题**。STDD CLI（`init` / `new` / `canon generate` / `archive`）
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

## 9. 许可与来源

| 内容 | 许可 |
|------|------|
| 本仓库原创内容（脚本、文档、`stdd-fin`） | **MIT**，见 [`LICENSE`](./LICENSE) |
| 上游 STDD V3.0.5 | **MIT**，版权归 杭州大道一以科技有限公司，见 [`UPSTREAM-LICENSE.txt`](./UPSTREAM-LICENSE.txt) |
| `fintech-engineer`（ClawHub，v1.0.3） | **无开源许可** — 本仓库**不含其原文**，仅参考领域分类视角并以原创形式重组，见 `NOTICE.md` |
| `wb-finance-skill`（WorkBuddy 内置） | 仅协作引用其取数规范，不含其内容 |

> 对外分发前请务必阅读 [`NOTICE.md`](./NOTICE.md)，其中列明了每一项第三方权利的来源与处理依据。
