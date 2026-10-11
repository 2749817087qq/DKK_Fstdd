# 经验库中心节点同步（自动沉淀 + hub 聚合 + 双模安全）

<!-- source_hash: dd739a12f3a50375 -->
<!-- generated_at: 2026-10-10T22:06:21+00:00 -->
<!-- canonical: canonical/proposals/2026-10-11-experience-center-node-sync.yaml -->

## Why

经验库当前是 per-project / per-agent-platform 的孤立存储。一台机跑 3 个 agent
平台时，每个平台各自存一份经验库，导致多副本、互相漂移（本次
2026-10-10-experience-library-consolidation 已收拾 4 副本 / 23 漂移的残局，但根因
未改，下次还会长）。此外经验收集是触发式 / 手动的：DELIVER 阶段不会自动沉淀经验，
默认 FSTDD_NO_SHARE 还跳过了静默上传，库几乎不增长。


## What Changes

- 扩展 experience extract 的抽取源：在现有 test-report.md 基础上，新增 design-adjustments.md 与 adjudication-log.tsv 两类源；不破坏现有 test-report 抽取路径。
- 新增非交互式自动沉淀入口（auto-deposit），接进 DELIVER 阶段；尊重 FSTDD_NO_SHARE=1 总开关（置位则跳过，延续现有静默上传政策）。
- 新增中心节点同步能力：push 本地经验到第一方 fstdd-hub 的 experiences 托管仓，pull/merge 远端回本地；基于 git（复用现有 server 远端 / hub 托管仓），幂等、可重入（复用 _index_lock / _rebuild_index 的并发安全逻辑）。
- 新增 opt-in 安全档：安全模式下用 cred-relay RSA-3072 OAEP-SHA256/MGF1-SHA256（混合加密：RSA 包裹随机 AES 密钥，AES 加密正文，因 318B 载荷上限）加密经验载荷后再 push；pull 时解密还原。默认（开放）模式不走加密，零密钥即可同步。
- 新增同步冲突策略：同 eid 多节点编辑 → 以 updated_at 末写胜 + 显式冲突日志，不静默覆盖。

## Capabilities

### New Capabilities

- **experience-center-sync**：fstdd experience sync [--push|--pull|--dry-run] [--secure]，对接第一方 fstdd-hub 托管仓，幂等合并本地与远端经验。
- **experience-auto-deposit**：DELIVER 期非交互抽取 + 入库（sources=test-report + design-adjustments + adjudication-log），honor FSTDD_NO_SHARE；产物一律 lifecycle=discovered 待人工 promote。

### Modified Capabilities

- **experience-extract**：抽取源由 test-report.md 扩至 design-adjustments.md + adjudication-log.tsv（C1），保持现有 test-report 路径不变。

## Success Criteria

- [ ] SC1：experience extract / auto-deposit 能从 test-report + design-adjustments + adjudication-log 三类源产出 discovered 草稿（夹具 change 含三类源，断言产出条数 > 0）。
- [ ] SC2：DELIVER 触发自动沉淀；FSTDD_NO_SHARE=1 时跳过（开关两种态各断言一次）。
- [ ] SC3：sync 两节点经第一方 hub 收敛——A push → B pull 后 B 库 == A 库；重跑幂等（无新变更）。
- [ ] SC4：安全档 round-trip——cred-relay RSA-3072 OAEP-SHA256/MGF1-SHA256 混合加密 → 解密内容逐字节一致（仿 selftest 的 T1 / T3 参数敏感性断言）。
- [ ] SC5：默认开放模式无密钥也能完成 sync（能用就好）。
- [ ] SC6：不引入任何第三方外发；_cmd_share_single 禁用状态与注释保持不变（grep 断言）。
