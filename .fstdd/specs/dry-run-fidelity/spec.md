# Spec: dry-run-fidelity

> Change: 2026-10-07-tool-defect-fixes | Auto-generated Human View

## Requirements

### Requirement: `--dry-run` 是**全局注册**的选项（`upstream/fstdd/cli/__init__.py`，help 声明
「预览操作，不实际修改文件系统」），对**所有**子命令可见。凡含写操作的子命令
SHALL 实现该语义：`--dry-run` 为真时 SHALL NOT 产生任何落盘副作用。
该 SHALL 由**契约扫描测试**锚定，使「新命令忘记实现」不再复发。


#### Scenario: SC-001

- **GIVEN** `phase.py::cmd_phase` 全文无 `dry_run` 处理，而 `--dry-run` 由全局父解析器注册（help 声明「不实际修改文件系统」）
- **WHEN** 执行 `fstdd phase advance <change> --dry-run`
- **THEN** SHALL NOT 修改 `.fstdd.yaml`（文件内容与 mtime 均不变）
- **AND** SHALL 在 stdout 打印将被推进的相位（from → to），使预览可见
- **AND** SHALL 以退出码 0 结束（预览不是错误）

#### Scenario: SC-002

- **GIVEN** `phase.py` 已补 dry-run 分支
- **WHEN** 执行 `fstdd phase advance <change>`（不带 `--dry-run`）
- **THEN** SHALL 与修复前的行为逐字节一致（`.fstdd.yaml` 写入内容、退出码、stdout 关键行均不变）
- **AND** 既有 `upstream/tests/commands/test_phase.py` SHALL 全绿

#### Scenario: SC-003

- **GIVEN** 存在两份命令模块样本：一份「有写操作但未处理 dry_run」，一份「已处理」
- **WHEN** 执行契约扫描测试（遍历 `upstream/fstdd/cli/commands/*.py`，凡含写操作者须出现 dry_run 处理）
- **THEN** SHALL 对未处理样本判 FAIL、对已处理样本判 PASS
- **AND** 扫描器 SHALL 同时识别 `getattr(args, "dry_run", False)` 与 `args.dry_run` 两种既有写法
- **AND** 对当前仓库执行时违规数 SHALL 为 0（修复前 `phase.py` 是唯一违规者）
