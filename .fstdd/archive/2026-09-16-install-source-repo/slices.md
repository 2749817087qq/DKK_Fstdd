# 切片规划 — 2026-09-16-install-source-repo

> 模式：standard｜Capability：2 new + 4 modified
> 对应 Spec：`canonical/specs/code/2026-09-16-install-source-repo.yaml`（7 REQ / 15 SC）
> 测试计划：`test-plan.md`（17 TC）

## 切片清单

### Slice 1 — 法定源建仓与双向同步（canonical-source）

| 项 | 内容 |
|---|---|
| **实现** | `~/.workbuddy-ai/Fstdd` 执行 `git init`；设 `origin` = GitHub；设 `receive.denyCurrentBranch=updateInstead`；工作区加 `canonical` remote；用**真实探针**验证双向同步 |
| **对应 TC** | TC-ISR-001、TC-ISR-002、TC-ISR-003 |
| **依赖** | 无 |
| **风险** | 该目录原有 820 文件且含独有工作 —— 先做全量备份再对齐，否则会丢 |

### Slice 2 — 归并调试副本的独有工作（merge-unique-work）

| 项 | 内容 |
|---|---|
| **实现** | ① `knowledge.py`：移除硬编码第三方默认值 + `repo` 为空时提前返回 ② `knowledge.yaml`（两份）：`repo: ""` ③ `experience.yaml`（两份）：`registries: []`，**与仓库侧 `share.silent` 块合并** |
| **对应 TC** | TC-ISR-010、TC-ISR-011、TC-ISR-014、TC-ISR-015 |
| **依赖** | Slice 1（备份已就位） |
| **风险** | ① `experience.yaml` 必须**合并而非覆盖**，否则丢静默开关 ② 调试副本**只读** ③ 该文件含字面 `/n` 的真缺陷（见 design-adjustments D2） |

### Slice 3 — 校验自定位与备份容忍（verify-resolution）

| 项 | 内容 |
|---|---|
| **实现** | ① `verify_skill_standards._installed_tools()`：解析顺序改为 `FSTDD_INST_DIR` → **法定源** → 脚本自身 → 历史兜底 ② 备份完整性检查：容忍「无备份」 ③ `verify_rename.py` 同步 |
| **对应 TC** | TC-ISR-005、TC-ISR-006、TC-ISR-007、TC-ISR-008、TC-ISR-009 |
| **依赖** | Slice 1（法定源需存在） |
| **风险** | 解析顺序初版按「自定位优先」实施，实测**不成立**并推翻（design-adjustments D1） |

### Slice 4 — 契约面收敛与文档对齐（contract-and-docs）

| 项 | 内容 |
|---|---|
| **实现** | ① `contract-auto-share` 的 `ALLOWED_REFS` 清空（理由随拉取源移除而失效） ② `docs/WORKBUDDY_INSTALL_NOTES.md` 修正 4 处 + 新增第 0 节三者关系 ③ 从法定源重装 skill 并验证路径 |
| **对应 TC** | TC-ISR-004、TC-ISR-012、TC-ISR-013、TC-ISR-016 |
| **依赖** | Slice 2、Slice 3 |
| **风险** | 文档是「法定源」判断的依据来源，它自己陈旧会持续误导后续判断 |

## 执行顺序

```
Slice 1（建仓+备份） → Slice 2（归并） ─┐
                                        ├─→ Slice 4（契约+文档+重装）
Slice 3（校验自定位） ─────────────────┘
```

- Slice 1 **必须最先**：它同时完成「建仓」与「保护性备份」，是后续切片的安全前提。
- Slice 2 与 Slice 3 可并行（文件不重叠）。
- Slice 4 依赖前两者（白名单与文档都引用其结论）。

## 失败模式预防（Phase 3 开始前加载经验库）

来自 `.fstdd/experiences/` 与项目记忆的已知坑，本变更有 4 处直接相关：

| # | 已知坑 | 本变更的预防措施 |
|---|---|---|
| 1 | **误改不属于自己的目录**（调试副本被另一程序使用） | 全程只读；归并前做全量备份；不删除任何位置 |
| 2 | **契约与实际不一致**（本日已复发多次） | 文档逐条对照实测值；配置加解析断言 |
| 3 | **硬编码路径在环境变化后失效** | change 目录查找兼容 `changes/` 与 `archive/`；安装位置解析保留显式覆盖与兜底 |
| 4 | **写文件默认 CRLF**（`write_text` 在 Windows 翻译换行） | 改完统一跑 `verify_eol --fix` 自愈 |

## 偏离记录

见 `design-adjustments.md`（5 项，其中 D1 推翻了 SPEC 的一条决策）。
