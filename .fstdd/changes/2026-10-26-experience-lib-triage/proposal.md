# 经验库诊断与框架缺陷修复 —— 从 113 条经验提取 5 项可执行变更

<!-- source_hash: 2855552258d60cbb -->
<!-- generated_at: 2026-10-26T13:39:47+00:00 -->
<!-- canonical: canonical/proposals/2026-10-26-experience-lib-triage.yaml -->

## Why

本仓经验库已积累 113 条经验（含 45 条 high + 2 条 critical），知识图谱 377 节点。
这些经验指出了框架的多类系统性缺陷，但尚未转化为修复变更。本 change 从中提取
5 项可执行变更，按优先级排序，作为 v3.5.0 的输入。

核心问题（按严重度排序）：
1. experience.py 的 _load_experience 只取第一个 frontmatter 块，双重包裹条目字段全丢
   → kg sync 恒 0 匹配，图谱实际靠 K 节点手动合并（EXP-2026-0041 旁证）
2. ci check-failures 的 TC 覆盖检查硬编码只扫 project_root/tests，不扫 upstream/tests/
   → 落在 upstream/tests/ 的 change 必然报 TC 覆盖 0/N 假红（EXP-2026-0041）
3. yaml.dump 整体回写带注释头/block scalar 的手写 YAML，丢注释+退化+重排键
   → 336 行文件缩成 235 行（EXP-2026-0043）
4. experience list/stats 会重写被跟踪的 .experience-index.yaml
   → 诊断后须 git checkout 回退（已知坑，多次命中）
5. 静默回传 collect_local() 无「已分享」水位线，每次 --silent 重传全库 113 条


## What Changes

- 修 `_load_experience`（experience.py:408）的双 frontmatter 块解析缺陷。
当前只取第一个 `---...---` 块，双重包裹的条目（含 `---\ninner\n---` 的）
其字段全丢。改为取**最后一个** frontmatter 块（或合并所有块）。
同时修经验 ID 与图谱节点 ID 的映射关系，使 `kg sync` 能自动匹配。

- 修 `ci check-failures` 的 TC 覆盖检查扫描路径。当前硬编码 `project_root/tests`，
不扫 `upstream/tests/`。改为同时扫描两个目录（与全量门禁 `pytest tests upstream/tests`
的路径一致）。EXP-2026-0041 直接证据。

- 修 YAML 回写保护：对带注释头/block scalar 的手写 YAML 文件（version.yaml /
project.yaml / canonical/*.yaml），禁止用 `yaml.dump` 整体回写。改为
原子替换（读→改→写时保留注释与格式）或加 `yaml.dump` 前置检查（检测到
注释头/block scalar 则拒绝整体回写，改用 sed/正则局部替换）。EXP-2026-0043 直接证据。

- 修 `experience list` / `stats` 重写 `.experience-index.yaml` 的行为。
读命令不应有写副作用。改为：list/stats 只读不写索引；索引重建改为
显式子命令 `experience reindex`。或至少在读操作结束后 git checkout 回退。

- 给 `collect_local()` 加「已分享」水位线过滤。当前每次 --silent 重传全库
113 条。改为：读审计日志最近一次成功回传的 experience_id 列表，跳过已传的。
或加 `--full` 标志强制全量重传。属行为变更，需 D哥 确认。


### Modified Capabilities

- **experience-io-contract**：经验库 I/O 契约修复：frontmatter 解析 + 索引无写副作用 + YAML 回写保护
- **ci-coverage-accuracy**：CI TC 覆盖检查扫描路径修正：覆盖 upstream/tests/
- **share-watermark**：静默回传水位线过滤：跳过已传经验

## Success Criteria

- [ ] SC1 `kg sync` 能自动匹配经验文件 ID 到图谱节点（0 匹配 → >0 匹配）
- [ ] SC2 `ci check-failures` 的 TC 覆盖检查同时扫 tests/ 和 upstream/tests/
- [ ] SC3 yaml.dump 回写手写 YAML 时保留注释与 block scalar（或拒绝整体回写）
- [ ] SC4 `experience list` / `stats` 不重写 .experience-index.yaml（读无写副作用）
- [ ] SC5 `collect_local()` 跳过已传经验（水位线过滤），`--full` 强制全量
- [ ] SC6 全量门禁 0 failed（tests/ + upstream/tests/）
- [ ] SC7 既有 113 条经验的字段提取结果 before/after 一致或更全
