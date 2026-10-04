# 2026-09-18-inbox-api-only-write 切片执行计划

> 范围：仅 **A 仓库侧**（本机 pytest 可验）。B 外部挂账见 test-plan §零。

## Dependency Graph Summary

```
  inbox-api-only-write        inbox-deploy
   (零依赖, P0)                (零依赖, P0)
        │                           │
        └──────────┬────────────────┘
                   ▼
              Part C 全量回归
   (TC-IBDP-006：pytest upstream/tests)

  两个 capability 之间无 import / 调用边（edges 为空），可并行。
```

**并行化说明**：
- 并行组 1：切片 1（inbox-api-only-write 鉴权三态）、切片 2（inbox-deploy 脚本加固）—— 二者零依赖，可并行。
- 合并验证：两切片完成后由 Part C 全量回归一次性确认无交叉影响。

## Slice Execution Plan

| # | 优先级 | 风险 | 预估工时 | 并行组 | TC 覆盖 | 实现目标 | 依赖 |
|---|--------|------|---------|--------|---------|---------|------|
| 1 | P0 | 🟡 Med | M | 组1 | TC-IAOW-006, TC-IAOW-007, TC-IAOW-008, TC-IAOW-009 | `tools/inbox_server.py`：`_authorized()` 三态 + `_auth_banner()` + `/health` 免鉴权 | 无 |
| 2 | P0 | 🟡 Med | M | 组1 | TC-IBDP-002, TC-IBDP-003, TC-IBDP-004 | `tools/deploy_inbox_server.sh`：建用户/收权/单元加固/env 存在性校验/后置校验段 | 无 |
| — | P0 | 🟢 Low | S | — | TC-IBDP-006 | Part C 全量 `pytest upstream/tests`（回归保护，非独立切片） | 1, 2 |

## Rationale

### Slice 1: inbox-api-only-write 鉴权三态（P0，可并行）
- **依赖关系**：与切片 2 无依赖边（dependency-graph edges 为空），故并列组 1。
- **风险分析**：中风险（🟡）。仓库版当前**无鉴权代码**（grep 零命中），由「无鉴权」升级为「三态」属行为变更，须防既有 A/B/C 组回归。经验库命中：
  - `EXP-2026-0014`（silent-exception）：IP 白名单解析遇非法项**不得静默吞掉** —— 实现改为 stderr 显式告警。
  - `EXP-2026-0013`（declared-form vs impl）：声明支持的 IP 形态（单 IP / CIDR）须以 parametrized 用例逐一校验。
- **工作量估算**：M（4 个 TC，1 个源文件 + 1 个测试文件修改）。

### Slice 2: inbox-deploy 脚本加固（P0，可并行）
- **依赖关系**：与切片 1 无依赖边，并列组 1。
- **风险分析**：中风险（🟡）。当前脚本 `User=ubuntu` 且单元模板**无 `EnvironmentFile` 行** —— 重跑即静默丢鉴权（双漂移陷阱）。回到「测试绿了 ≠ 断言有效」教训（memory §4），后置校验**必须含负向断言**（ubuntu 写入必须被拒），否则权限未收口也会全绿。静态守护用例（读脚本全文断言）成本低、防回归强。
- **工作量估算**：M（3 个 TC，1 个脚本文件 + 1 个测试文件修改）。

### 合并验证（Part C）
- 两切片无共享可变量（一为服务进程行为，一为静态脚本文本），交叉影响面为零；仍按 skill 要求跑全量 `pytest upstream/tests`（TC-IBDP-006）。

## 设计偏离登记
- **DA-01**（Phase 2 已登记）：鉴权行为以「部署版契约」为准，仓库侧按契约实现，漂移由部署动作收敛。本 Phase 无新增偏离。