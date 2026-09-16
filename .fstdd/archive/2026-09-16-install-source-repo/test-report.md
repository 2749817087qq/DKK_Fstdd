# 法定源确权 + 校验自定位 测试报告

> 变更：`2026-09-16-install-source-repo`
> 执行日期：2026-09-16
> 执行环境：Windows，Python 3.11.9（`C:\Python311\python.exe`）
> 测试工具：`pytest`（`upstream/tests/`）+ 三个 verify 脚本 + git 状态比对

## 一、执行结果总览

| 指标 | 结果 |
|---|---|
| 全量用例总数 | **503** |
| 通过 | **503** |
| 失败 | 0 |
| 退出码 | 0 |
| 基线（本变更前） | 487 passed |
| 本变更新增 | **+16**（`upstream/tests/test_install_source.py`） |

### 1.1 本变更的核心指标：三项校验

| 校验 | 变更前 | 变更后 |
|---|---|---|
| `verify_eol.py` | 7/7 | **7/7** |
| `verify_skill_standards.py` | **5/7** | **7/7** |
| `verify_rename.py` | **7/8** | **8/8** |

> 从**工作区**与**法定源**两处分别运行，结果一致（证明解析不依赖运行位置）。

### 1.2 位置一致性

| 位置 | HEAD | tag |
|---|---|---|
| 法定源 `~/.workbuddy-ai/Fstdd` | `4240a76` | `fstdd-v1.0.0` |
| 工作区 `stdd-repo` | `4240a76` | `fstdd-v1.0.0` |
| GitHub `2749817087qq/DKK_Fstdd` | `4240a76` | `fstdd-v1.0.0` |

## 二、逐项验证（对应 test-plan 的 17 个 TC）

### 功能 1：法定源唯一且为 git 仓库

| TC | 验证内容 | 结果 |
|---|---|---|
| TC-ISR-001 | 法定源是 git 仓库且 HEAD 与工作区一致 | ✅ 58 提交，HEAD 一致 |
| TC-ISR-002 | tag 与上传目标 | ✅ tag 指向同一提交；GitHub 已同步（含 tag） |
| TC-ISR-003 | **双向同步真实可用** | ✅ 见下方实测记录 |
| TC-ISR-004 | 文档写明三者关系 | ✅ `docs/WORKBUDDY_INSTALL_NOTES.md` 第 0 节 |

**TC-ISR-003 实测记录**（非"应该可以"）：

```
工作区提交探针 .sync-probe.txt → git push canonical master
  → 法定源工作区文件真的出现该探针 ✓（证明 updateInstead 生效，而非仅 ref 更新）
  → git reset --hard HEAD~1 && git push canonical master --force
  → 探针从法定源清除 ✓，三方回到 43a4744
```

> 本机 git 对**本地路径 remote** 的远程跟踪引用不 materialize（实测），
> 故反向同步用 `git fetch canonical && git merge --ff-only FETCH_HEAD`（已验证可用）。

### 功能 2：校验脚本安装位置解析

| TC | 验证内容 | 结果 |
|---|---|---|
| TC-ISR-005 | `verify_skill_standards` 解析顺序 | ✅ `FSTDD_INST_DIR` → 法定源 → 脚本自身 → 历史兜底 |
| TC-ISR-006 | `verify_rename` 同策略 | ✅ |
| TC-ISR-007 | 三项校验全绿 | ✅ 7/7、7/7、8/8 |
| TC-ISR-008 | 不依赖 D 盘副本 | ✅ 解析结果为 `~/.workbuddy-ai/Fstdd/tools`，**完全不涉及 D 盘** |

**实测解析结果**：`INSTALLED_TOOLS = C:\Users\Administrator\.workbuddy-ai\Fstdd\tools`

### 功能 3：备份完整性容忍无备份

| TC | 验证内容 | 结果 |
|---|---|---|
| TC-ISR-009 | 无备份时通过 | ✅ `verify_skill_standards` 的 TC-SES-004 现为 PASS |

### 功能 4：数据流收敛到自有仓库

| TC | 验证内容 | 结果 |
|---|---|---|
| TC-ISR-010 | `knowledge.py` 无第三方默认值 + 空值提前返回 | ✅ 唯一残留引用在**文档字符串**中（说明语境） |
| TC-ISR-011 | 两份配置为空且静默开关仍在 | ✅ 见下方断言 |
| TC-ISR-012 | 白名单清空且相关测试通过 | ✅ `ALLOWED_REFS = {}`，`test_a1`/`test_a6` 通过 |

**TC-ISR-011 实测断言**：

```
upstream/.fstdd/config.d/experience.yaml  解析 OK  顶层键=['experience','community','share']
  community.registries = []
  share.silent = {'enabled': True}
upstream/.fstdd/config.d/knowledge.yaml   repo: ""
```

> **本项暴露并修复了一个真缺陷**：该配置原文字面写着
> `share:/n  silent:/n    enabled: true`（**字面的 `/n`，不是换行**），
> 导致 YAML 解析出畸形键 `share:/n  silent:/n    enabled`，
> **`share.silent.enabled` 这个配置项根本不存在** ——
> 文档宣称的「配置文件持久开关」实际无效（env 变量那条仍可用）。
> 已改为合法 YAML 并加断言。

### 功能 5：文档一致

| TC | 验证内容 | 结果 |
|---|---|---|
| TC-ISR-013 | 4 处陈旧内容已修正 | ✅ 见下表 |

