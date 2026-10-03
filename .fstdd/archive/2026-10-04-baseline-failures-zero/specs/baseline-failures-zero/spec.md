# Spec: baseline-failures-zero

> Change: 2026-10-04-baseline-failures-zero | Auto-generated Human View

## Requirements

### Requirement: 项目模板（`.fstdd/templates/**`）与可分发镜像（`upstream/.fstdd/templates/**`）
SHALL 逐文件字节一致，文件集合亦须相等。


#### Scenario: SC-001

- **GIVEN** `.fstdd/templates/` 已含 finance 段，`upstream/.fstdd/templates/` 尚未同步
- **WHEN** 逐文件比较两处 templates 目录的字节内容
- **THEN** SHALL 使 canonical/proposal.yaml、canonical/spec.yaml、test-plan.md 三文件字节相等
- **AND** 两处目录的文件集合 SHALL 相等（无「仅源」「仅镜像」差异）
- **AND** SHALL 不修改模板的语义内容，仅补齐镜像侧缺失段落

### Requirement: 裸 except 吞异常审计活表 SHALL 与扫描器实况零漂移：指纹集合
(file, stmt, handler) 完全相等，同行号偏差 ≤ ±5。


#### Scenario: SC-002

- **GIVEN** 实况扫描得 25 点；归档表 19 点且 guard.py 5 处行号位移超容差
- **WHEN** 以活表路径执行指纹集合比较与行号容差校验
- **THEN** SHALL 使活表 points 与实况扫描的指纹多重集合完全相等
- **AND** 每条表记录的行号与同指纹实况点偏差 SHALL ≤ 5
- **AND** guard.py 5 处行号 SHALL 刷新为 317/381/454/473/1265

#### Scenario: SC-003

- **GIVEN** 活表共 25 点，含 1 条 意外吞错（EA-019）
- **WHEN** 校验分类合法性、理由覆盖率与严重度/响应一致性
- **THEN** SHALL 使每点 classification ∈ {合理容错, 意外吞错, 收窄建议} 且 justification 非空
- **AND** 合理容错点 SHALL response=放行；意外吞错点 SHALL severity∈{p1,p2} 且 response≠放行
- **AND** SHALL 保留至少 1 条「意外吞错 + detection_path=true」
- **AND** SHALL 不改动任何被扫描源码的 except 行为

### Requirement: 显式 `--publish` 失败语义的测试 SHALL 自隔离（hermetic），不依赖运行环境是否
具备 scp 目标的 SSH 别名/凭证。


#### Scenario: SC-004

- **GIVEN** publish() 的优先级 1 为 scp 通道，在具备 fstdd-hub 别名的环境可成功
- **WHEN** 在用例内 monkeypatch publish_via_scp 为失败并令 inbox 指向死端口后调用 main()
- **THEN** SHALL 使 main() 返回 1（显式命令失败→非零）
- **AND** 隔离 SHALL 只作用于测试，不改变 publish() 的生产三档降级逻辑
- **AND** 静默路径（silent_share）零阻塞语义 SHALL 不受影响

### Requirement: 全仓 naive 时间戳 SHALL 清零：L1 值层无「含时刻却无时区」的值，L2 源层无未豁免的
无参 naive 调用，且豁免清单每条可在源码定位。


#### Scenario: SC-005

- **GIVEN** notices-authenticity-gate 的 8 处时间值缺时区后缀
- **WHEN** 执行 `tools/check_timestamps.py --repo .` 全仓扫描
- **THEN** SHALL 使 naive 计数为 0
- **AND** 扫描 SHALL 为只读（前后文件哈希不变）
- **AND** 扫描范围 SHALL 显式列出且含 changes / canonical / templates

#### Scenario: SC-006

- **GIVEN** 新增 3 条 category=identifier 豁免（hub_client / share_experience / verify_notices）
- **WHEN** 执行豁免清单自检 find_stale_exemptions
- **THEN** SHALL 使失效豁免数为 0（每条豁免均可定位）
- **AND** 每条豁免 SHALL 附非空理由
- **AND** 豁免类别 SHALL 覆盖 pure_date/identifier/year_extract/comparison 四类

#### Scenario: SC-007

- **GIVEN** tools/heartbeat.py 与 tools/fstdd003_daily_share.py 产出的时间戳原为 naive
- **WHEN** 扫描这两个文件的 L2 源层
- **THEN** SHALL 使其代码行不再被判为 naive 产出（含 timezone 感知标记）
- **AND** 改动 SHALL 保留原墙钟显示语义（本地时区 aware），不改变日志读取习惯

#### Scenario: SC-008

- **GIVEN** 4 组修复全部落地
- **WHEN** 执行全量 pytest 与四个自检脚本
- **THEN** SHALL 得到 pytest 0 failed 与四个自检脚本全绿
- **AND** 基线失败数 SHALL 由 6 降为 0
- **AND** SHALL 不产生新的 skip 以掩盖失败
