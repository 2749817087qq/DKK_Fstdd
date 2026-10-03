# caveman 语体压缩（跨节点传讯砍 token 60%）+ KG 自动同步器（源码变更→自动 re-index）

<!-- source_hash: 0f7a4598b3345965 -->
<!-- generated_at: 2026-10-03T08:31:56+00:00 -->
<!-- canonical: canonical/proposals/2026-10-03-caveman-kg-sync.yaml -->

## Why

FSTDD 当前两个 token/效率痛点：
1. multihub 任务 scope / release announcement / 跨节点通知 → 长 JSON 或 Markdown，
   每个节点完整拉取 → token 浪费。实际 FSTDD 四阶段里 Phase 1 proposal.yaml 动辄
   几百行，跨节点同步时没必要把"为什么这么设计"的完整论证传过去，只要"做什么 +
   怎么做 + 约束"的最小集合。
2. knowledge-graph.yaml 当前是纯静态 YAML（182 nodes）。今天加了 12 个金融节点，
   但后续每次源码变（比如改 build.md C4、改 understand.md Step 0.5），KG 不会
   自动同步。节点与源码脱节 → Agent 查 KG 拿到过期节点 → 经验库噪声。


## What Changes

- fstdd CLI 新增 `caveman` 子命令 + 独立 Python 库 (fstdd/caveman.py) — compress() + compress_dict() — 任何模块可 import
- Phase 1/2 canon/spec generate 自动追加 caveman 精简版输出
- hub_client.py issue() + complete() 自动附带 scope_min / result_min（调 caveman.compress_dict / compress）
- Gate approve / release announcement 通知消息用 caveman 精简版
- fstdd CLI 新增 `kg sync` 子命令 + KG 扫描/提取/同步模块
- post-commit hook 可选触发 kg sync（.git/hooks/post-commit.fstdd.sample）
- knowledge-graph.yaml node schema 新增 5 个 metadata 字段：first_seen_at / last_synced_at / last_removed_at / deprecated / source_files；edge schema 加 type='co-occurrence' / last_synced_at
- KG re-index 首次全量跑 → dry-run → 验证所有能被正则匹配到的 KG nodes 全部命中（不硬卡 182 全命中）

### New Capabilities

- **caveman-compressor**：FSTDD 跨节点传讯语体压缩器 — ≤200 字 / 砍 token ~60% / 保留关键信息
- **kg-autosync**：FSTDD 知识图谱自动同步器 — 源码变更 → re-index → ADD/UPDATE/DEPRECATE

## Success Criteria

- [ ] caveman
- [ ] kg_sync
