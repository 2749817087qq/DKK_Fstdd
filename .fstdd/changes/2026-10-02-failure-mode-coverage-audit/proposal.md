# 审计 14 类失败模式在 skill + CLI guard 里的实际落地

<!-- source_hash: dd5fc3ed7cd479c7 -->
<!-- generated_at: 2026-10-02T07:45:04+00:00 -->
<!-- canonical: canonical/proposals/2026-10-02-failure-mode-coverage-audit.yaml -->

## Why

FSTDD V3.0 声称 14 类失败模式检查（幻觉调用/过度信任 LLM/prompt 注入/记忆污染/上下文窗溢出/工具参数漂移/凭证泄露/权限绕过/并发竞态/路径遍历/跨会话残留/输出截断/格式错/循环依赖等）是核心卖点。
但审计发现：
1. CLI guard 是门禁（阻断非 BUILD/DELIVER 阶段编辑），不是检测（扫描 14 类问题）
2. skill build.md 里有失败模式检查表，但需确认每一类是否都有对应检测手段
3. 部分类别可能只有文字引用、缺少实际可执行的检测脚本或 hook
4. knowledge-graph.yaml 有 failure_pattern 节点（KG-094 等），但未验证是否覆盖全部 14 类


## What Changes

- 逐类审计 14 类失败模式的实际覆盖（CLI 检测 / skill 引导 / hook 拦截）
- 对审计发现的缺口补齐检测手段（优先 hook，其次 CLI detect 子命令）
- 产出审计报告 coverage-report.md（每类的覆盖证据）

### New Capabilities

- **failure-mode-coverage-report**：14 类失败模式的实际覆盖审计报告，每类标注 CLI / skill / hook 覆盖状态 + 缺口

### Modified Capabilities

- **fstdd-guard**：审计后可能新增检测钩子到 guard（如果发现门禁覆盖不足）
- **skills-build**：审计后可能补全 skill build.md 的失败模式检查项（如果发现文字与实装不一致）

## Success Criteria

- [ ] 14 类失败模式每一类都有明确覆盖证据（CLI 检测 / skill 引导 / hook 拦截 至少一项）
- [ ] 产出 coverage-report.md，每类标注覆盖状态 + 证据文件行号
- [ ] 如果发现缺口，补齐后 re-audit，确保全部 PASS
