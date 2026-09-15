# FSTDD 全局安装说明（WorkBuddy）

安装时间：2026-09-14
来源仓库：https://github.com/leonai42/stdd （master 分支，V3.0.5，MIT License）
许可：MIT（详见仓库 LICENSE）

## 1. 安装位置

| 内容 | 路径 |
|------|------|
| FSTDD 源码 / CLI / 静态资源骨架 | `C:\Users\Administrator\.workbuddy-ai\Fstdd\upstream` |
| 全局 skill（WorkBuddy 用户级） | `C:\Users\Administrator\.workbuddy-ai\skills\fstdd*` |
| 重装脚本 | `C:\Users\Administrator\.workbuddy-ai\Fstdd\tools\install_workbuddy_skills.py` |
| 校验脚本（升级后必跑） | `C:\Users\Administrator\.workbuddy-ai\Fstdd\tools\verify_workbuddy_skills.py` |

已安装的全局 skill（6 个）：

- `fstdd` — 总入口：判断项目是否已初始化、路由阶段、说明 CLI 位置
- `fstdd-understand` — Phase 1 需求理解与确认（Gate 1）
- `fstdd-spec` — Phase 2 规格设计与测试方案（Gate 2）
- `fstdd-build` — Phase 3 切片规划 + TDD 实现 + 质量验证（Gate 3，V3.0.5 三阶段合一）
- `fstdd-deliver` — Phase 4 归档交付
- `fstdd-upgrade` — 版本同步与升级

## 2. 相对上游的本地适配（3 处）

1. **skill 格式**：上游 WorkBuddy 安装器写 `~/.workbuddy/skills/*.md`（单文件），与本机实际目录
   `~/.workbuddy-ai/skills/<name>/SKILL.md` 不一致，已改为 WorkBuddy 标准目录格式。
2. **路径固化**：skill 正文里 `.fstdd/skills/_shared/*.md`、`python bin/fstdd` 均为项目相对路径，
   全局安装后不可解析，已全部替换为绝对路径
   （`C:/Users/Administrator/.workbuddy-ai/Fstdd/upstream/...`）。
3. **Python 解释器**：FSTDD CLI 依赖 PyYAML + Jinja2。managed Python 3.13 无 PyYAML，
   系统 `C:\Python311\python.exe` 已具备（PyYAML 6.0.2 / Jinja2 3.1.6），
   故 skill 中的命令统一写为 `"C:\Python311\python.exe" "C:/Users/Administrator/.workbuddy-ai/Fstdd/upstream/bin/fstdd"`。

## 3. 安全策略（本机默认）

- **经验自动上传：默认禁用**。`fstdd-deliver` 的 Step 2.8 会把项目沉淀的经验上传到 FSTDD 外部社区 Git 仓库，
  属数据外发。已在 skill 中插入禁用声明，仅当用户显式要求时才执行
  （手动命令：`fstdd experience share <EXP-ID>`）。
- **联网升级**：`fstdd-upgrade` 会从 `raw.githubusercontent.com` 拉取文件覆盖本地 `.fstdd/` 静态资源，
  属用户主动触发行为，未做改动。
- 未启用仓库自带的 `.fstdd/hooks/*.py` 生命周期钩子，也未启用 `deploy/server-api.py`。

## 4. 升级后必做（硬性规程，不可跳过）

**问题**：`/fstdd-upgrade`、重新拉取仓库、手动覆盖 skill 文件，都会直接覆盖
`C:\Users\Administrator\.workbuddy-ai\skills\fstdd-deliver\SKILL.md`，
第 3 节的所有本机策略会**一并消失且没有任何提示**。上传防线就是这样被静默抹掉的。

**规程**：任何升级 / 重装 / 版本同步之后，立即执行以下两步，缺一不可：

```
"C:\Python311\python.exe" "C:/Users/Administrator/.workbuddy-ai/Fstdd/tools/install_workbuddy_skills.py"
"C:\Python311\python.exe" "C:/Users/Administrator/.workbuddy-ai/Fstdd/tools/verify_workbuddy_skills.py"
```

- 第 1 步：重新生成本机适配后的 skill（安全策略、绝对路径、Python 解释器绑定）
- 第 2 步：校验策略哨兵 `FSTDD_LOCAL_POLICY_NO_UPLOAD_V1` 是否仍在位
- **第 2 步输出 FAIL（退出码 1）时，禁止继续任何 DELIVER 相关操作**，先修复再继续

**防静默失效的三层设计**：

| 层 | 机制 | 失效时表现 |
|----|------|-----------|
| 1. 安装脚本插桩 | 按锚点在 Step 2.8 处插入禁用声明 | 锚点失效 → 打印 `[WARN]` 并走兜底，不静默 |
| 2. 兜底策略块 | 锚点不存在时整段前置到正文开头 | 保证哨兵必然存在 |
| 3. 写后 + 独立校验 | 安装后自检；`verify` 脚本可随时复检 | 缺失即 `[FAIL]` + 退出码 1 |

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

## 6. 验证记录（2026-09-14 实测）

### 6.1 功能链路

在沙箱项目执行 `init` → `new` → `status`：

- `init`：成功，生成 `.fstdd/` 骨架、FSTDD.md、AGENTS.md、FSTDD_CONSTITUTION.md，Guard 已激活
- `new smoke-test`：成功，生成 change 骨架 + canonical YAML（proposal/specs）
- `status`：成功，输出四阶段 pending 状态

已知非致命告警：

- `all registries unreachable` — 社区经验 registry 不可达（网络限制），经验库为空，不影响主流程
- 使用 managed Python 3.13 时 `init` 会在注册项目处报 `ModuleNotFoundError: No module named 'yaml'`
  → 请统一使用 `C:\Python311\python.exe`

### 6.2 防静默失效（针对「升级覆盖防线」问题）

| 测试 | 操作 | 结果 |
|------|------|------|
| 覆盖检测 | 用上游原件替换已适配的 `fstdd-deliver/SKILL.md` | `verify` 输出 `[FAIL]` 4 项（哨兵缺失、缺升级规程、残留 `python bin/fstdd`、残留相对路径），退出码 1 ✅ |
| 锚点失效兜底 | 正文移除 Step 2.8 锚点后施加策略 | 打印 `[WARN]`，策略块前置到正文开头，哨兵仍在位 ✅ |
| 幂等重跑 | 连续重跑安装脚本 | 无叠加错乱，校验仍 PASS ✅ |
| 恢复 | 重跑安装 + 校验 | 6 个 skill 全部 PASS ✅ |
