# Guard 相位门增加路径作用域：消除 ACTIVE_CHANGE 只读相位导致的全项目冻结

<!-- source_hash: 2752f7f14a65ec53 -->
<!-- generated_at: 2026-09-25T04:24:08+00:00 -->
<!-- canonical: canonical/proposals/2026-09-25-guard-phase-path-scope.yaml -->

## Why

STDD Guard 的相位门是全项目粒度：当 ACTIVE_CHANGE 指向处于 understand/spec
相位的 change 时，该工作区内一切 Edit/Write（包括与该 change 无关的文件、
agent 自身 memory 日志）全部被拦截（exit 2）。这导致「ACTIVE_CHANGE 漂移
= 阶段劫持」：一个停在只读相位的 change 会冻结整个工作区的其它工作。


## What Changes

- 相位门增加路径作用域：非可编辑相位时，只拦截 change 声明范围（scope）内的文件；范围外文件降级为警告（warn-only）或直接放行。
- 明确 change scope 的声明来源（proposal what_changes / tasks.md 文件清单 / change 目录本身），无声明时的默认行为需定义（建议维持现状全拦，避免静默放开）。
- 排查并消除本机旧修订 guard.py 副本（patchtest、FSTDD004 内嵌仓等 40,082 B 无豁免逻辑版本）导致的豁免面不一致。
- 补充回归测试：只读相位 + 范围外文件编辑 ⇒ 放行/警告；范围内文件 ⇒ 拦截；GATE token / .fstdd.yaml 硬阻断在两种情形下均不受影响。

### New Capabilities

- **phase-gate-path-scope**：相位门按 change 声明的文件作用域判定拦截范围，非全局

### Modified Capabilities

- **guard-check-phase-gate**：cmd_guard_check 的相位判定从全项目粒度改为作用域粒度；两道硬阻断（GATE token / .fstdd.yaml 确认字段）保持全项目粒度不变

## Success Criteria

- [ ] 只读相位下，编辑 change 作用域外的项目文件不再被拦截（或有明确 warn-only 输出）
- [ ] 只读相位下，编辑 change 作用域内的文件仍被拦截（exit 2）
- [ ] GATE token 写入、.fstdd.yaml 确认字段篡改在任何相位、任何路径下仍被硬阻断（exit 2）
- [ ] 既有 pytest tests/commands/test_guard.py 与 tests/test_guard_silent_except.py 全绿，新增作用域用例覆盖上述三类情形
- [ ] YAML-first 流程产物放行（:735）行为不变