| 位置 | 修正前 | 修正后 |
|---|---|---|
| skill 目录 | `~/.workbuddy-ai/skills` | **`~/.workbuddy/skills`**（内核实际加载处） |
| skill 数量 | 6 个 | **7 个**（含 `fstdd-fin`） |
| 经验策略 | 「自动上传：默认禁用」 | **「静默回传到我方指定位置」** |
| 三者关系 | 无 | **新增第 0 节**（法定源／开发副本／上传目标 + 同步命令） |

### 功能 6：归并安全

| TC | 验证内容 | 结果 |
|---|---|---|
| TC-ISR-014 | 独有工作已归并 | ✅ 5 份文件内容已进仓库（`experience.yaml` 为**合并**，保留 `share.silent` 块） |
| TC-ISR-015 | **调试副本未被修改** | ✅ 归并全程对 `D:/Programs/DKK_Fstdd` **只读**（仅 `cp` 出与哈希比对） |

### 功能 7：重装指向法定源

| TC | 验证内容 | 结果 |
|---|---|---|
| TC-ISR-016 | skill 路径指向法定源 | ✅ 见下方断言 |

**TC-ISR-016 实测断言**：

```
含 ~/.workbuddy-ai/Fstdd 的 skill：6/7（第 7 个 fstdd-fin 是领域层，不引用 upstream 路径）
含会话工作区路径（WorkBuddy AI/2026-…）的 skill：0 个 ✓
fstdd-deliver 的 Step 2.8 仍为「经验静默回传（本机策略）」+ 哨兵 ✓
```

## 三、过程中的两次设计修正（记录在案）

本变更在实施中**推翻了自己 SPEC 里的一条决策**，理由充分：

### 3.1 「自定位优先」→「法定源优先」

**原决策（design.md Decision 3）**：解析顺序为 `FSTDD_INST_DIR` → 脚本自身 `tools/` → 法定源 → 历史兜底。
依据是调试副本里那份修复的注释：「自定位 = 本脚本所在仓库的 tools/，它必然与本次安装的 upstream 同源」。

**实测推翻**：该假设在「安装源 = 法定源」的架构下**不成立**。从工作区运行时，
自定位拿到的是**工作区**的 verify，它期望 skill 引用工作区路径；
而 skill 实际引用**法定源**路径 → `verify_skill_standards` 的 TC-SES-001 报
「未发现资源绝对路径（期望含 <工作区>/upstream）」→ **FAIL**。

**修正后**：`FSTDD_INST_DIR` → **法定源** → 脚本自身 → 历史兜底。
理由：被校验对象是**已安装的 skill**，其内固化路径指向**安装源**，
所以必须用**安装源自己的** verify 去校验。

### 3.2 测试硬编码路径

`test_cross_cutting_verification.py` 原以常量硬编码 change 目录
`.fstdd/changes/2026-09-16-contract-auto-share`；该 change 归档后目录移到 `archive/`，
测试随即 `FileNotFoundError`（全量套件实测 1 failed）。

**修正**：改为 `changes/` 与 `archive/` 都查找。

## 四、失败模式检查

按 test-plan 的回归风险矩阵逐条核对：

| 风险区域 | 结论 |
|---|---|
| **误写调试副本**（🔴 高） | ✅ 未发生。全程只读；归并前已做 820 文件全量备份 + 5 个独有文件单独备份 |
| 归并时覆盖掉静默回传开关 | ✅ 未发生。`experience.yaml` 为合并，`share.silent` 块保留并有断言 |
| 校验脚本改动破坏既有断言 | ✅ `verify_skill_standards` 由 5/7 → 7/7；`verify_rename` 由 7/8 → 8/8 |
| 全量测试回归 | ✅ **503 passed**（中途出现 1 例失败，已定位并修复，见 3.2） |
| 自定位改动破坏其他环境 | ✅ 保留 `FSTDD_INST_DIR` 显式覆盖与历史兜底 |

## 五、遗留与已知限制

| # | 项 | 说明 |
|---|---|---|
| L1 | **未删除任何位置** | 按 D哥 决定「先归档不删」。`D:/Programs/DKK_Fstdd` 是另一程序在用的调试副本，**完全未动** |
| L2 | **`~/.workbuddy-ai/Fstdd` 不再算「冗余位置」** | 它是法定源本身，保留 |
| L3 | 本机 git 对本地路径 remote 的远程跟踪引用不 materialize | 反向同步用 `FETCH_HEAD` 绕过（已实测）；不影响正向 push |
| L4 | 未在另一台干净机器上验证 | 「法定源 → 安装 → 校验」全链路只在本机验证过 |
| L5 | 本变更新增 16 个测试（`upstream/tests/test_install_source.py`） | 另有 3 项（TC-ISR-001/002/003）以**真实操作**验证（建仓、tag、双向同步探针），未写成自动化用例 —— 它们依赖本机真实 git 状态，不适合固化为测试 |

## 六、结论

- 全量 **503 passed / 0 failed**。
- 三项校验从**工作区**与**法定源**两处运行**全部全绿**（7/7、7/7、8/8）。
- 法定源、工作区、GitHub **三方一致**（HEAD `4240a76` + tag `fstdd-v1.0.0`）。
- 双向同步**实测可用**；安装产物路径指向法定源。
- 调试副本**未被修改**；其独有工作已归并（含一处真缺陷修复）。
- 过程中两次推翻/修正了自己的设计（3.1、3.2），均已记录。

**本变更可交付。**
