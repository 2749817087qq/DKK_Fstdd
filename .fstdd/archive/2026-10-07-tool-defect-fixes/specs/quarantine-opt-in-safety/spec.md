# Spec: quarantine-opt-in-safety

> Change: 2026-10-07-tool-defect-fixes | Auto-generated Human View

## Requirements

### Requirement: `tools/verify_notices.py` 的**默认**运行 SHALL NOT 移动或删除任何文件；
隔离（`shutil.move` 到 `tools/_quarantine/`）SHALL 仅在显式传入 `--quarantine` 时发生。
默认路径 SHALL 仍以**可观测**方式呈现命中项（显式告警 + 非零退出码 + JSON 字段），
使「不再破坏」不以「不再可见」为代价。


#### Scenario: SC-013

- **GIVEN** 某目录存在凭证形状命中的文件，且**未**传 `--quarantine`
- **WHEN** 执行 `python tools/verify_notices.py <dir>`（默认）
- **THEN** SHALL NOT 移动、重命名或删除该目录内任何文件
- **AND** 该目录的文件清单与各文件内容 SHALL 与运行前逐字节一致
- **AND** `tools/_quarantine/` SHALL NOT 新增条目

#### Scenario: SC-014

- **GIVEN** 某目录存在凭证形状命中的文件，且**传入** `--quarantine`
- **WHEN** 执行 `python tools/verify_notices.py <dir> --quarantine`
- **THEN** SHALL 将命中文件移入 `tools/_quarantine/`（恢复修复前的行为）
- **AND** 隔离记录 SHALL 仅含文件名 / md5 前 12 位 / 规则名 / 时间，SHALL NOT 含凭证字面值

#### Scenario: SC-015

- **GIVEN** 默认模式（未传 `--quarantine`）下存在命中项
- **WHEN** 执行 `python tools/verify_notices.py <dir> --json`
- **THEN** SHALL 在 JSON 顶层新增 `would_quarantine` 键，列出「若加 `--quarantine` 会被移走」的条目
- **AND** 既有四键 `results` / `quarantined` / `warnings` / `exit_code` SHALL 保持存在且语义不变
- **AND** 默认模式下 `quarantined` SHALL 为空数组（因为确实没有移动任何东西）
- **AND** 存在命中项时退出码 SHALL 非 0（保留告警强度）
