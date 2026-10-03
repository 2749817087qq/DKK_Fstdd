# Spec: conftest-platform

> Change: 2026-10-03-release-validation-framework | Auto-generated Human View

## Requirements

### Requirement: conftest.py 提供 --platform CLI option，允许指定当前运行平台

#### Scenario: SC-CONF-001-1

- **GIVEN** pytest 命令行，conftest.py 存在并注册 addoption
- **WHEN** pytest tests/ --platform workbuddy
- **THEN** pytest 正常收集测试，无 UnknownOption 错误
- **AND** --platform 参数值写入 pytest.config.option.platform

### Requirement: 平台 marker 注册 — 四平台标记 workbuddy/trae/claude_code/linux

#### Scenario: SC-CONF-002-1

- **GIVEN** conftest.py 有 pytest_configure hook
- **WHEN** pytest 启动收集测试
- **THEN** 四个 marker (platform_workbuddy/platform_trae/platform_claude_code/platform_linux) 注册成功
- **AND** 无 UnknownMarkWarning 或 UnknownMarkError

### Requirement: 平台不匹配的测试自动 skip — 不硬 fail

#### Scenario: SC-CONF-003-1

- **GIVEN** 当前 --platform=trae，测试用 @pytest.mark.platform_workbuddy 标记
- **WHEN** pytest 收集并执行该测试
- **THEN** 该测试被 skip，skip reason 包含 current_platform=trae, required=workbuddy
- **AND** skip 不计入 FAIL，不影响 exit code 判定

### Requirement: env 双 key 兼容 — FSTDD_TOKEN 或 HUB_TOKEN 都能读

#### Scenario: SC-CONF-004-1

- **GIVEN** .heartbeat.env 只有 FSTDD_TOKEN=xxx（无 HUB_TOKEN）
- **WHEN** runner 读取 multihub token
- **THEN** 读到 FSTDD_TOKEN 的值，fallback 机制正常工作

#### Scenario: SC-CONF-004-2

- **GIVEN** .heartbeat.env 只有 HUB_TOKEN=yyy（无 FSTDD_TOKEN）
- **WHEN** runner 读取 multihub token
- **THEN** 读到 HUB_TOKEN 的值

#### Scenario: SC-CONF-004-3

- **GIVEN** .heartbeat.env 两者都有
- **WHEN** runner 读取 multihub token
- **THEN** 优先用 FSTDD_TOKEN（显式优先级）
