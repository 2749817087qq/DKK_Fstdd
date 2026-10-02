# 自动化执行记忆：FSTDD 产物周汇总报告 (1ac52506)

## 2026-09-21 00:30 执行（首跑 / W38）
- 报告已生成：`D:\FSTDD003\docs\FSTDD003-weekly-report-2026-W38.md`
- 统计窗口：2026-09-14 ~ 2026-09-20（ISO W38，周一 00:30 跑，汇总过去 7 个自然日）。
- 结果：本周新增 skill（去重唯一名）**20** 个（skills-archive 11 项 + artifacts/skills 10 项，install-github-skill 两端重复去重）；经验文档 **27** 篇（FSTDD003-EXP-20260917*~20260920*），severity high10/medium11/low1/info1/未标4。
- 关键判定：skill 目录 mtime 全为 09-17（FSTDD003 前缀批量应用日），无法区分"本周新产出"与"本周前缀化"；09-21 的 `FSTDD003-memory-detail-sink` 超窗口，计入 W39。报告已如实注明此 caveats。
- 方法：用 Python 脚本批量抽 SKILL.md frontmatter summary + 经验文档 现象/根因/改善 三段；未触外网。
- 六大主题归纳：① 静默失败(≥7篇) ② 测试盲区(≥6) ③ 归档合并缺陷(4) ④ 环境残留(≥5) ⑤ 协作安全(3) ⑥ 规范冲突/标准可证伪(≥5)。
- 建议沉淀 skill：`notice-auth-verify`(高优,安全)、`silent-success-guard`、`red-replay`、`proxy_guard`(已存在待回传)、`archive-mirror`(已落地)、`recv-reply-reconcile`(已落地)。

## 2026-09-28 15:47 执行（次跑 / W39）
- 报告已生成：`D:\FSTDD003\docs\FSTDD003-weekly-report-2026-W39.md`
- 统计窗口：2026-09-21 ~ 2026-09-27（ISO W39，周一 00:30 跑，汇总过去 7 个自然日）。
- 结果：本周新增 skill（去重唯一名）**4** 个（全部来自 skills-archive，artifacts/skills 无新增）；经验文档 **22** 篇（FSTDD003-EXP-20260921*~20260927*），severity high **17** / medium **5**。
- 关键判定：skill mtime 全在窗口内（09-21~09-23），可区分「本周新产出」。W39 问题高度集中在 FSTDD CLI 工具链（82%），与 W38 的分散主题形成对比。
- 核心模式：7/22 篇描述「参数被解析但不被消费」同一族问题（--dry-run 不 dry、--type 被忽略、target_phase 被忽略等），占全部 32%。这是系统性架构缺陷，非偶发。
- 方法：Python 脚本批量扫 skills mtime + 经验文档 frontmatter/title；读取全部 22 篇经验文档正文提取「问题/根因/改善」三段；未触外网。
- 五大主题归纳：① 参数静默忽略(7篇) ② 测试假绿/假红(3) ③ 工具口径漂移(3) ④ Windows 文件系统(2) ⑤ 对账/履约盲区(2)。
- 建议沉淀 skill：`fstdd-parameter-audit`(最高优,根治7篇同族问题)、`mutation-harness-selftest`、`scp-diff-check`、`windows-fs-safety`、`fstdd-ci-workaround`。
- 环比：问题数 ↓19%（27→22），high 占比 ↑40pp（37%→77%）。问题更聚焦但更严重。

## 周期规律（供下次参考）
- 每周一 00:30 触发；文件名用窗口起止日所在的 ISO 周。
- 例：09-21(周一) → 窗口 09-14~09-20 → 文件名 W38；09-28(周一) → 窗口 09-21~09-27 → 文件名 W39。
- skill 判定靠 mtime，经验文档靠文件名日期；两者都需落在窗口内才计入。
