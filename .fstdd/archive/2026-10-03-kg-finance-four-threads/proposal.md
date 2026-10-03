# knowledge-graph 注册金融四条主线 + 8 类金融失败模式节点

<!-- source_hash: a038999e3337922e -->
<!-- generated_at: 2026-10-03T02:06:21+00:00 -->
<!-- canonical: canonical/proposals/2026-10-03-kg-finance-four-threads.yaml -->

## Why

知识图谱 knowledge-graph.yaml 有 2912 行，目前只有 process_deviation 等少数
failure_pattern 节点，零金融领域节点。fstdd-fin SKILL.md 定义了四条主线
（资金流/交易撮合/风险合规/技术底座）+ 8 类金融特有失败模式，
这些知识没有进入跨项目知识图谱。金融项目 Agent 跨 Session / 跨项目
调用 fstdd knowledge merge 时，拿不到金融领域的历史经验。


## What Changes

- knowledge-graph.yaml nodes section 追加 4 条金融主线 domain_thread 节点
- knowledge-graph.yaml nodes section 追加 8 类金融失败模式 failure_pattern 节点 (severity: high)
- 更新 last_merged 时间戳 + graph_version (从 1.0 升到 1.1)

### New Capabilities

- **kg-finance-domain-nodes**：知识图谱包含金融领域 domain_thread + 8 类金融 failure_pattern 节点

## Success Criteria

- [ ] knowledge-graph.yaml nodes section 追加 4 个 domain_thread 节点 (threads_001-004)
- [ ] knowledge-graph.yaml nodes section 追加 8 个 failure_pattern 节点 (fin_fail_001-008)
- [ ] graph_version 1.0 → 1.1, last_merged 更新
- [ ] YAML 合法（yaml.safe_load 不报错）
- [ ] 原有节点一字不变
