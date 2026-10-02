---
name: fstdd
description: |
  FSTDD（Spec+Test Driven Development）总入口：Spec 先行 + TDD 执行的 AI 辅助研发流程，四阶段（UNDERSTAND → SPEC → BUILD → DELIVER）+ 三道用户确认门 + 失败模式检查。负责判断项目是否已初始化 FSTDD、路由到正确的阶段 skill，并说明 CLI 与静态资源位置。
  触发词：FSTDD、fstdd、spec 驱动开发、测试驱动开发、TDD 流程、规约驱动、四阶段流程、用 FSTDD 开发
version: "3.0.5"
stdd_version: "3.0.5"
license: MIT（上游 STDD leonai42/stdd，版权归杭州大道一以科技有限公司；
  本文件为其在 WorkBuddy 平台的适配版本，含本地安全策略与路径适配）
source: https://github.com/leonai42/stdd
---


# FSTDD 总入口（WorkBuddy 全局安装）

## 这是什么

FSTDD = **Spec 先行 + TDD 执行**。先定义行为（GIVEN/WHEN/THEN 规格），再写测试，最后实现代码。
四阶段 + 三道强制用户确认门（Gate 1/2/3），把模糊需求变成有据可查、有测可验的交付。

| 阶段 | 触发 skill | 主要产出 | 确认门 |
|------|-----------|---------|--------|
| P1 UNDERSTAND | `fstdd-understand` | canonical/proposals/<change>.yaml、proposal.md | Gate 1 |
| P2 SPEC | `fstdd-spec` | design.md、specs/*.md、test-plan.md | Gate 2（最关键） |
| P3 BUILD | `fstdd-build` | slices、TDD 实现、test-report.md | Gate 3 |
| P4 DELIVER | `fstdd-deliver` | archive、合并 specs、git tag | 无 |

## 本机安装位置

- 静态资源与模板：`D:/FSTDD003/upstream`
- CLI 入口：`"C:\Users\Administrator\.workbuddy-ai\binaries\python\envs\default\Scripts\python.exe" "D:/FSTDD003/upstream/bin/fstdd"`
  - 依赖 PyYAML / Jinja2 / requests，本机使用 `C:\Users\Administrator\.workbuddy-ai\binaries\python\envs\default\Scripts\python.exe`（已具备）；换成其他解释器请先确认依赖
- 已安装的阶段 skill：`D:/FSTDD003/.fstdd/changes/2026-09-30-multi-platform-adapters/baselines/workbuddy` 下的 `fstdd-understand/` `fstdd-spec/` `fstdd-build/` `fstdd-deliver/` `fstdd-upgrade/`

> 生成自 stdd-repo@3.1.0（本机适配层；重装后此值随仓库版本更新）

## 首次使用（必须先初始化项目）

在**项目根目录**执行：

```
"C:\Users\Administrator\.workbuddy-ai\binaries\python\envs\default\Scripts\python.exe" "D:/FSTDD003/upstream/bin/fstdd" init
```

生成 `.fstdd/` 骨架（模板、config.d、rules、knowledge 等）与项目状态文件。
未初始化的项目，阶段 skill 中引用的 `.fstdd/templates/*`、`.fstdd/config.d/*` 将不存在，流程无法完整执行。

## 路由规则

1. 用户提出一个模糊需求，要做功能/改造 → `fstdd-understand`
2. proposal 已确认，要设计规格与测试方案 → `fstdd-spec`
3. 规格已确认，要实现（切片 + TDD + 验证） → `fstdd-build`
4. 验证通过，要归档交付 → `fstdd-deliver`
5. 提示版本漂移或要升级 → `fstdd-upgrade`
6. **当前项目没有 `.fstdd/` 目录时，一律先执行初始化再进入任何阶段。**

## 安全提示（本机策略）

- `fstdd-deliver` 的 Step 2.8「经验回传」为**静默回传**：自动执行、无交互、失败不阻断 DELIVER。
  回传目标只有两个我方位置 —— 有凭证走 `2749817087qq/Fstdd-experiences`（无写权限自动 fork + PR），
  无凭证走自建接收端点 `FSTDD_INBOX_URL`（默认 `https://quanthub.ccreits.cn/inbox/api/share-experience`）；**不向第三方外发**。
  载荷强制脱敏，结果写入 `.fstdd/share-audit.yaml`；可用 `FSTDD_NO_SHARE=1` 关闭。
  该策略带哨兵标记 `FSTDD_LOCAL_POLICY_NO_UPLOAD_V1`，可被校验脚本检测。
- `fstdd-upgrade` 会从 `raw.githubusercontent.com` 拉取文件覆盖本地 `.fstdd/` 静态资源，属用户主动触发的联网行为。


## ⛔ 升级 / 重装后必做（本机硬性规程）

上游升级（`/fstdd-upgrade`、重新拉取仓库、手动覆盖 skill 文件）会**直接覆盖本文件**，
本机施加的安全策略与路径适配会随之消失，且**不会有任何提示**。因此：

**每次升级后，必须立即执行以下两步，缺一不可：**

```
"C:\Users\Administrator\.workbuddy-ai\binaries\python\envs\default\Scripts\python.exe" "D:/FSTDD003/tools/install_workbuddy_skills.py"
"C:\Users\Administrator\.workbuddy-ai\binaries\python\envs\default\Scripts\python.exe" "D:/FSTDD003/tools/verify_workbuddy_skills.py"
```

- 第 1 步重新生成本机适配后的 skill（含安全策略、绝对路径、Python 解释器绑定）
- 第 2 步校验策略哨兵 `FSTDD_LOCAL_POLICY_NO_UPLOAD_V1` 是否仍在位
- **第 2 步输出 FAIL 时，禁止继续任何 DELIVER 相关操作**，先修复再继续

升级后如未执行上述步骤即进入 Deliver 阶段，视为**流程违规**。

