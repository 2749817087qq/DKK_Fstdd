# Spec: test-teardown-resilience

> Change: 2026-10-12-test-teardown-resilience | Auto-generated Human View

## Requirements

### Requirement: 韧性层 —— 测试进程内的删除原语在被沙箱守卫打断（SystemExit）时不中断收尾，且该打断可见、可计数；真实异常不得被吞

#### Scenario: SC-001

- **GIVEN** 测试进程已通过 conftest 包装 os.remove / os.unlink / shutil.rmtree（安装点 pytest_configure）
- **WHEN** 被包装的原实现抛出 SystemExit（模拟守卫拦截）
- **THEN** wrapper SHALL 捕获该 SystemExit 并将其降级为告警，SHALL NOT 向上抛出
- **AND** 调用方（pytest fixture teardown 或框架代码）SHALL 继续执行后续收尾步骤

#### Scenario: SC-002

- **GIVEN** wrapper 捕获了一次 SystemExit
- **WHEN** 检查测试会话输出
- **THEN** SHALL 出现包含被捕获删除目标路径的 warning，且会话结束 SHALL 输出捕获次数汇总（不得静默）
- **AND** 汇总行 SHALL 便于与真实回归区分（含固定前缀，如 [teardown-resilience]）

#### Scenario: SC-003

- **GIVEN** 被包装的原实现抛出真实异常（非 SystemExit，如 PermissionError）
- **WHEN** 调用被包装的删除原语
- **THEN** wrapper SHALL 原样抛出该异常，使调用方/测试照常失败（SHALL NOT 吞掉）
- **AND** wrapper SHALL NOT 使用 `except Exception` 或 `except BaseException` 宽捕获

### Requirement: 规避层 —— 测试期的临时目录落在仓库外的中立目录，减少命中守卫触发条件

#### Scenario: SC-004

- **GIVEN** pytest 会话启动（pytest_configure 已执行）
- **WHEN** 读取测试进程内的 TMP / TEMP / TMPDIR
- **THEN** SHALL 指向一个存在于仓库之外的目录，且该目录 SHALL 可写
- **AND** 该设置 SHALL 仅在测试进程内生效，SHALL NOT 写入仓库配置或影响生产

### Requirement: 症状末端加固 —— 受影响测试对「目录已存在」具备鲁棒性

#### Scenario: SC-005

- **GIVEN** tests/test_verify_notices_default_safe.py 的目标临时目录已存在（上一轮残留）
- **WHEN** 运行该测试文件的任一用例
- **THEN** SHALL 不抛 FileExistsError，测试 SHALL 继续按其断言执行

### Requirement: 可判性 —— 全量门禁结果对守卫是否触发不敏感

#### Scenario: SC-006

- **GIVEN** 守卫未触发
- **WHEN** 连续运行 3 次全量 `pytest tests -q -p no:cacheprovider`（每次全新 basetemp）
- **THEN** 3 次的 failed 数与 errors 数 SHALL 完全一致
- **AND** 在守卫未触发的前提下，failed 与 errors SHALL 均为 0

### Requirement: 范围边界 —— 本 change 不触碰 vendored 内核

#### Scenario: SC-007

- **GIVEN** 本 change 的全部改动
- **WHEN** 执行 `git diff --name-only`（相对本 change 起点）
- **THEN** SHALL NOT 包含 `upstream/` 下的任何文件
- **AND** 改动 SHALL 限于 `tests/` 与 `.fstdd/changes/2026-10-12-test-teardown-resilience/`
