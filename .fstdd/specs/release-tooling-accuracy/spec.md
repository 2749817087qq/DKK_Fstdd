# Spec: release-tooling-accuracy

> Change: 2026-10-06-legacy-debt-cleanup | Auto-generated Human View

## Requirements

### Requirement: 发布检查清单 SHALL 与实际仓库结构一致。`.fstdd/standards/release-and-docs.md` 中关于
「仓库根是否存在 `tests/`」的表述 SHALL 为真；清单给出的全量测试命令 SHALL 覆盖
实际存在的全部测试目录。


#### Scenario: SC-001

- **GIVEN** `.fstdd/standards/release-and-docs.md` 第 29 行含失真表述「仓库根**没有** `tests/`」，而仓库根 `tests/` 实际存在（9 个 `*.py`）
- **WHEN** 阅读该文件的发布检查清单并核对其中关于测试目录的表述
- **THEN** SHALL 使该文件不再含「仓库根没有 tests/」或等义失真表述
- **AND** 清单 SHALL 反映仓库根 `tests/` 的存在
- **AND** 清单给出的全量测试命令 SHALL 同时覆盖 `upstream/tests/` 与仓库根 `tests/`
- **AND** 除该处失真表述外，清单其余条目 SHALL 逐字保持不变

### Requirement: 仓库根 `tests/` 的版本断言 SHALL 从**单一事实源**动态派生，SHALL NOT 硬编码任何版本字面量。
`tests/test_finance_content.py::test_L1_11` SHALL 断言 `.fstdd/version.yaml` 的
`fstdd_version` 与 `.fstdd/config.d/project.yaml` 的 `stdd_version` 一致。


#### Scenario: SC-002

- **GIVEN** `tests/test_finance_content.py:147` 现为 `assert m.group(1) == "3.3.0"`，而 `.fstdd/version.yaml` 的 `fstdd_version` = `3.3.5`
- **WHEN** 在当前版本下执行 `pytest tests/test_finance_content.py::test_L1_11_version_yaml_fstdd_version`
- **THEN** SHALL 通过
- **AND** 该用例 SHALL NOT 再含任何形如 `== "3.3.0"` 的版本字面量断言
- **AND** 该用例 SHALL 校验 `.fstdd/version.yaml` 的 `fstdd_version` 与 `.fstdd/config.d/project.yaml` 的 `stdd_version` 相等

#### Scenario: SC-003

- **GIVEN** `.fstdd/version.yaml` 的 `fstdd_version` 被改为任意合法版本值（形如 `[0-9.]+`），且 `.fstdd/config.d/project.yaml` 的 `stdd_version` 同步为相同值
- **WHEN** 执行 `pytest tests/test_finance_content.py::test_L1_11_version_yaml_fstdd_version`
- **THEN** SHALL 仍然通过（断言不依赖具体版本号）
- **AND** 当两处版本源不一致时，该用例 SHALL 失败并给出可定位的差异信息

#### Scenario: SC-004

- **GIVEN** 编码修复（capability `test-suite-portability`）与版本断言修复均已完成
- **WHEN** 执行 `pytest tests/ -q`（仓库根测试全量）
- **THEN** SHALL 使仓库根 `tests/` 的失败数为 0
- **AND** `tests/test_multi_platform.py` 的 2 例 SHALL 由 `test-suite-portability` 的 SC-002 覆盖并转绿
- **AND** 仓库根 `tests/` 的用例总数 SHALL NOT 因本次改动而减少

#### Scenario: SC-005

- **GIVEN** `tests/test_install_smoke.py` 断言字面量发布 tag `fstdd-v3.1.1`，而 `.fstdd/version.yaml` 的 `fstdd_version` = `3.3.5`（HEAD 的精确 tag = `fstdd-v3.3.5`）
- **WHEN** 在 `git fetch origin --tags` 可达的环境下执行 `pytest tests/test_install_smoke.py::test_L0_01_git_pull_to_tag`
- **THEN** SHALL 通过
- **AND** 仓库根 `tests/` 下 SHALL NOT 再出现形如 `fstdd-v<数字>` 的发布 tag 字面量
- **AND** 期望 tag SHALL 由 `.fstdd/version.yaml` 的 `fstdd_version` 派生为 `fstdd-v<version>`
- **AND** 该用例的断言路径 SHALL 具备宿主隔离覆盖（不依赖真实网络即可验证通过/失败两个分支）
