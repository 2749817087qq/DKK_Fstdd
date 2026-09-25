# 自动化执行记忆：FSTDD 产物周汇总报告 (1ac52506)

## 2026-09-21 00:30 执行（首跑 / W38）
- 报告已生成：`D:\FSTDD003\docs\FSTDD003-weekly-report-2026-W38.md`
- 统计窗口：2026-09-14 ~ 2026-09-20（ISO W38，周一 00:30 跑，汇总过去 7 个自然日）。
- 结果：本周新增 skill（去重唯一名）**20** 个（skills-archive 11 项 + artifacts/skills 10 项，install-github-skill 两端重复去重）；经验文档 **27** 篇（FSTDD003-EXP-20260917*~20260920*），severity high10/medium11/low1/info1/未标4。
- 关键判定：skill 目录 mtime 全为 09-17（FSTDD003 前缀批量应用日），无法区分"本周新产出"与"本周前缀化"；09-21 的 `FSTDD003-memory-detail-sink` 超窗口，计入 W39。报告已如实注明此 caveats。
- 方法：用 Python 脚本批量抽 SKILL.md frontmatter summary + 经验文档 现象/根因/改善 三段；未触外网。
- 六大主题归纳：① 静默失败(≥7篇) ② 测试盲区(≥6) ③ 归档合并缺陷(4) ④ 环境残留(≥5) ⑤ 协作安全(3) ⑥ 规范冲突/标准可证伪(≥5)。
- 建议沉淀 skill：`notice-auth-verify`(高优,安全)、`silent-success-guard`、`red-replay`、`proxy_guard`(已存在待回传)、`archive-mirror`(已落地)、`recv-reply-reconcile`(已落地)。

## 周期规律（供下次参考）
- 每周一 00:30 触发；文件名用报告日所在 ISO 周，但统计窗口是「上个完整 7 天」（周一前推 7 天 ~ 昨日）。
- 例：09-21(周一) → 窗口 09-14~09-20 → 文件名 W38（因 09-14~09-20 属 ISO W38，09-21 起为 W39）。
- skill 判定靠 mtime，经验文档靠文件名日期；两者都需落在窗口内才计入。
