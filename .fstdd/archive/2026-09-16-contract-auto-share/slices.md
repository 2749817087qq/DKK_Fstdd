# 切片规划 — 2026-09-16-contract-auto-share

> 模式：standard｜Capability：4 个（3 new + 2 modified）
> 对应 Spec：`canonical/specs/code/2026-09-16-contract-auto-share.yaml`（8 REQ / 20 SC）
> 测试计划：`test-plan.md`（24 TC）

## 切片划分原则

**按「文件所有权」切分，保证切片之间零文件重叠**，从而可并行实施且不产生合并冲突。

| 切片 | 独占文件 |
|---|---|
| Slice 1 | `upstream/fstdd/cli/commands/init.py`、`FSTDD_CONSTITUTION.md`、`.fstdd/memory/FSTDD_CONSTITUTION.md`、`.fstdd/onboarding/AI_OPERATING_MANUAL.yaml` |
| Slice 2 | `tools/install_workbuddy_skills.py`、`tools/share_experience.py` |
| Slice 3 | `upstream/fstdd/cli/commands/upgrade.py` |
| Slice 4 | 仅新增测试文件（不动生产代码） |

## 切片清单

### Slice 1 — 契约面单一真源（constitution-single-source）

| 项 | 内容 |
|---|---|
| **实现** | ① 修 `init.py` 宪法模板：4 处裸 `STDD` → `FSTDD`；把「经验数据不外发 + 需要回传时**显式执行**」纠正为「**静默回传到我方指定位置** + **不向第三方外发**」② 从修好的模板**重新生成**仓库根 `FSTDD_CONSTITUTION.md` ③ 补齐缺失的 `.fstdd/memory/FSTDD_CONSTITUTION.md` ④ 修 `.fstdd/onboarding/AI_OPERATING_MANUAL.yaml:113` 的陈旧表述与旧命令名 |
| **对应 TC** | TC-CAS-014、TC-CAS-015、TC-CAS-016 |
| **依赖** | 无 |
| **风险** | 仓库根宪法由手工维护改为生成产物 —— 若日后有人手工改它，逐字节断言会立即报红（这正是设计意图） |

### Slice 2 — Phase 4 静默回传（phase4-silent-share）

| 项 | 内容 |
|---|---|
| **实现** | ① 改造 `install_workbuddy_skills.py::apply_deliver_policy()`：把 Step 2.8 的**整段上游正文替换**为静默回传策略块（当前是"前置一句注释 + 保留上游正文"，导致矛盾指令并存）；保留哨兵 `FSTDD_LOCAL_POLICY_NO_UPLOAD_V1` 与锚点失效兜底 ② `share_experience.py` 增加**审计记录**（`.fstdd/share-audit.yaml`，append-only）③ 增加**关闭开关**（`FSTDD_NO_SHARE=1` 优先 + `experience.yaml` 的 `share.silent.enabled`）④ 保证**零阻塞**：显式超时 + 全异常吞掉 + 不改退出码 |
| **对应 TC** | TC-CAS-001、002、003、004、005、007、008、009、010、011、012、022 |
| **依赖** | 无 |
| **风险** | 改造策略注入会影响既有 `verify_workbuddy_skills.py` 的哨兵判定 —— 必须保留哨兵语义并同步校验；`.gitignore` 需新增审计文件 |

### Slice 3 — 存量升级（constitution-upgrade）

| 项 | 内容 |
|---|---|
| **实现** | ① 修 `upgrade.py` 的 `UPGRADE_NOTES`：陈旧 rule「Phase 4 DELIVER 自动同步知识图谱」改为指向我方位置；4 处旧名（`stdd init` / `stdd knowledge merge` / 裸 `STDD`）修正 ② 新增 `_migrate_constitution()`：**片段级迁移**（不做整文件覆盖，以保留用户自定义）+ 先备份（复用 `_backup_project_files`）+ 报告改动清单 + 幂等 |
| **对应 TC** | TC-CAS-017、TC-CAS-018、TC-CAS-019、TC-CAS-020 |
| **依赖** | Slice 1（迁移的目标文本需与修正后的模板一致） |
| **风险** | 迁移目标是"已知陈旧片段"，若使用者手工改写过度则片段匹配失败 —— 此时**不得强行覆盖**，应跳过并提示 |

### Slice 4 — 交叉验证（cross-cutting-verification）

| 项 | 内容 |
|---|---|
| **实现** | ① 目标锁死静态扫描（区分**可执行 vs 说明**、**拉取 vs 外发**）② `validate` 的 TC-ID 判定回归（正向：模板写法通过；反向：真实重复仍被捕获）③ **变异验证**：注入 4 个缺陷，要求全部被捕获 |
| **对应 TC** | TC-CAS-006、TC-CAS-021、TC-CAS-023、TC-CAS-024 |
| **依赖** | Slice 1、2、3 全部完成 |
| **风险** | 变异验证若只做 1-2 个缺陷，可能漏掉"某组断言其实空转" —— 故要求 4 个缺陷**全部**被捕获，缺一即视为验证不充分 |

## 执行顺序

```
Slice 1 ─┐
Slice 2 ─┼─ 并行（文件零重叠）─→ Slice 4（依赖前三者产物）
Slice 3 ─┘
```

- Slice 1 / 2 / 3 **可并行**：独占文件互不相交（见上表）。
- Slice 4 **必须最后**：它的扫描对象是前三者的产物。
- Slice 3 依赖 Slice 1 的**文本结果**（迁移目标），但文件不重叠；若并行执行，
  Slice 3 以「修正后的目标文本」为准（在 SPEC 已确定，见 design.md Decision 8），不读 Slice 1 的中间态。

## 失败模式预防（Phase 3 开始前加载经验库）

来自 `.fstdd/experiences/` 与项目记忆的已知坑，本变更有 4 处直接相关：

| # | 已知坑 | 本变更的预防措施 |
|---|---|---|
| 1 | **缩进错误**（Edit 工具的 `old_string` 容忍缩进差异，写入按 `new_string` 原样 → 已两次引入 `IndentationError`） | 改 Python 后**必须** `ast.parse` 校验；不按视觉缩进手写 |
| 2 | **契约与代码不一致**（本次即为复发） | Slice 4 的逐字节断言 + 变异验证 |
| 3 | **脱敏/扫描规则误伤**（域名正则曾把 `README.md` 当域名） | Slice 4 的扫描必须区分可执行/说明、拉取/外发，并对真实数据先跑一遍看误报 |
| 4 | **远端命令被执行两次**（本机 agent 环境特性） | 端到端实测用幂等方式，且以**端状态**（端点计数）而非命令回显作为证据 |

## 偏离记录

| # | 偏离 | 原因 | 影响 |
|---|---|---|---|
| 1 | SPEC 阶段提前修了 `validate.py` 的 TC-ID 误判 | 它阻塞 Gate 2 的 `fstdd validate`；且模板与工具矛盾属本次同类问题 | 已补 REQ-008 / SC-019 / SC-020 / TC-CAS-023/024，追溯链完整 |
| 2 | 新增 Decision 10（扫描的可执行/说明判定规则） | 侦察中发现仓库存在**合法**的第三方标识引用（历史说明 + 拉取配置），简单匹配必然误报 | 无（属设计细化） |
