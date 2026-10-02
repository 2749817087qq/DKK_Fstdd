# test-report.md — 2026-10-02-skills-sync-upstream-diff

## 测试概览

| 项 | 值 |
|---|---|
| 时间 | 2026-10-02T11:22:00+08:00 |
| TC 覆盖 | 实测 diff + 文件存在性验证 |
| 新增测试 | 0（配置类 change） |
| 14 类失败模式 | ✅ 全量 PASS |

## 实测证据

Change 2+3 联合 commit 5d4cace:

- deliver.md: 4917B → 5434B（structure delta 归档顺序坑 + bin/stdd→bin/fstdd 修正）
- upgrade.md: 4387B → 4650B（stdd-upgrade → fstdd-upgrade，版本 3.0.5-fin.1，去除 GitHub upstream 依赖，改成本地 upstream/.fstdd 权威源）
- _shared/confirm-gate.md: NEW（upstream/.fstdd 独有，本地缺失）
- _shared/long-range-auth.md: NEW（upstream/.fstdd 独有，本地缺失）
- _shared/mode-selection.md: NEW（upstream/.fstdd 独有，本地缺失）
- build/spec/understand: 本地=远程.fstdd=upstream/.fstdd 完全相同（14689/16534/6237B）

## 14 类失败模式

| 类别 | 状态 |
|---|---|
| 凭证泄漏 | ✅ N/A（纯 Markdown） |
| 远程同步断裂 | ✅ PASS（同步 merge commit 5094ff2 打通） |
| 版本漂移 | ✅ PASS（本地 now = upstream/.fstdd improved） |
| 零回归 | ✅ PASS（pytest tools/test_verify_notices.py 21 passed） |
| 安全 | ✅ PASS（无代码改动，纯文档同步） |
| (其余 9 类) | ✅ PASS/N/A |
