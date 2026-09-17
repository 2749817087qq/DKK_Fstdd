---
task_id: FSTDD003
schema: fstdd-distributed-task/v0.1
title: FSTDD 安装/运行工程测试与经验回传
status: archived          # pending | running | blocked | done | archived
created: 2026-09-12
updated: 2026-09-17
node: WORKBUDDY-AI-WIN   # 执行节点标识（本实例）
owner: D哥
mode: fstdd              # 走 FSTDD 四阶段 + 三确认门
upstream: https://github.com/2749817087qq/DKK_Fstdd.git
experience_repo: 2749817087qq/Fstdd-experiences
inbox: http://43.134.236.80:8787
depends_on: []
tags: [install, hardening, experience-upload, distributed]
---

# FSTDD003 — 分布式任务卡

> 任务目录即任务根：`D:\FSTDD003`。
> 编号规则：**FSTDD + 三位序号**，全局唯一，跨节点不重复。
> 每个任务目录都必须是**可独立运行的 FSTDD 工作区**（含 `.fstdd/` 骨架 + `tools/`）。

## 1. 任务定义

| 项 | 内容 |
|---|---|
| 目标 | 卸载旧 STDD，安装自研 FSTDD，做工程测试，把安装/运行问题回传到经验库 |
| 范围 | 仅限 **WorkBuddy AI 实例**（home = `~/.workbuddy-ai`）。另一实例 `~/.workbuddy` 不在范围内 |
| 交付 | 安装成功 + 7 个 skill 落位 + 三轮问题清单 + 27 条经验回传成功 |
| 终止条件 | 经验回传服务端确认接收，本地 commit 完成 |

## 2. 四阶段执行记录

| 阶段 | 产出 | 确认门 | 状态 |
|---|---|---|---|
| P1 UNDERSTAND | 需求澄清：卸载旧 STDD、装 FSTDD、问题回传 | Gate 1 | ✅ |
| P2 SPEC | `docs/INSTALL_RUN_ISSUES_2026-09-16.md`（4 项已修 + 5 项待修） | Gate 2 | ✅ |
| P3 BUILD | `install.sh` 4 项修复；三层外发防护；自建接收端点降级链 | Gate 3 | ✅ |
| P4 DELIVER | 三轮复测清单；27/27 经验回传；本地 6 个 commit | — | ✅ |

## 3. 分布式执行约定（供后续任务沿用）

1. **任务根 = 目录名**：`D:\FSTDD<NNN>`，目录内必须有 `TASK.md` 与 `.fstdd/`。
2. **节点标识**：每个执行实例在 `node` 字段登记自己的标识，禁止两个节点同时写同一任务目录。
3. **幂等**：任务卡只增不改历史结论；状态变更必须同时更新 `updated`。
4. **依赖**：`depends_on` 填上游 task_id，上游未 done 不得启动。
5. **经验回传**：无 GitHub 凭证时自动降级 POST 到 `inbox`；**禁止第三方外发**。
6. **产物不入库**：`experiences/` 是导出产物，已 `.gitignore`；留存靠回传通道。

## 4. 本任务关键结论（可复用）

- **实例 home 隔离**：WorkBuddy 只扫**自己 home + `skills/`**。`~/.workbuddy` 与 `~/.workbuddy-ai` 各扫各的，不是同一实例扫两处。
- **Git Bash → Windows Python 路径**：`/c/Users/...` 会被解析成 `\c\Users\...`，必须过 `cygpath -m`。
- **`for arg in "$@"` + `shift` 失效**：迭代列表展开时已固定，改用下标遍历。
- **升级覆盖防线**：上游升级会静默覆盖 `deliver.md`，每次升级后必须重跑
  `install_workbuddy_skills.py` + `verify_workbuddy_skills.py`，校验哨兵 `FSTDD_LOCAL_POLICY_NO_UPLOAD_V1`。
- **回传口径坑（P10）**：`publish` 提交的是**导出目录全量**，`README` 索引只反映源目录条数，两者不一致且会重复累加服务端计数。
  伴生问题：**导出目录不清理陈旧条目**，源目录删了、导出目录还在，口径持续漂移。
  本次已手工对齐到 **源 26 = 导出 26 = 索引 26**。

