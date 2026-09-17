---
name: stdd-deliver
description: STDD Phase 6: 交付 — 归档变更、合并规范、创建版本标签
---
<!-- STDD-HARDENING:NO-UPLOAD v1 -->
> ## ⛔ 数据外发管控（本地策略覆盖，优先级高于上游默认行为）
>
> 本技能经本地全局安装时已做安全加固，**以下行为默认禁用**：
>
> | 步骤 | 行为 | 默认状态 | 启用条件 |
> |---|---|---|---|
> | Step 2.8 | 经验上传至 STDD 外部社区 Git 仓库（`stdd experience share`） | **禁用** | 仅当用户**显式要求**上传/分享经验时执行 |
>
> **判定规则**：
> 1. 默认一律跳过外发步骤，仅在输出中提示"已跳过（默认禁用）"。
> 2. 只有用户在同一轮对话中明确表达上传意图（如"把经验上传到社区"、"share 一下经验"、"同步经验到社区池"）才执行。
> 3. **不得**将"归档完成"、"交付完成"、Step 2.9 知识图谱同步等隐式推断为上传授权。
> 4. 执行前必须列出待上传条目（EXP-ID + 标题 + 内容摘要），经用户二次确认后才调用 `stdd experience share`。
> 5. 用户未明确表态时，按跳过处理，**不要反问**——静默跳过并在摘要中标注。
>
> **原因**：`stdd experience share` 会 POST 到 `https://hzddyy.com/stdd/api/share-experience`，
> payload 含经验正文 `content` 与 `author`（取自 `git config user.name`）。经验条目可能包含项目内部实现细节、
> 业务规则、代码上下文，属于数据外发，需用户知情授权。
>
> **注意**：`stdd-upgrade` 会从 GitHub raw 重新拉取上游技能文件，**会覆盖本声明**。
> 升级后必须重新施加：运行 `python ~/.workbuddy-ai/stdd-hardening/apply.py`


# STDD Phase 6: DELIVER — 交付

## 阶段目标

归档变更、合并规范、创建版本标签。

## 前置条件

- Phase 5 已完成（test-report.md 经用户确认）
- `.stdd.yaml` 中 `phases.verify.confirmed_at` 已设置

## 执行流程

### Step 1: 归档变更

1. 将 `changes/<date>-<name>/` 移动到 `archive/<date>-<name>/`
2. 更新 `.stdd.yaml`（status: archived）

### Step 2: 合并规范

对于变更中的每个 capability spec：

1. 如果是 **NEW** capability：
   - 复制 `changes/<date>-<name>/specs/<capability>/spec.md` → `specs/<capability>/spec.md`
   - 如果 `specs/<capability>/` 已存在，合并新增的 Requirements

2. 如果是 **MODIFIED** capability：
   - 将 changes 中的 spec 新增/修改的 Requirements 合并到 `specs/<capability>/spec.md`
   - 保留合并记录（在 spec 文件中标注变更日期和 change 名称）

### Step 3: 版本标记

1. 展示建议的 commit message 和 tag 名称，等待用户确认
2. 用户确认后执行 git 操作（不自动 push，由用户决定何时 push）

### Step 4: 部署（如需要）

如果项目有部署流程：
1. 读取项目的部署文档或配置
2. 按部署流程执行
3. 如部署需要用户操作，指导用户完成

## 产出物

- `archive/<date>-<name>/` — 归档的完整变更记录
- 更新后的 `specs/<capability>/spec.md` — 合并后的主规范
- Git commit + tag

## 质量检查

- 所有变更文件已提交
- specs 已合并更新，无遗漏
- Git tag 已创建
- `.stdd.yaml` 状态已更新为 archived

## 完成

Phase 6 完成后，整个 STDD 流程结束：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STDD 流程完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ 变更已归档: archive/<date>-<name>/
✅ 规范已合并: specs/
✅ 版本标记: <tag>

📁 归档目录包含完整的：
  - proposal.md / design.md
  - specs / test-plan.md
  - tasks.md / test-report.md
  - design-adjustments.md (如有)

🚀 可以 push 到远程仓库进行部署。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
