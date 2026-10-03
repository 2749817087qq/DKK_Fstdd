# Phase Context — 2026-10-03-share-publish-sanitize

> 用途：跨 Session 恢复时的关键上下文（决策 / 关注点 / 产出物）

## Phase 1 UNDERSTAND（completed）

- 目标：修复 `tools/share_experience.py` 经验出站路径「发送前不脱敏」。
- 根因：脱敏只在「导出写盘」，4 个出站拷贝点直读 `experiences/` 原始文件。
- 用户原话：「先修复 publish_to_inbox 的脱敏逻辑」→ 范围覆盖全部出站路径。

## Phase 2 SPEC（completed，Gate 2 于 11:27:01 确认）

- REQ-001..004 / SC-001..012；TC-SOS-001..012；confidence 分布：高 6 / 中 6。
- 关键设计决策（详见 design.md）：
  1. 收口点 = 每个发送函数入口各自 `stage_sanitized()`（堵 silent 直调旁路）
  2. `OUTBOUND_RESIDUAL_RE` 复刻服务端判据，作为可独立断言的第二道防线
  3. `--no-sanitize` 对出站无效（恒 True）
  4. stage 顺带把 frontmatter 改写为 `sanitized: true`
  5. 临时目录 + `finally` 清理，纯标准库
- 用户关注点：4 个拷贝点（proposal 原写「三条」）已在 design 澄清；不扩大替换面（`README.md`/`sqlite3.connect`/`github.com` 不得被替换）。

## Phase 3 BUILD（completed，待 Gate 3）

### 切片记录

| 切片 | 范围 | TC | 新增测试函数 | 状态 |
|------|------|----|--------------|------|
| S1 | stage_sanitized + OUTBOUND_RESIDUAL_RE | TC-SOS-001..007 | 7 | ✅ done（tc_coverage 7/7） |
| S2 | 四出站拷贝点收口 + 零阻塞 | TC-SOS-008..012 | 6 | ✅ done（tc_coverage 5/5） |

### 新增/修改文件

- `tools/share_experience.py`：新增 `OUTBOUND_RESIDUAL_RE`（L165-178）、`stage_sanitized`（L461-497）；
  改造 `publish_via_scp`/`publish_via_inbox`/`publish_via_pr` 为「stage wrapper + `_scp_dir`/`_post_inbox_dir`/`_pr_dir`」；
  `publish()` GitHub 分支 stage 收口。
- `tests/test_share_publish_sanitize.py`：新增（12 TC / 16 item，全绿）。
- 变更工件：`tasks.md`、`slices.md`、`code-structure-delta.md`、`test-report.md`。

### 触发经验

- 新增 EXP-2026-0017（出站未统一收口；security/high）
- 复用 EXP-2026-0016、EXP-2026-0015（复发，occurrences 1→2）、FSTDD005-EXP-20260918-C1/C4/C5/C6、EXP-2026-0013

### 遗留

- 环境缺 coverage/ruff/mypy → 相应检查 SKIPPED
- design.md 行号引用漂移（低）→ DELIVER 修正
- DELIVER 不自动 `git push`；需用户明示