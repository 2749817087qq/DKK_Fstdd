# Spec: static-content-checks

> Change: 2026-10-03-release-validation-framework | Auto-generated Human View

## Requirements

### Requirement: L1-01: skills/fstdd-fin/SKILL.md 文件存在且 > 1500 字符

#### Scenario: SC-L1-001

- **GIVEN** 仓库根目录下 skills/fstdd-fin/SKILL.md
- **WHEN** 静态检查文件存在
- **THEN** assert path.exists() AND assert file.stat().st_size > 1500

### Requirement: L1-02: SKILL.md 包含全部 7 红线关键词

#### Scenario: SC-L1-002

- **GIVEN** SKILL.md 内容读入内存
- **WHEN** 逐一检查 7 红线关键词
- **THEN** 7 个 assert 全 PASS
- **AND** 关键词清单: 交易准确性/幂等性/审计不可篡改/账实相符/降级不静默/数据合规/无硬编码

### Requirement: L1-03: understand.md 含 Step 0.5 + 金融判定

#### Scenario: SC-L1-003

- **GIVEN** .fstdd/skills/understand.md 内容读入
- **WHEN** 搜索 Step 0.5 和 金融 关键词
- **THEN** assert 'Step 0.5' in content AND assert '金融' in content

### Requirement: L1-04: upstream understand.md 同步含 Step 0.5

#### Scenario: SC-L1-004

- **GIVEN** upstream/.fstdd/skills/understand.md 内容读入
- **WHEN** 搜索 Step 0.5
- **THEN** assert 存在

### Requirement: L1-05: build.md C4 section 精确 22 行（含 header + 22 table rows）

#### Scenario: SC-L1-005

- **GIVEN** .fstdd/skills/build.md 内容读入
- **WHEN** 用正则提取 '## C4' 到 '## C5' 之间的 table 行数
- **THEN** 精确等于 22（不是 14，不是 39）
- **AND** 提取方法: 找 | 开头的 table row，排除 header 和 separator

### Requirement: L1-06: upstream build.md C4 同步 22 行

#### Scenario: SC-L1-006

- **GIVEN** upstream/.fstdd/skills/build.md
- **WHEN** 同 L1-05 方法
- **THEN** 精确 22 行

### Requirement: L1-07: B2.5 section 含 10 维金融测试关键词

#### Scenario: SC-L1-007

- **GIVEN** build.md 内容
- **WHEN** 搜索 B2.5 section 下的 10 个关键词
- **THEN** 全部命中: 幂等/对账/精度/时区/降级/一致/安全/审计/合规/恢复

### Requirement: L1-08: 8 类金融失败模式关键词存在

#### Scenario: SC-L1-008

- **GIVEN** build.md C4 table
- **WHEN** 搜索 8 类金融失败模式
- **THEN** 全部命中: 重复扣款/账实不符/静默降级/精度丢失/审计缺口/状态机漏洞/额度穿透/合规遗漏

### Requirement: L1-09: KG FIN- 前缀节点 ≥ 12

#### Scenario: SC-L1-009

- **GIVEN** knowledge-graph.yaml 解析为 dict
- **WHEN** 遍历 nodes 列表，统计 id 以 'FIN-' 开头的节点
- **THEN** count >= 12

### Requirement: L1-10: KG graph_version >= 1.1

#### Scenario: SC-L1-010

- **GIVEN** knowledge-graph.yaml 解析
- **WHEN** 读取 graph_version 字段
- **THEN** assert float(version) >= 1.1

### Requirement: L1-11: version.yaml fstdd_version = 3.1.1

#### Scenario: SC-L1-011

- **GIVEN** .fstdd/version.yaml 解析
- **WHEN** 读取 fstdd_version
- **THEN** assert version == '3.1.1'

### Requirement: L1-12: version.yaml feedback_protocol.mandatory = true

#### Scenario: SC-L1-012

- **GIVEN** version.yaml 解析
- **WHEN** 读取 feedback_protocol.mandatory
- **THEN** assert mandatory is True

### Requirement: L1-13: 3 平台 install 命令字段齐全

#### Scenario: SC-L1-013

- **GIVEN** version.yaml install.install_by_platform 解析
- **WHEN** 检查 workbuddy/claude_code/trae 三个 key 都存在
- **THEN** 全部存在且各自有 install 命令数组
