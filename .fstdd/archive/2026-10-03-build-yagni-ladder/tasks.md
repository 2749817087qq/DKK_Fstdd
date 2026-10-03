# v3.2.0（候选）任务清单

> change：2026-10-03-build-yagni-ladder
> 目标：BUILD C4 #23 过度工程检查（YAGNI-7 梯子）+ yagni-ladder.md 模板

## 1. build-quality-verification（C4 22 → 23）（P0）

- [ ] 1.1 本地 `.fstdd/skills/build.md` C4 表追加第 23 行「过度工程（Over-Engineering）/ YAGNI-7 梯子」
- [ ] 1.2 本地 `.fstdd/skills/build.md` C4 小节标题「14 类失败模式检查清单」→「23 类失败模式检查清单」
- [ ] 1.3 **upstream** `.fstdd/skills/build.md` 同改（与本地逐字一致，依赖 1.1/1.2 文案定稿）
- [ ] 1.4 `tests/test_finance_content.py`：L1-05 / L1-06 函数改名 `..._c4_exact_23`，断言 22 → 23
- [ ] 1.5 新增 `test_L1_14`：C4 第 23 行双份含 `YAGNI`、覆盖方式含 `YAGNI-7`、动作含「新增功能点」「逐级」（TC-BQV-003 / TC-YLG-004）
- [ ] 1.6 新增 `test_L1_15`：两份 C4 含「23 类失败模式检查清单」且不含旧标题（TC-BQV-004）
- [ ] 1.7 文件 docstring「13 TC」→「17 TC」

## 2. yagni-ladder-gate（模板 + 检查动作）（P0）

- [ ] 2.1 新建 `.fstdd/templates/yagni-ladder.md`（7 级判定表 + 逐级填写说明 + carve-out 豁免清单）
- [ ] 2.2 新建 `upstream/.fstdd/templates/yagni-ladder.md`（与 2.1 内容一致，安装源）
- [ ] 2.3 新增 `test_L1_16`：双份模板存在 + 含 7 级 token + 两份内容一致（TC-YLG-001 / TC-YLG-002）
- [ ] 2.4 新增 `test_L1_17`：模板含 carve-out 4 token + 「永不」（TC-YLG-003）

## 3. 测试与验证（P0）

- [ ] 3.1 `pytest tests/test_finance_content.py` 全绿（17 TC）
- [ ] 3.2 `run_release_validation.py` L1 通过（TC-BQV-006）
- [ ] 3.3 全量 `pytest` 无回归（既有 L1-07 / L1-08 保持绿）

## 4. 交付期 ops（Phase 4，Gate 3 之后）（P0）

- [ ] 4.1 install + verify 三平台（workbuddy / claude-code / trae），grep fstdd-build SKILL.md 含 `#23` 与 `YAGNI`（TC-YLG-005）

<!--
优先级说明：
- P0：阻塞性任务，完成前无法进入下一阶段
- P1：重要任务，应在当前阶段完成
- P2：可延后到后续版本的任务
依赖标注：(依赖 #N.M) 表示此任务依赖第 N 组第 M 个任务完成后才能开始
-->