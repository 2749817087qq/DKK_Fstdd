# Spec: validation-runner

> Change: 2026-10-03-release-validation-framework | Auto-generated Human View

## Requirements

### Requirement: 单入口参数解析 — --platform / --task-id / --skip / --e2e / --skip-report

#### Scenario: SC-RUN-001-1

- **GIVEN** python tests/run_release_validation.py --help
- **WHEN** 执行 help
- **THEN** help 输出包含全部 5 个参数说明

#### Scenario: SC-RUN-001-2

- **GIVEN** --platform workbuddy
- **WHEN** 启动 runner
- **THEN** 正确解析为 platform='workbuddy'

#### Scenario: SC-RUN-001-3

- **GIVEN** --skip l2,l3
- **WHEN** 启动 runner
- **THEN** classes_to_run 排除 L2 和 L3

### Requirement: 依赖链串行执行 — 前一类 FAIL 立即停，后一类不跑

#### Scenario: SC-RUN-002-1

- **GIVEN** L1 静态校验有意 fail（修改源码让 regex 匹配不到）
- **WHEN** 完整跑 runner
- **THEN** L1 FAIL 后 runner 停止，L2/L3/L4 不被执行
- **AND** stdout 显示 'STOPPED at L1 due to FAIL'
- **AND** exit code = 1

### Requirement: 颜色编码输出 — 🟢🟡🔴⚪🔵 正确出现在 stdout

#### Scenario: SC-RUN-003-1

- **GIVEN** 某个 TC PASS
- **WHEN** runner 输出
- **THEN** 该 TC 行前缀 🟢

#### Scenario: SC-RUN-003-2

- **GIVEN** 某个 TC SKIP
- **WHEN** runner 输出
- **THEN** 该 TC 行前缀 ⚪ + skip reason

### Requirement: 最终结构化 JSON — tests/last_report.json 包含完整报告

#### Scenario: SC-RUN-004

- **GIVEN** runner 执行完毕（不管 PASS 还是 FAIL）
- **WHEN** 读 tests/last_report.json
- **THEN** JSON 存在且含以下顶层字段: node_id, platform, timestamp, overall, classes{duration,status,tcs:[{id,name,status,evidence}]}
- **AND** overall ∈ {'PASS', 'FAIL', 'PARTIAL'}
- **AND** timestamp ISO 8601

### Requirement: 自动 multihub 回传 — L6 claim release task → complete + result JSON

#### Scenario: SC-RUN-005-1

- **GIVEN** --skip-report 未指定，.heartbeat.env 正确
- **WHEN** runner 跑完所有指定 classes
- **THEN** 自动 claim 并 complete release multihub task
- **AND** result 字段是完整 JSON（last_report.json 内容）
- **AND** claim 和 complete 都返回 200/201

#### Scenario: SC-RUN-005-2

- **GIVEN** --skip-report 指定
- **WHEN** runner 跑完
- **THEN** 跳过 multihub 回传，只生成本地 last_report.json

#### Scenario: SC-RUN-005-3

- **GIVEN** multihub 连通性失败
- **WHEN** runner 尝试 auto-report
- **THEN** 捕获 HTTP exception，打印指导消息，exit code 不因此增加
- **AND** 不吞掉之前已有的 FAIL exit code

### Requirement: L2/L3 UI 钩子 — 当 runner 无 UI 时 gracefully SKIP

#### Scenario: SC-RUN-006

- **GIVEN** runner 在无 UI 环境运行（Linux headless）且没有 --e2e
- **WHEN** 执行到 L2
- **THEN** L2 全部 SKIP，reason='no UI available'
- **AND** 不硬 FAIL，不阻塞后续 L4/L6
