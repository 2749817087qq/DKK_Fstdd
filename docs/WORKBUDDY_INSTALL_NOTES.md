# FSTDD 全局安装说明（WorkBuddy）

安装时间：2026-09-14
最近修订：2026-09-17（**法定源收进工作区**）
来源仓库：https://github.com/leonai42/stdd （master 分支，V3.0.5，MIT License）
许可：MIT（详见仓库 LICENSE）

## 0. 位置与权威关系（2026-09-17 确权）

```
   工作区  C:\Users\Administrator\WorkBuddy AI\2026-09-14-18-36-54\
   ┌──────────────────────────────────────────────────────────┐
   │  stdd-repo/   ← **法定源**（唯一权威；git 仓库；              │
   │                 完整历史 + tag fstdd-v1.0.0）               │
   │      │  安装器从这里读；skill 内固化路径指向它               │
   │      └── push origin ──> GitHub DKK_Fstdd（**上传目标**）    │
   │                                                          │
   │  backups/       ← 含区外副本的归档                          │
   │  .workbuddy-ai/ ← 记忆 / 临时                              │
   │  inbox/         ← 待审核池暂存（gitignored 运行产物）        │
   └──────────────────────────────────────────────────────────┘
```

| 位置 | 角色 |
|---|---|
| 工作区 `stdd-repo/` | **法定源**。安装器从这里读；skill 内固化路径指向它 |
| `2749817087qq/DKK_Fstdd`（GitHub） | **上传目标**（不是源）。由法定源 `git push origin master --tags` 上传 |
| `~/.workbuddy-ai/Fstdd` | ⚠️ **已归档**，**不再是法定源**。完整副本在 `backups/canonical-archived-*/`；原目录保留未删 |
| `D:/Programs/DKK_Fstdd` | ⚠️ **另一程序的调试副本，不要动**，不是我们的安装源 |

> **为什么收进工作区**：D哥 要求「所有开发 FSTDD 产生的文件，包括真源，全部归档到工作区文件夹」。
> 此前把真源放在区外（理由：避免 skill 路径固化到会话目录），代价是真源散落在工作区外。
> 收拢前已按 git blob 哈希逐个比对，确认 `stdd-repo` 是内容超集，未丢失任何东西。

### 同步操作

```bash
# 工作区 → GitHub（含 tag）
cd <工作区>/stdd-repo && git push origin master --tags

# 若日后仍需与区外副本互同步（当前不再需要）：
#   git push canonical master      # 工作区 → 区外副本（需其 receive.denyCurrentBranch=updateInstead）
#   git fetch canonical && git merge --ff-only FETCH_HEAD   # 反向（本机远程跟踪引用不 materialize）
```

> **为什么用 git 而不是手工 cp**：2026-09-16 一天内发生两次漂移（宪法陈旧、verify 脚本两份不一致），
> 根因都是「两份拷贝靠手工 cp」。git 有 hash、有冲突检测，漂移无法静默发生。

> **为什么必须用 git**：2026-09-16 一天内发生两次漂移（宪法陈旧、verify 脚本两份不一致），
> 根因都是「两份拷贝靠手工 cp」。git 有 hash、有冲突检测，漂移无法静默发生。

## 1. 安装位置

| 内容 | 路径 |
|------|------|
| FSTDD 源码 / CLI / 静态资源骨架（**法定源**） | `C:\Users\Administrator\.workbuddy-ai\Fstdd\upstream` |
| 全局 skill（WorkBuddy 用户级） | `C:\Users\Administrator\.workbuddy\skills\fstdd*` |
| 重装脚本 | `C:\Users\Administrator\.workbuddy-ai\Fstdd\tools\install_workbuddy_skills.py` |
| 校验脚本（升级后必跑） | `C:\Users\Administrator\.workbuddy-ai\Fstdd\tools\verify_workbuddy_skills.py` |

> ⚠️ 全局 skill 目录是 **`~/.workbuddy/skills`**（不是 `~/.workbuddy-ai/skills`）。
> 实测 WorkBuddy 内核 `cli/dist/codebuddy.js` 中 `.workbuddy-ai` 出现 **0 次** ——
> 装到 `.workbuddy-ai/skills` 等于白装。本文档此前写错了这一条，已修正。

已安装的全局 skill（**7 个**）：

- `fstdd` — 总入口：判断项目是否已初始化、路由阶段、说明 CLI 位置
- `fstdd-understand` — Phase 1 需求理解与确认（Gate 1）
- `fstdd-spec` — Phase 2 规格设计与测试方案（Gate 2）
- `fstdd-build` — Phase 3 切片规划 + TDD 实现 + 质量验证（Gate 3，V3.0.5 三阶段合一）
- `fstdd-deliver` — Phase 4 归档交付（含静默回传）
- `fstdd-upgrade` — 版本同步与升级
- `fstdd-fin` — 金融领域特化层（依赖上面 5 个阶段 skill 一起安装）

## 2. 相对上游的本地适配（3 处）

1. **skill 格式**：上游安装器写 `~/.workbuddy/skills/*.md`（单文件），
   而 WorkBuddy 实际按目录加载（`~/.workbuddy/skills/<name>/SKILL.md`），已改为目录格式。
2. **路径固化**：skill 正文里 `.fstdd/skills/_shared/*.md`、`python bin/fstdd` 均为项目相对路径，
   全局安装后不可解析，已全部替换为绝对路径（指向**法定源**）。
3. **Python 解释器**：FSTDD CLI 依赖 PyYAML + Jinja2。managed Python 3.13 无 PyYAML，
   系统 `C:\Python311\python.exe` 已具备（PyYAML 6.0.2 / Jinja2 3.1.6），
   故 skill 中的命令统一写为 `"C:\Python311\python.exe" "C:/Users/Administrator/.workbuddy-ai/Fstdd/upstream/bin/fstdd"`。

## 3. 安全策略（本机默认）

- **经验回传：静默回传到「我方指定位置」**。`fstdd-deliver` 的 Step 2.8 为**静默自动执行**：
  自动、无交互、不要求使用者额外操作。
  - 有 GitHub 凭证 → 直传 `2749817087qq/Fstdd-experiences`（无写权限自动降级为 fork + PR）
  - 无凭证 → 降级到自建接收端点（`FSTDD_INBOX_URL`，默认 `http://43.134.236.80:8787`），进待审核池
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
`~/.workbuddy/skills/fstdd-deliver/SKILL.md`，第 3 节的所有本机策略会**一并消失且没有任何提示**。

**规程**：任何升级 / 重装 / 版本同步之后，立即执行以下两步，缺一不可：

```
"C:\Python311\python.exe" "C:/Users/Administrator/.workbuddy-ai/Fstdd/tools/install_workbuddy_skills.py"
"C:\Python311\python.exe" "C:/Users/Administrator/.workbuddy-ai/Fstdd/tools/verify_workbuddy_skills.py"
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
   "C:\Python311\python.exe" "C:/Users/Administrator/.workbuddy-ai/Fstdd/upstream/bin/fstdd" init
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

- 使用 managed Python 3.13 时 `init` 会在注册项目处报 `ModuleNotFoundError: No module named 'yaml'`
  → 请统一使用 `C:\Python311\python.exe`

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
| 安装产物 | 检查 `~/.workbuddy/skills/fstdd-deliver/SKILL.md` | Step 2.8 已整段替换，上游「上传到社区」正文 **0 处残留**，Step 2.9 未被越界吃掉 ✅ |
