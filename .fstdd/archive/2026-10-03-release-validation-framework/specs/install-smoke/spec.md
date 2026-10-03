# Spec: install-smoke

> Change: 2026-10-03-release-validation-framework | Auto-generated Human View

## Requirements

### Requirement: L0-01: git pull 拉到 fstdd-v3.1.1 tag

#### Scenario: SC-L0-001

- **GIVEN** 当前在 FSTDD 工作目录，remote 配置正确
- **WHEN** 执行 git fetch origin --tags; git describe --tags --exact-match HEAD
- **THEN** 输出 fstdd-v3.1.1 或包含该 tag
- **AND** exit 0

### Requirement: L0-02: install_workbuddy_skills.py --platform <p> → exit 0, 7/7 OK

#### Scenario: SC-L0-002

- **GIVEN** --platform 参数传入有效平台
- **WHEN** 执行 python tools/install_workbuddy_skills.py --platform <p>
- **THEN** exit code = 0
- **AND** stdout 包含 '7/7 OK' 或类似成功标记
- **AND** skill 目标目录下存在 fstdd-fin/SKILL.md

### Requirement: L0-03: verify_workbuddy_skills.py → exit 0, 所有 skill PASS

#### Scenario: SC-L0-003

- **GIVEN** install 已完成
- **WHEN** 执行 python tools/verify_workbuddy_skills.py --platform <p>
- **THEN** exit code = 0
- **AND** stdout 无 FAIL 行

### Requirement: L0-04: node heartbeat — 本节点出现在 multihub online nodes 列表

#### Scenario: SC-L0-004

- **GIVEN** .heartbeat.env 有正确的 FSTDD_NODE_ID
- **WHEN** 执行 hub_client.py 列出 online nodes
- **THEN** 本节点 id 在列表中
- **AND** multihub 连通性确认

### Requirement: L0-05: multihub ping → exit 0

#### Scenario: SC-L0-005

- **GIVEN** .heartbeat.env 有正确的 multihub URL + token
- **WHEN** 执行 hub_client.py ping
- **THEN** exit code = 0
- **AND** response status 200
