# STDD (Spec+Test Driven Development) — 通用流程指引 | Universal Guide

> 此文件可作为项目规则加载到任何 AI 编程平台（Cursor, Copilot, Windsurf, Aider 等）。
> This file can be loaded as project rules on any AI coding platform (Cursor, Copilot, Windsurf, Aider, etc.).
>
> 完整设计文档见 / Full design document: [DESIGN.md](DESIGN.md)

---

## V2.9.2: 项目级强制门 / Project-Level Enforcement Gate

> **本项目的 `enforce_stdd: true`。所有代码修改（Edit/Write）必须先通过 STDD 流程启动。**
> **This project has `enforce_stdd: true`. All code modifications MUST go through STDD workflow first.**
>
> 如果你收到修改代码的请求，请先回复用户：
> "本项目启用了 STDD 强制门。请先运行 /stdd-understand 启动变更流程。"
>
> 如果用户明确要求绕过 STDD（如紧急热修复），请在修改完成后补充 `pending-adjustments.yaml` 记录。

---

## 核心原则 / Core Principles

STDD 是一套 Spec+Test 双驱动的研发流程，通过 4 个阶段将需求转化为高质量交付。
STDD is a Spec+Test dual-driven development methodology that transforms requirements into high-quality deliverables through 4 phases (V3.0.5: 6→4 Phase 合并).

**三道强制确认门 / Three Mandatory Confirmation Gates**：
1. Phase 1 结束：用户确认 proposal.md | End of Phase 1: User confirms proposal.md (Gate 1)
2. Phase 2 结束：用户确认 design.md + specs + test-plan.md | End of Phase 2: User confirms design + specs + test-plan (Gate 2)
3. Phase 3 结束：用户确认 test-report.md + design-adjustments.md | End of Phase 3 (BUILD): User confirms test report + design adjustments (Gate 3)

**Gate 2 后执行模式选择 / Execution Mode Selection After Gate 2**：
- 🚀 全自动长程模式（默认）：一次性预授权 → Phase 3 连续自动执行 → Gate 3 等待确认
- 📋 普通交互模式：Phase 3 按需暂停交互 → Gate 3 等待确认

**V3.0.5 Gate 硬防线 / Gate Hardening**：
- Gate 确认必须显式声明通道（`stdd gate approve --confirmed-by dialog|file_token|cli`），省略 → exit 2 拒绝
- 每次确认落审计链：confirmed_by(通道) + confirmed_actor(发起者) + confirmed_evidence(证据) + confirmed_at
- AI 不得静默自跑 approve、不得伪造 evidence；必须先展示确认框、等用户口头确认后执行

**核心理念 / Core Philosophy**：
- Spec 先行 / Spec-first：先定义行为（GIVEN/WHEN/THEN），再写代码。Define behavior before writing code.
- TDD 执行 / TDD execution：RED → GREEN → REFACTOR，按垂直切片推进。Proceed by vertical slices.
- 设计调整可追溯 / Traceable adjustments：实现中对设计的任何偏离必须记录。Every design deviation must be documented.
- 用户确认驱动 / User-confirmation-driven：关键节点必须用户确认。Key checkpoints require explicit user confirmation.

---

## 四阶段流程 / Four-Phase Flow

```
Phase 1: UNDERSTAND  →  proposal.md  →  用户确认 / User confirm (Gate 1)
Phase 2: SPEC        →  design.md + specs + test-plan.md  →  用户确认 / User confirm (Gate 2)
                       └→ 执行模式选择（长程/普通）
Phase 3: BUILD       →  tasks.md + slices.md + TDD RED→GREEN→REFACTOR + test-report.md + design-adjustments.md
                        →  用户确认 / User confirm (Gate 3)
                        (V3.0.5: SLICE/BUILD/VERIFY 合一；十一类失败模式检查 / Eleven failure mode checks)
Phase 4: DELIVER     →  archive + merge specs + git tag
```

### 各阶段简要说明 / Phase Summary

**Phase 1: UNDERSTAND — 需求理解 | Requirement Understanding**
将模糊需求转化为清晰、可验证的变更提案（proposal.md）。Why / What Changes / Capabilities / Impact / Success Criteria。
Transform vague requirements into a clear, verifiable proposal (proposal.md). Why / What Changes / Capabilities / Impact / Success Criteria.

