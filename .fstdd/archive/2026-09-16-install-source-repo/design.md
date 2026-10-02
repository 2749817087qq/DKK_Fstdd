# 法定源确权 + 校验自定位 - 技术设计

## Context

### 机器上并存三个位置，职责从未定清

| 位置 | 性质 | 状态（本变更前） |
|---|---|---|
| `…/stdd-repo`（会话工作区） | 开发副本 | 最新，含全部提交 |
| `~/.workbuddy-ai/Fstdd` | **法定源**（`docs/WORKBUDDY_INSTALL_NOTES.md` 指定） | **无 `.git`**，靠 cp 同步 |
| `D:/Programs/DKK_Fstdd` | **另一程序的调试副本** | 落后，且有独有未提交工作 |

三者之间靠**手工 cp** 同步 —— 这是本日两次漂移（宪法陈旧、verify 脚本两份不一致）的共同根因。

### 三个具体故障

1. `verify_skill_standards.py::_installed_tools()` 把 `D:/Programs/DKK_Fstdd` **硬编码在首位**
   → 从工作区运行时去校验调试副本，而那份期望 skill 引用 D 盘路径 → **必然 FAIL**。
2. 同一脚本的「备份完整性」**无条件要求存在 `--fix` 备份**，但 `--fix` 幂等、
   树已合规时不改动也就**不留备份** → 合规环境里恒定 FAIL。
3. 上一轮我从**工作区**重装 skill，导致 skill 内路径固化到**会话目录** ——
   与既有文档（应指向法定源）相悖。

### 约束

- `D:/Programs/DKK_Fstdd` 是另一程序在用的调试副本，**不得写入**（D哥 明确）。
- 法定源必须有**工作区**（安装器要读 `…/Fstdd/upstream`），故不能是 bare 仓库。
- 全量测试基线 **487 passed**，不得回归。
- 本机 git 对**本地路径 remote** 的远程跟踪引用不 materialize（实测），需绕开。

## Decisions

### 1. 法定源 = `~/.workbuddy-ai/Fstdd`，并建成 git 仓库

**方案**：在该目录 `git init`，`origin` = GitHub，与工作区建立 git 双向同步。

**为什么**：该路径**已被既有文档指定**（`docs/WORKBUDDY_INSTALL_NOTES.md` 第 1 节），
且调试副本里的自定位修复注释也把它称作「规范位置」——两条独立证据同向。
选它而非新造路径，避免再多一个位置。

**备选方案及排除原因**：
- 备选 A：`D:/Programs/DKK_Fstdd` → 排除。D哥 明确它是另一程序在用的调试副本。
- 备选 B：工作区 `stdd-repo` → 排除。它在会话目录下，skill 路径固化到它会随会话失效。
- 备选 C：新建一个路径 → 排除。既有文档已指定，新造会增加位置而非减少。

### 2. 用 git 取代手工 cp 作为同步机制

**方案**：工作区设 `canonical` remote 指向法定源；法定源设 `receive.denyCurrentBranch=updateInstead`。

**为什么**：手工 cp 没有 hash、没有冲突检测，**漂移可以静默发生** —— 本日已发生两次。
git 天然带 hash 与冲突检测，漂移无法静默。`updateInstead` 让「推入即更新工作区」，
这样安装器读到的永远是最新文件。

**备选方案及排除原因**：
- 备选 A：继续手工 cp → 排除。已证明会漂移。
- 备选 B：把法定源做成 bare 仓库 → 排除。安装器需要工作区文件。
- 备选 C：用 rsync 等同步工具 → 排除。引入新依赖，且无冲突检测语义。

### 3. 自定位优先的解析顺序

**方案**：`FSTDD_INST_DIR`（显式覆盖）→ 脚本自身所在仓库的 `tools/` → 法定源 → 历史位置兜底。

**为什么**：脚本自身所在仓库必然与「本次安装」同源，是最可靠的默认；
显式覆盖留给 CI/特殊场景；历史位置只作兜底以免破坏既有环境。

**注意**：本机 git 对本地路径 remote 不 materialize 远程跟踪引用（实测），
所以反向同步用 `git fetch canonical && git merge --ff-only FETCH_HEAD`，
不依赖 `canonical/master` 引用。

