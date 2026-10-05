# FSTDD 全局安装说明（WorkBuddy）

安装时间：2026-09-14
最近修订：2026-09-29（**路径口径定稿：法定源 = 工作区内 `stdd-repo`，本机实际工作区 = `E:/FSTDD`**）
来源仓库：https://github.com/leonai42/stdd （上游项目 master 分支，上游最新发布 V3.0.5，MIT License）
许可：MIT（详见仓库 LICENSE）

## 0. 位置与权威关系（2026-09-29 路径口径定稿）

```
   E:/FSTDD/                  ← **工作区**（本机实际位置；全部 FSTDD 资产集中于此）
   ┌───────────────────────────────────────────────────────┐
   │  stdd-repo/   ← **法定源**（唯一权威；git 仓库；          │
   │                 完整历史 + tag fstdd-v1.0.0）            │
   │      │  安装器从这里读；skill 内固化路径指向它            │
   │      └── push origin ──> GitHub DKK_Fstdd（**上传目标**） │
   │                                                       │
   │  backups/       ← 归档与备份（含本地裸库 stdd-repo.git）  │
   │  .workbuddy-ai/ ← 记忆 / 临时 / .gh_token（GitHub 凭证） │
   └───────────────────────────────────────────────────────┘
```

| 位置 | 角色 |
|---|---|
| **`E:/FSTDD/stdd-repo/`** | **法定源**（唯一权威）。安装器从这里读；skill 内固化路径指向它 |
| `2749817087qq/DKK_Fstdd`（GitHub） | **上传目标**（不是源）。由法定源 `git push origin master --tags` 上传 |
| `~/.workbuddy-ai/Fstdd` | ⚠️ 更早一轮的归档副本，**不是法定源** |
| `D:/Programs/DKK_Fstdd` | ⚠️ **另一程序的调试副本，不要动**，不是我们的安装源 |
| `D:/tools/FSTDD/` | ❌ 变更 `2026-09-17-migrate-to-d-drive` 的**目标位置，本机从未落地**（实测 `D:\tools` 不存在）。**不要**再把文档 / 脚本 / 测试指向它 |

> **路径口径（定稿）**：法定源 = **工作区内的 `stdd-repo`**（canonical spec
> `canonical-in-workspace` SC-001 / SC-009）。工作区在本机实际为 `E:/FSTDD`，
> 故法定源 = `E:/FSTDD/stdd-repo`。
>
> 历史文档曾写 `D:/tools/FSTDD/stdd-repo` —— 那是 `d-drive-home` 变更的迁移目标，
> 但该迁移**未执行**：实测 `Test-Path D:\tools` = False，而仓库就在 `E:\FSTDD\stdd-repo`。
> 文档、脚本、测试一律以**实际工作区**为准；脚本内的路径解析一律由 `__file__` 自定位，
> **不写死盘符**（换机即失效的硬编码是本文件 2026-09-29 修复的对象）。

### 同步操作

```bash
# 工作区 → 服务器裸库（真值源）
cd E:/FSTDD/stdd-repo && git push server master --tags

# 工作区 → 本地裸库（备份）
cd E:/FSTDD/stdd-repo && git push local master --tags
```

> **为什么用 git 而不是手工 cp**：2026-09-16 一天内发生两次漂移（宪法陈旧、verify 脚本两份不一致），
> 根因都是「两份拷贝靠手工 cp」。git 有 hash、有冲突检测，漂移无法静默发生。

> 📌 GitHub（`DKK_Fstdd`）仍是**上传目标**，但当前受「全域禁推」执行中约束 ——
> 未经总工裁定不得向 GitHub 推送。

## 1. 安装位置

| 内容 | 路径 |
|------|------|
| FSTDD 源码 / CLI / 静态资源骨架（**法定源**） | `E:/FSTDD/stdd-repo/upstream` |
| 全局 skill（WorkBuddy 用户级） | `<本实例 home>/skills/fstdd*` —— 本机 = `C:\Users\Administrator\.workbuddy-ai\skills\fstdd*` |
| 重装脚本 | `E:/FSTDD/stdd-repo/tools/install_workbuddy_skills.py` |
| 校验脚本（升级后必跑） | `E:/FSTDD/stdd-repo/tools/verify_workbuddy_skills.py` |
| Python 解释器（已具备 PyYAML + Jinja2） | `C:\Users\Administrator\.workbuddy-ai\binaries\python\envs\default\Scripts\python.exe` |

