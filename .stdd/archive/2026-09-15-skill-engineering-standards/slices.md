# 切片规划 — 2026-09-15-skill-engineering-standards

> 模式：standard｜Capability：3 个（2 new + 1 modified）

## 切片清单

### Slice 1 — 运行时冒烟（skill-runtime-verification）

| 项 | 内容 |
|---|---|
| **实现** | `verify_workbuddy_skills.py` 增加 `smoke_test()`；支持 `STDD_CLI` 覆盖以便故障注入 |
| **对应 TC** | TC-SES-001、TC-SES-002、TC-SES-007 |
| **依赖** | 无 |
| **风险** | 冒烟耗时增加；临时目录需确保清理 |

### Slice 2 — 元数据治理（skill-metadata-governance）

| 项 | 内容 |
|---|---|
| **实现** | 新增 `check_skill_metadata.py`（扫描 / `--fix` / `--revert`）；改造 install 脚本写入 version 与 license |
| **对应 TC** | TC-SES-003、TC-SES-004、TC-SES-005 |
| **依赖** | 无（与 Slice 1 可并行，但同改 tools/ 故串行） |
| **风险** | 写入用户既有 31 个 skill —— 由全量备份 + 正文哈希断言兜底 |

### Slice 3 — 发布清单（skill-release-checklist）

| 项 | 内容 |
|---|---|
| **实现** | 新增 `docs/SKILL_RELEASE_CHECKLIST.md` |
| **对应 TC** | TC-SES-006 |
| **依赖** | Slice 1、2（清单需引用其命令） |
| **风险** | 无 |

## 执行顺序

```
Slice 1（冒烟） → Slice 2（元数据） → Slice 3（清单）
```

串行：三者同在 `tools/` 或引用其命令，并行会产生状态耦合。

## 偏离记录

| # | 偏离 | 原因 | 影响 |
|---|---|---|---|
| DA-1 | version 缺失数由 23 修正为 31 | 严格口径：不把 `stdd_version`（上游版本）计入 skill 自身版本 | 提案/测试/报告数字同步更正 |
| DA-2 | TC-SES-003 改为构造样本验证 | 原断言依赖「--fix 前」的一次性状态，修复后不再可复现 | 用例改为随时可重复 |
| DA-3 | TC-SES-004 改为复合断言 | 原断言假设总有文件待修复，已合规时误报 | 增加幂等性与备份一致性验证 |
| DA-4 | 测试运行位置改为安装位置 DKKstdd | 在 stdd-repo 副本跑 verify 会因 STDD_SRC 不同产生反向误判 | 源码检查与运行验证分离 |