## 5. 遗留项

- [ ] 本地 6 个 commit 未 push（`github.com:443` 不通、代理 502、SSH 公钥未授权）
- [ ] P10 / P11 尚未回传（再跑一次会重复提交全量 27 条，等服务端去重后再传）
- [ ] `install.sh` 4 项修复未合入上游
- [ ] 待修：P5 token 路径、P6 Guard 平台误判、P7 verify 漏校验、P8 change 名不支持中文、P9 子命令缺参提示
- [ ] **P12 待修**：`extract-proposal` 与 Gate 生成物不兼容（`canon.py::_generate_one()` 只渲染 5 个 section，
      模板 14 个，解析器按模板解析）→ `capabilities/constraints/risk_areas/non_goals` 静默丢空，
      **`what_changes` 虚增**（H3 不终止 H2 区间，被 `_parse_section` 吞并）。最小修法：生成器补 `## Capabilities` 父标题。
- [ ] **P13 待修**：嵌套工作区下 change 落到父工作区；`canon.py::_generate_one()` 的
      change 级 → 项目级 canonical 回退**不打印警告**。另：CLI 入口在 Git Bash 下需 `cygpath`（既有 P3 的同类遗漏）。
- [ ] **P14 待修**：`init` 自动拉社区经验必失败（registry 指向的仓库无 release → 404），
      且 `_post_init_experiences()` 用 `except Exception` 把 404 归因成"网络不可用"；
      提示里的命令名仍是旧 `stdd`。

## 6. 第四轮（2026-09-17 · 真实业务变更实战）

前两轮测**安装/运行**，本轮测**真实变更跑流程**：在既有项目根下新建子工作区 `reits-writer/`，
`fstdd init` 后立变更 `2026-09-17-corpus-paragraph-integrity`，走完 Phase 1（Gate 1）→ Phase 2。

**结论：安装链路与骨架生成已稳；流程链路（Gate 生成物 ↔ CLI 解析器 ↔ 多工作区锚定）有实质缺陷。**

| 编号 | 问题 | 严重度 | 经验条目 |
|---|---|---|---|
| P12 | `extract-proposal` 对 Gate 生成物系统性失效 + `what_changes` 虚增污染 | **高** | `EXP-20260917-EXTRACT-1` |
| P13 | 嵌套工作区下 change 落到父工作区 + canonical 双轨回退静默写错位置 | 中 | `EXP-20260917-MULTIWS-1` |
| P14 | `init` 自动拉社区经验必失败 + 报错归因错误 | 低 | `EXP-20260917-REGISTRY-1` |

报告全文：`docs/RUN_ISSUES_2026-09-17_reits-writer.md`

### 本轮新增可复用结论

- **P12 最危险处不是"丢空"而是"虚增"**：`what_changes` 6 → 10 条，**数量变多，不看内容发现不了**。
  根因是 `### New Capabilities`（H3）**不终止** `## What Changes`（H2）区间 —— 缺 `## Capabilities`
  父标题时，capability 的 bullet 被 `_parse_section` 吞并。**静默失败里，"变多"比"变空"更难察觉。**
- **Canonical-First 的正确用法**：`canonical/proposals/<change>.yaml` 是唯一真源，
  `proposal.md` 只是 Human View。**人工核对 Gate 内容时直接读 YAML，不要依赖 `extract-proposal` 摘要。**
- **嵌套工作区铁律**：执行 `fstdd` 命令前**显式 `cd` 到目标工作区根**；产出后用
  **绝对路径核对落点**；发现落错位置**不擅自搬迁**（会破坏 Gate 已确认的 traceability），
  记录在案 + 向上游反馈。
- **Git Bash 调 Windows Python 必过 `cygpath -m`**：既有 P3 只覆盖 `install.sh`，
  本轮确认 **CLI 入口 `bin/fstdd` 同样踩**（`~` → `/c/Users/...` → `\c\Users\...` → `can't open file`）。
- **"社区经验拉不到 ≠ 初始化失败"**：`_post_init_experiences()` 异常被吞，`init` 仍 rc=0，可继续。