> ⚠️ **全局 skill 目录 = 本实例 home 下的 `skills/`**，不是写死的固定路径。
> 判据来自内核 `cli/dist/codebuddy.js`：
>
> ```js
> function getWorkbuddyConfigDir(){
>   let eA = process.env.WORKBUDDY_CONFIG_DIR?.trim();
>   return eA || eM.join(ek.homedir(), ".workbuddy")
> }
> ```
>
> `~/.workbuddy` 只是**兜底值**；桌面应用启动时会把 `WORKBUDDY_CONFIG_DIR`
> 设为本实例 home。本机该变量 = `C:\Users\Administrator\.workbuddy-ai`，
> 故本实例实际加载 **`~/.workbuddy-ai/skills`**（三层实测见 §6.4）。
>
> 📌 安装脚本与校验脚本**共用** `tools/_skill_install_env.py` 中的同一个解析器 ——
> **同一事实只允许有一处定义**。历史事故：两者各自写死 `~/.workbuddy/skills`
> 并互相以「与对方保持一致」背书，于是一起错、一起绿，装了 10 天无人察觉（见 §6.4）。

已安装的全局 skill（**7 个**）：

- `fstdd` — 总入口：判断项目是否已初始化、路由阶段、说明 CLI 位置
- `fstdd-understand` — Phase 1 需求理解与确认（Gate 1）
- `fstdd-spec` — Phase 2 规格设计与测试方案（Gate 2）
- `fstdd-build` — Phase 3 切片规划 + TDD 实现 + 质量验证（Gate 3，三阶段合一）
- `fstdd-deliver` — Phase 4 归档交付（含静默回传）
- `fstdd-upgrade` — 版本同步与升级
- `fstdd-fin` — 金融领域特化层（依赖上面 5 个阶段 skill 一起安装）

## 2. 相对上游的本地适配（3 处）

1. **skill 格式**：上游安装器写 `<实例 home>/skills/*.md`（单文件），
   而 WorkBuddy 实际按目录加载（`<实例 home>/skills/<name>/SKILL.md`），已改为目录格式。
2. **路径固化**：skill 正文里 `.fstdd/skills/_shared/*.md`、`python bin/fstdd` 均为项目相对路径，
   全局安装后不可解析，已全部替换为绝对路径（指向**法定源**）。
3. **Python 解释器**：FSTDD CLI 依赖 PyYAML + Jinja2。managed Python 的**基座**
   （`binaries/python/versions/3.13.12`）无 PyYAML，但其 **default env**
   （`binaries/python/envs/default/Scripts/python.exe`）已具备
   （实测 3.13.14 / PyYAML 6.0.3 / Jinja2 3.1.6），historically 使用的
   `C:\Python311\python.exe` **本机不存在**。
   故 skill 中的命令统一写为
   `"<default env python>" "E:/FSTDD/stdd-repo/upstream/bin/fstdd"`。

## 3. 安全策略（本机默认）

- **经验回传：静默回传到「我方指定位置」**。`fstdd-deliver` 的 Step 2.8 为**静默自动执行**：
  自动、无交互、不要求使用者额外操作。
  - 有 GitHub 凭证 → 直传 `2749817087qq/Fstdd-experiences`（无写权限自动降级为 fork + PR）
  - 无凭证 → 降级到自建接收端点（`FSTDD_INBOX_URL`，默认 `https://quanthub.ccreits.cn/inbox/api/share-experience`），进待审核池
  - **不向第三方外发**：上游社区仓库与第三方服务器的通道**已永久移除**
  - 载荷强制脱敏；回传失败**不阻断** DELIVER（零阻塞）
  - 结果写入 `.fstdd/share-audit.yaml`；可用 `FSTDD_NO_SHARE=1` 或
    `.fstdd/config.d/experience.yaml` 的 `share.silent.enabled: false` 关闭
- **经验/知识来源已收敛**：`community.registries` 与 `knowledge.community.repo` 均为空，
  不再从上游第三方仓库拉取。
- **联网升级**：`fstdd-upgrade` 会从 `raw.githubusercontent.com` 拉取文件覆盖本地 `.fstdd/` 静态资源，
  属用户主动触发行为，未做改动。
- 未启用仓库自带的 `.fstdd/hooks/*.py` 生命周期钩子，也未启用 `deploy/server-api.py`。

## 4. 升级后必做（硬性规程，不可跳过）

**问题**：`/fstdd-upgrade`、重新拉取仓库、手动覆盖 skill 文件，都会直接覆盖
`~/.workbuddy-ai/skills/fstdd-deliver/SKILL.md`，第 3 节的所有本机策略会**一并消失且没有任何提示**。

**规程**：任何升级 / 重装 / 版本同步之后，立即执行以下两步，缺一不可：

```
"C:\Users\Administrator\.workbuddy-ai\binaries\python\envs\default\Scripts\python.exe" "E:/FSTDD/stdd-repo/tools/install_workbuddy_skills.py"
"C:\Users\Administrator\.workbuddy-ai\binaries\python\envs\default\Scripts\python.exe" "E:/FSTDD/stdd-repo/tools/verify_workbuddy_skills.py"
```