**Phase 2: SPEC — 规格设计 | Spec Design**
这是整个流程中**最重要的阶段** / **The most critical phase**。产出技术设计（design.md）、行为规格（specs/\*.md，GIVEN/WHEN/THEN 格式）、测试方案（test-plan.md，TC-ID 映射）。
Produce technical design (design.md), behavior specs (specs/\*.md, GIVEN/WHEN/THEN format), test plan (test-plan.md, TC-ID mapping).

**Phase 3: BUILD — 实现与质量验证 | Build & Quality Verification**（V3.0.5：SLICE/BUILD/VERIFY 三阶段合一）
将测试方案拆分为垂直切片（tasks.md + slices.md），逐一执行 TDD RED → GREEN → REFACTOR；切片完成后做全量测试 + 覆盖率诊断 + E2E（可配置）+ Lint + Diff 审查 + 十一类失败模式检查，汇总设计调整到 design-adjustments.md。开始前自动加载对应语言规范和相关经验库条目。普通模式最多 5 轮迭代，长程模式最多 10 轮。
Split test plan into vertical slices (tasks.md + slices.md), execute TDD RED → GREEN → REFACTOR per slice; then full test + coverage diagnostics + E2E (configurable) + Lint + Diff review + eleven failure mode checks, summarize adjustments to design-adjustments.md. Auto-loads language standards and experience entries before starting. Max 5 iterations (normal) or 10 (long-range).

**Phase 4: DELIVER — 交付 | Delivery**
归档到 archive/ → 合并 specs 到 specs/ → Git commit + tag。
Archive to archive/ → merge specs to specs/ → Git commit + tag.

---

## 关键规则 / Key Rules

1. **模板先行 / Template First**：编写任何文档前，必须先读取 `.stdd/templates/` 中的对应模板。Must read the template before generating any document.
2. **开发规范 / Dev Standards**：Phase 3 (BUILD) 开始前，必须先读取 `.stdd/standards/<language>.md`。Must read language standard before Phase 3.
3. **Spec→Test 映射 / Mapping**：GIVEN→Arrange, WHEN→Act, THEN→Assert。
4. **垂直切片 / Vertical Slice**：每次只实现一个 spec Scenario → 1+ 测试 → 1 个实现单元。One spec Scenario → 1+ tests → 1 implementation unit per slice.
5. **测试覆盖 / Test Coverage**：新行为必须有测试；测试验证行为而非实现。New behavior must have tests; tests verify behavior not implementation.

---

## 目录结构 / Directory Structure

```
.stdd/              # STDD 系统文件 / System files
  experiences/      # 自学习经验库 / Self-learning experience library (V2.5: 5状态生命周期)
changes/            # 活跃变更 / Active changes
specs/              # 主规范 / Master specs
archive/            # 已完成变更 / Completed changes
```

---

## 文档模板 / Document Templates

所有模板位于 / All templates at `.stdd/templates/`：
- `proposal.md` — 变更提案 / Change proposal
- `design.md` — 技术设计 / Technical design
- `spec.md` — 行为规格 (GIVEN/WHEN/THEN) / Behavior spec
- `spec-draft.md` — AI 生成 spec 草稿 (V2.4+) / AI-generated spec draft
- `test-plan.md` — 测试方案 / Test plan
- `tasks.md` — 任务清单 / Task list
- `slices.md` — 切片计划 / Slice plan
- `design-adjustments.md` — 设计调整说明 / Design adjustments
- `test-report.md` — 测试报告 / Test report

---

## 开发规范 / Development Standards

位于 / Located at `.stdd/standards/`：
- `python.md` — Python 开发规范 / Python dev standard（V1.0 起）
- `java.md` — Java / Spring Boot 规范（V2.3 新增）
- `go.md` — Go 标准布局规范（V2.3 新增）
- `rust.md` — Rust / Cargo 规范（V2.3 新增）
- `typescript.md` — TypeScript / Node.js 规范（V2.3 新增）

---

## 命令 / Commands

| 命令 / Command | 说明 / Description |
|---------------|-------------------|
| `/stdd-understand` | Phase 1: 需求理解与确认 / Requirement understanding |
| `/stdd-spec` | Phase 2: 规格设计与测试方案 / Spec & test design |
| `/stdd-continue` | 从当前阶段继续执行 (Phase 3-4) / Continue from current phase |
| `/stdd-status` | 查看当前变更状态 / View current change status |
