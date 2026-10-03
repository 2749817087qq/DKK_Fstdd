# FSTDD × 金融：修复 fstdd-fin 资产 + 核心四阶段融合

<!-- source_hash: 6b2c43cb7641ec44 -->
<!-- generated_at: 2026-10-03T01:52:45+00:00 -->
<!-- canonical: canonical/proposals/2026-10-03-finance-integration.yaml -->

## Why

FSTDD 宣称集成了金融领域增强层（fstdd-fin），但自审计发现融合度仅 0.6/5：
(1) fstdd-fin SKILL.md 源文件丢失，主目录 skills/ 不存在，只在 _scratch/ 有孤立副本；
(2) install_workbuddy_skills.py 零 fin 条目，安装链路不接 fstdd-fin；
(3) 核心四阶段 skill（understand/spec/build/deliver）零金融钩子 — 金融红线、
    金融特有测试维度、金融失败模式均未注入通用流程；
(4) config.d/quality.yaml 失败模式库 14 类里零金融条目；
(5) platforms.yaml 未注册 fstdd-fin；
结果：写了一本好手册，但没人读、没人分发、流程里没插。金融项目用通用 skill 走流程 = 裸奔。


## What Changes

- 恢复 fstdd-fin SKILL.md 到 skills/fstdd-fin/SKILL.md（从 _scratch 副本拷）
- install_workbuddy_skills.py 注册 fstdd-fin source 路径 + install 输出
- .fstdd/skills/understand.md 前置钩子：金融系统判定 → 7 红线强制检查（缺失 = Gate 1 不通过）
- .fstdd/skills/build.md 注入金融特有测试维度提示（幂等/精度/对账/降级等 10 维）
- .fstdd/config.d/quality.yaml 失败模式库新增 8 类金融特有模式
- .fstdd/platforms.yaml 注册 fstdd-fin 为第 7 个 skill

### New Capabilities

- **fstdd-fin-skill-registration**：fstdd-fin 从孤立 scratch 回归主 skills/ 目录，安装链路打通，与通用层同级安装
- **finance-quality-failure-modes**：8 类金融特有失败模式（重复扣款/账实不符/静默降级/精度丢失/审计缺口/状态机漏洞/额度穿透/合规遗漏）进入 quality.yaml

### Modified Capabilities

- **understand-phase-finance-redlines**：UNDERSTAND 阶段前置金融红线判定钩子，7 红线缺失 = Gate 1 不通过
- **build-phase-finance-test-dimensions**：BUILD 阶段注入 10 维金融特有测试维度强制覆盖

## Success Criteria

- [ ] skills/fstdd-fin/SKILL.md 存在且内容与 _scratch 副本一致（sha256 匹配）
- [ ] install_workbuddy_skills.py 包含 fstdd-fin source + install 路径
- [ ] .fstdd/skills/understand.md 含金融系统判定 + 7 红线强制检查段落
- [ ] .fstdd/skills/build.md 含 10 维金融测试维度段落
- [ ] .fstdd/config.d/quality.yaml 失败模式库新增 8 类金融条目
- [ ] .fstdd/platforms.yaml 注册 fstdd-fin 为第 7 个 skill
- [ ] 非金融项目四阶段 skill 行为不变（回归验证：用通用项目触发 understand，不出现金融钩子）
- [ ] fstdd validate 通过（skill 文件格式、platforms.yaml 注册、quality.yaml 结构）