- 第 1 步：重新生成本机适配后的 skill（安全策略、绝对路径、Python 解释器绑定）
- 第 2 步：校验策略哨兵 `FSTDD_LOCAL_POLICY_NO_UPLOAD_V1` **以及静默回传策略块**是否仍在位
- **第 2 步输出 FAIL（退出码 1）时，禁止继续任何 DELIVER 相关操作**，先修复再继续

**防静默失效的三层设计**：

| 层 | 机制 | 失效时表现 |
|----|------|-----------|
| 1. 安装脚本插桩 | 锚定 Step 2.8 并**整段替换**为静默回传策略块 | 锚点失效 → 打印 `[WARN]` 并走兜底，不静默 |
| 2. 兜底策略块 | 锚点不存在时整段前置到正文开头 | 保证哨兵必然存在 |
| 3. 写后 + 独立校验 | 安装后自检；`verify` 脚本可随时复检 | 缺失即 `[FAIL]` + 退出码 1 |

> 第 1 层从「只前置一句注释」改为「整段替换」是有意的：此前注释说「跳过」、
> 而上游正文仍写着「自动上传到社区」，**两句冲突指令并存**，AI 行为不可预期，
> 且等于保留一条指向第三方的语义入口。

该规程已硬编码写入 `fstdd`、`fstdd-deliver`、`fstdd-upgrade` 三个 skill 的正文中，
无论上游如何覆盖源文件，只要重跑安装脚本就会重新出现。

## 5. 使用方式

1. 在项目根目录初始化（每个项目只需一次）：
   ```
   "<default env python>" "E:/FSTDD/stdd-repo/upstream/bin/fstdd" init
   ```
2. 在 WorkBuddy 对话中直接说需求即可按触发词命中，例如：
   - 「用 FSTDD 做一个 XXX 功能」→ `fstdd` 总入口 → `fstdd-understand`
   - 「fstdd-spec」/「fstdd-build」/「fstdd-deliver」可直接进入对应阶段

## 6. 验证记录

### 6.1 功能链路（2026-09-14 实测）

在沙箱项目执行 `init` → `new` → `status`：

- `init`：成功，生成 `.fstdd/` 骨架、FSTDD.md、AGENTS.md、FSTDD_CONSTITUTION.md，Guard 已激活
- `new smoke-test`：成功，生成 change 骨架 + canonical YAML（proposal/specs）
- `status`：成功，输出四阶段 pending 状态

已知非致命告警：

- 使用 managed Python 的**基座解释器**（无 PyYAML）时 `init` 会在注册项目处报
  `ModuleNotFoundError: No module named 'yaml'`
  → 请统一使用 **default env** 的解释器（见 §1 表格）。

### 6.2 防静默失效（2026-09-14）

| 测试 | 操作 | 结果 |
|------|------|------|
| 覆盖检测 | 用上游原件替换已适配的 `fstdd-deliver/SKILL.md` | `verify` 输出 `[FAIL]` 4 项，退出码 1 ✅ |
| 锚点失效兜底 | 正文移除 Step 2.8 锚点后施加策略 | 打印 `[WARN]`，策略块前置到正文开头，哨兵仍在位 ✅ |
| 幂等重跑 | 连续重跑安装脚本 | 无叠加错乱，校验仍 PASS ✅ |
| 恢复 | 重跑安装 + 校验 | skill 全部 PASS ✅ |

### 6.3 法定源与同步（2026-09-16 实测）

| 测试 | 操作 | 结果 |
|------|------|------|
| 法定源建仓 | `git init` + 对齐工作区 | HEAD 一致（`43a4744`）、58 提交、tag `fstdd-v1.0.0` ✅ |
| 双向同步 | 工作区提交探针 → `push canonical` | **法定源工作区文件真的更新**；强制回滚后探针清除 ✅ |
| 上传含 tag | 法定源 `push origin master --tags` | GitHub master 与 tag 均对齐 ✅ |
| 安装产物 | 检查 `~/.workbuddy-ai/skills/fstdd-deliver/SKILL.md` | Step 2.8 已整段替换，上游「上传到社区」正文 **0 处残留**，Step 2.9 未被越界吃掉 ✅ |

### 6.4 skill 目录纠正（2026-09-26 实测）

**背景**：2026-09-16 曾据「内核 bundle 里 `.workbuddy-ai` 字面量出现 0 次」判定
「加载 `~/.workbuddy/skills`」，并把该结论写入**代码默认值、本文档、测试、经验记录**四处。
该判定**依据不足** —— bundle 里读的是环境变量，`~/.workbuddy` 只是兜底值。

