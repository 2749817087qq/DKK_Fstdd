# FSTDD v3.1.1 大规模跨节点测试框架 — 8 大类 / 47 TC / 颜色编码 / 派发矩阵

<!-- source_hash: 08fe46fd5c6dac45 -->
<!-- generated_at: 2026-10-03T04:27:42+00:00 -->
<!-- canonical: canonical/proposals/2026-10-03-release-validation-framework.yaml -->

## Why

FSTDD v3.1.1 commit 836b394 push 前，我跳过了 FSTDD Phase 2-3 流程，
直接手写测试代码 + commit + push + 派发模糊 scope 的 multihub 任务。
问题根因：没有预定义测试体系，想到什么写什么，违反 AGENTS.md 里
"enforce_stdd: true" 的强制约束。
具体表现：
  - 测试正则误匹配（39 行 != 22 行 C4）
  - .heartbeat.env key 名混淆（FSTDD_ 前缀 vs HUB_ 前缀）
  - pytest mark 未注册（claude-code 连字符 vs claude_code 下划线）
  - multihub 任务 scope 里没写可执行命令，节点无从下手
  - 我自己 commit 了 4 个文件，全部被 revert 干净


## What Changes

- 创建 tests/conftest.py — pytest 共享配置：--platform CLI + 自动 skip 不匹配平台
- 创建 tests/test_finance_content.py — 13 TC 纯静态校验（L1）
- 创建 tests/test_install_smoke.py — 5 TC 安装冒烟（L0）
- 创建 tests/run_release_validation.py — 8 大类单入口 runner + 自动 multihub 回传
- 修复 .heartbeat.env 读取 — FSTDD_TOKEN/FSTDD_NODE_ID/FSTDD_MULTIHUB_URL 主键兼容
- 修复 pytest platform marker 命名一致性 — conftest.py 和 test_*.py 统一用 claude_code

### New Capabilities

- **release-validation-framework**：FSTDD 跨节点 release 测试体系：8 大类 / 47 TC / 单入口 runner / 自动 multihub 反馈

## Success Criteria

- [ ] conftest.py --platform 参数注册成功，无 UnknownMarkWarning
- [ ] test_finance_content.py 所有 TC PASS（静态内容确实对得上）
- [ ] test_install_smoke.py 所有平台 PASS（install + verify exit 0）
- [ ] run_release_validation.py 完整跑通 → OVERALL: PASS
- [ ] runner 自动 multihub complete 成功（result 字段含完整 JSON report）
- [ ] multihub 新派发的任务 scope 里有可执行命令（不是模糊描述）
- [ ] commit + push 后，其他节点 pull 后直接能跑（不依赖额外环境）