### 4. 备份检查：容忍「无备份」

**方案**：把「至少存在一次 `--fix` 备份」从**必要条件**改为**条件校验**——
存在备份时才校验其正文与当前文件一致；不存在时视为合法（树已合规，无需备份）。

**为什么**：`--fix` 幂等，合规树不会产生备份。原断言在合规环境里**恒定 FAIL**，
属于「断言把合法状态当成错误」。

### 5. 数据流完全收敛到自有仓库

**方案**：采纳调试副本的独有工作 —— `knowledge.py` 移除第三方默认值并在 `repo` 为空时提前返回；
`knowledge.yaml` 的 `repo` 置空；`experience.yaml` 的 `registries` 置空。

**为什么**：D哥 决定「完全收敛到自有仓库」。既有策略允许「拉上游社区（只进）」，
本次把**拉取源也去掉**。

**关键实现细节（来自调试副本的注释，值得保留）**：仅把 `repo` 置空是不够的 ——
空值会落到下方的 `gh clone` 分支**仍然外联**。必须**提前返回**。

**连带影响**：`contract-auto-share` 的 `ALLOWED_REFS` 条目（理由为「拉取源属既定策略」）
**立即失效**，必须移除；其 `test_a6_allowlist_is_not_rotten` 会因此由红转绿。

### 6. `experience.yaml` 必须**合并**而非覆盖

**方案**：归并时保留仓库侧的 `share.silent.enabled` 块，同时引入调试副本的 `registries: []`。

**为什么**：两份文件在**不同方向**上各自前进过：仓库加了静默回传开关，调试副本移除了三方 registry。
直接覆盖会丢一边。

### 7. 调试副本只读

**方案**：对 `D:/Programs/DKK_Fstdd` 只做 `cp` 出与哈希比对，**绝不写入**。
归并前后各算一次哈希清单以证明未改动。

**为什么**：它是另一程序的调试副本，改动会影响那个程序。这是硬约束，不是偏好。

### 8. 文档与事实对齐

**方案**：修正 `docs/WORKBUDDY_INSTALL_NOTES.md` 的 4 处陈旧内容（skill 目录、数量、
经验策略、三者关系）。

**为什么**：该文档正是「法定源」这一判断的依据来源，**它自己陈旧**会持续误导。
这与 `contract-auto-share` 修的是同一类问题。

## Architecture

```
                    法定源  ~/.workbuddy-ai/Fstdd
                    （唯一权威；git 仓库；有工作区）
                              │
        ┌─────────────────────┼──────────────────────┐
        │                     │                      │
   git push canonical    git push origin        安装器读它
        │                     │                 （skill 路径固化到此处）
        ▼                     ▼                      ▼
   工作区 stdd-repo      GitHub DKK_Fstdd      ~/.workbuddy/skills/fstdd*
   （开发副本）           （上传目标）           （AI 实际读到的）

  反向：工作区 git fetch canonical && git merge --ff-only FETCH_HEAD

  ⚠️ D:/Programs/DKK_Fstdd —— 另一程序的调试副本，本变更只读不写
```

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| **误写调试副本，影响另一程序** | 全流程只读；归并前后哈希比对（TC-ISR-015）作为硬断言 |
| 归并 `experience.yaml` 时覆盖掉静默回传开关 | 明确要求**合并**（Decision 6）；TC-ISR-011 断言 `share.silent.enabled` 仍在 |
| 法定源工作区被推入时与本地改动冲突 | `updateInstead` 在目标工作区不干净时会**拒绝**推送（git 内建保护），不会静默覆盖 |
| 本地路径 remote 的跟踪引用不可用 | 反向同步改用 `FETCH_HEAD`（已实测可用） |
| 自定位改动破坏既有 CI/其他环境 | 保留 `FSTDD_INST_DIR` 显式覆盖与历史位置兜底 |
| 移除第三方拉取源后，社区经验图谱不再更新 | 属**有意决策**（完全收敛到自有仓库）；配置项保留可改回 |
| 归档的 `contract-auto-share` 测试随白名单调整而变 | 白名单移除后 `test_a6` 由红转绿，需重新跑归档测试确认 |
| 文档修正不彻底，继续误导后续判断 | 逐条对照实测值（TC-ISR-013） |