**三层取证**：

| # | 证据 | 结果 |
|---|------|------|
| 1 | 内核 `cli/dist/codebuddy.js` 的 `getWorkbuddyConfigDir()` | 首选 `WORKBUDDY_CONFIG_DIR`；本机该变量 = `C:\Users\Administrator\.workbuddy-ai` |
| 2 | 会话可用 skill 列表 | `~/.workbuddy-ai/skills` 下 12 个 **12/12** 命中；`~/.workbuddy/skills` 下 38 个 **0/38** |
| 3 | 行为测试 | `~/.workbuddy/skills/fstdd-understand/SKILL.md` 文件存在，但直接调用返回 `Can not find skill` |

**处置**：

- 目录解析**收口**到 `tools/_skill_install_env.py`（唯一事实源），按内核顺序解析：
  `FSTDD_OUT` → `WORKBUDDY_CONFIG_DIR` → `CODEBUDDY_CONFIG_DIR`
  → `~/.workbuddy-ai`（若存在）→ `~/.workbuddy`；
- 8 个 skill 重装到 `~/.workbuddy-ai/skills`，正文写入生成戳 `生成自 stdd-repo@<版本>`；
- 校验脚本新增：**生成戳校验**（缺失即 FAIL、版本不符 WARN）+ **影子副本探测**（只报告不删除）；
- `test_install_source.py` 的 `test_c2` 由「断言旧错误结论」改为「断言该结论已移除」；
- 顺带修正：`adapt()` 漏替换上游 CLI 旧名，导致装出的 skill 在教 AI 执行不存在的命令
  （实测 11 处，已归零）。

> ⚠️ 遗留：`~/.workbuddy/skills` 下仍有 7 个 `fstdd*` 旧副本。它们**不会被加载**，
> 但会误导排查（看到旧版本号就以为装好了）。安装脚本与校验脚本只报告、不删除，
> 待人工确认后清理。

### 6.5 路径口径定稿（2026-09-29 实测）

**背景**：本文档与若干测试长期把**法定源**写成 `D:/tools/FSTDD/stdd-repo` ——
这是变更 `2026-09-17-migrate-to-d-drive` 的**迁移目标**。但本机从未执行该迁移：
`D:\tools` 不存在，仓库实际位于 `E:\FSTDD\stdd-repo`。后果是
`upstream/tests/test_migrate_to_d_drive.py` **13 项恒红**（测试在守一个从未发生的迁移），
且文档教人使用不存在的 `C:\Python311\python.exe`。

**取证**：

| # | 证据 | 结果 |
|---|------|------|
| 1 | `Test-Path D:\tools` | `False` —— D 盘迁移未落地 |
| 2 | 仓库实际位置 | `E:\FSTDD\stdd-repo`（`git remote -v` 指向 server / local 裸库 / origin） |
| 3 | canonical spec `canonical-in-workspace` SC-001/SC-009 | 法定源 = **工作区内的 `stdd-repo`**（不写死盘符） |
| 4 | 解释器探测 | `C:\Python311\python.exe` 不存在；`<managed default env>` 具备 PyYAML 6.0.3 + Jinja2 3.1.6 |
| 5 | 实跑 `tools/verify_workbuddy_skills.py` | 已装 skill 缺生成戳、含未替换旧路径 ⇒ FAIL（旧安装器产物） |

**定稿**：

- 法定源 = **工作区内的 `stdd-repo`**；本机工作区 = `E:/FSTDD` ⇒ 法定源 = `E:/FSTDD/stdd-repo`；
- D 盘迁移目标（`D:/tools/FSTDD`）标记为**未落地、弃用**，文档 / 脚本 / 测试不再指向它；
- Python 解释器口径 = managed **default env**（具依赖），弃用不存在的 `C:\Python311`；
- `test_migrate_to_d_drive.py` 按实际工作区重写为 `test_repo_home.py`（断言工作区/法定源/裸库/skill 路径一致性），不再假设 D 盘。

> ✅ 下游待办已收口（2026-09-29）：被取代的 spec `d-drive-home` 已从现行 `.fstdd/specs/` 移除。
> 它的 SC-008 / SC-009 仍要求「法定源 SHALL 写为 `D:/tools/FSTDD/stdd-repo`」—— 与该迁移从未
> 落地的事实相反，且与继任 spec `canonical-in-workspace` 冲突（留着会被 `fstdd index` 当作活能力）。
> 历史原文仍留档于 `.fstdd/archive/2026-09-17-migrate-to-d-drive/specs/d-drive-home/spec.md`；
> `canonical-in-workspace` 保留为现行权威。回归锚点见 `upstream/tests/test_repo_home.py::test_d4`。
