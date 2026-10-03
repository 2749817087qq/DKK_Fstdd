# upstream 内核同步: understand.md Step 0.5 + build.md C4 22 行 table

<!-- source_hash: cc9ebb76e5ecb17b -->
<!-- generated_at: 2026-10-03T02:06:20+00:00 -->
<!-- canonical: canonical/proposals/2026-10-03-upstream-finance-sync.yaml -->

## Why

上两个 change (2026-10-03-finance-integration + 2026-10-03-finance-failure-modes)
在本地 .fstdd/skills/understand.md 加了 Step 0.5 金融钩子，在 build.md C4 加了
22 行失败模式 table (14 通用 + 8 金融)。但 upstream 内核的 .fstdd/skills/
understand.md 和 build.md 里这两处变更都没有，形成 fork 漂移。
下次 upstream sync 时本地改动会被覆盖，或者 upstream 用户拿不到金融钩子。


## What Changes

- upstream .fstdd/skills/build.md C4 section 追加 22 行失败模式 table（14 通用 + 8 金融）+ 检查结果说明
- upstream .fstdd/skills/understand.md Step 0 之后追加 Step 0.5 金融系统判定 + 7 红线强制检查

### New Capabilities

- **upstream-finance-hooks-synced**：upstream skills/understand.md 和 build.md 同步了本地金融钩子，所有平台安装自带金融增强

### Modified Capabilities

- **upstream-build-c4-checklist**：upstream build.md C4 从 3 行通用描述扩展为 22 行可执行 table

## Success Criteria

- [ ] upstream/.fstdd/skills/build.md C4 section 包含标题 + 22 行 table + 检查结果说明
- [ ] upstream/.fstdd/skills/understand.md Step 0 之后包含 Step 0.5 金融判定 + 7 红线
- [ ] 原有 upstream build.md C4 标题和 understand.md Step 0-1 一字不变
- [ ] 本地 .fstdd/skills/understand.md 和 build.md 内容与 upstream 一致
