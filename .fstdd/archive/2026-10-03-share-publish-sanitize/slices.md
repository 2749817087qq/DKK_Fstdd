# 切片执行计划 — 2026-10-03-share-publish-sanitize

> mode: standard | capability: share-outbound-sanitize | 12 TC

## Dependency Graph Summary

- 零依赖节点：`share-outbound-sanitize.stage_sanitized`（新函数，无上游依赖）
- 依赖链：`stage_sanitized` → 4 个出站拷贝点 → `silent_share` E2E
- 深度：3 | 关键路径：S1 → S2 | cycles：无

## 五步分析结果

| 切片 | 覆盖 REQ/SC | 风险分 | 工作量 | 并行组 | Rationale |
|------|-------------|--------|--------|--------|-----------|
| S1 | REQ-001(SC-001..005) / REQ-002(SC-006..007) | 🟢 3 | M（7 TC，1 源文件 + 1 测试文件） | 1（串行前置） | 脱敏原语是全部出站路径的地基，必须先绿；命中 EXP-C4（第二道防线可观测）与 EXP-2026-0013（声明/实现一致） |
| S2 | REQ-003(SC-008..011) / REQ-004(SC-012) | 🟡 4 | M（5 TC，1 源文件） | 1（依赖 S1） | 4 个拷贝点分属不同通道（scp/GitHub/inbox/PR），跨模块交互多；命中 EXP-C1（静默失败无消费者）与 EXP-C6（凭证外泄） |

> 风险分 ≥ 4 → S2 依赖 S1 产出，独立成切片；两切片串行，无并行合并验证。

## 排序

1. **S1（P0）** — `stage_sanitized` + `OUTBOUND_RESIDUAL_RE` + 7 TC（TC-SOS-001..007）
2. **S2（P0）** — 四拷贝点收口 + 5 TC（TC-SOS-008..012）

## 实现目标（S1 产出物）

- `tools/share_experience.py`：模块常量 `OUTBOUND_RESIDUAL_RE`、函数 `stage_sanitized()`
- `tests/test_share_publish_sanitize.py`：TC-SOS-001..007

## 实现目标（S2 产出物）

- `tools/share_experience.py`：`publish_via_inbox` / `publish_via_scp` / `publish`(GitHub 分支) / `publish_via_pr` 收口
- `tests/test_share_publish_sanitize.py`：TC-SOS-008..012