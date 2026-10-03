# BUILD C4 #23 过度工程检查（YAGNI-7 决策梯子）+ 模板

<!-- source_hash: c03f156ed345b74e -->
<!-- generated_at: 2026-10-03T09:36:00+00:00 -->
<!-- canonical: canonical/proposals/2026-10-03-build-yagni-ladder.yaml -->

## Why

BUILD 阶段 C4 现有 22 类失败模式（14 通用 + 8 金融）全部属于「做错了什么」：
幻觉调用 / 注入 / 精度丢失 / 合规遗漏…。缺「做多了什么」这一整类。

AI Agent（含 FSTDD 自身执行编码时）系统性偏向过度工程：用户要一个小功能，
Agent 默认新增文件 + 抽象层 + 第三方依赖，而不是先问「真的需要写吗」。
FSTDD 四阶段目前只有隐式「别过度工程化」这类软要求，BUILD C4 无显式检查项
→ 无法逐项打勾、无法在 test-report.md 留证、无客观通过/不通过判据。


## What Changes

- build.md C4 新增第 23 行「过度工程（Over-Engineering）」，覆盖方式标 `YAGNI-7 梯子`，检查动作 = 每个新增功能点/新文件/新依赖逐级回答 7 阶梯子，首个成立级别即答案；同时把 C4 小节标题「14 类失败模式检查清单」修正为「23 类失败模式检查清单」
- 新增 YAGNI-7 梯子填表模板 `yagni-ladder.md`（7 级判定表 + 逐级填写说明 + carve-out 豁免清单），供 change 在 BUILD 时对每个新增功能点填答并写入 test-report.md
- 同步静态内容断言：tests/test_finance_content.py L1-05 / L1-06 由「精确 22 行」改为「精确 23 行」；新增 1 条断言确认 build.md C4 #23 含 YAGNI 关键词
- 上游变更后重跑 install + verify（platforms.yaml 三平台 workbuddy/claude-code/trae），确认安装后的 SKILL.md C4 含 #23

### New Capabilities

- **yagni-ladder-gate**：BUILD C4 强制对每个新增功能点执行 YAGNI-7 决策梯子判定，首个成立级别即答案，并留证于 test-report.md

### Modified Capabilities

- **build-quality-verification**：C4 失败模式检查从 22 类扩展为 23 类（新增「过度工程」类）

## Success Criteria

- [ ] `upstream/.fstdd/skills/build.md` C4 section 精确 23 data row，编号含 #23 且该行关键词含 'YAGNI'
- [ ] `.fstdd/skills/build.md` C4 section 精确 23 data row，内容与 upstream 一致
- [ ] `upstream/.fstdd/templates/yagni-ladder.md` 与 `.fstdd/templates/yagni-ladder.md` 均存在，包含 7 级全部问题文本与 carve-out 清单
- [ ] `tests/test_finance_content.py` L1-05/L1-06 断言 23；`pytest tests/test_finance_content.py` L1 全绿（无回归）
- [ ] install 后三平台（workbuddy/claude-code/trae）SKILL.md 的 C4 含 '#23' 与 'YAGNI'
- [ ] 本 change git diff 不含任何运行时 Python/CLI 逻辑变更（仅 .md 模板/skill 文本 + tests 断言）
