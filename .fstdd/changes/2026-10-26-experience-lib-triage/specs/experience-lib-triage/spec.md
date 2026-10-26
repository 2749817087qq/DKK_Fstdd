# Capability: experience-lib-triage

## MODIFIED Requirements

### Requirement: frontmatter 解析取最后一个非空块

#### Scenario: 单 frontmatter 文件解析不变

- **GIVEN** 一个经验文件只含一个 `---...---` frontmatter 块
- **WHEN** 调用 `_load_experience(path)`
- **THEN** 系统 SHALL 返回与当前实现一致的字段字典
- **AND** 不得因解析逻辑变化而丢字段

#### Scenario: 双重包裹 frontmatter 取内层

- **GIVEN** 一个经验文件含外层 `---\ninner ---\n...inner ---\n---` 双重包裹
- **WHEN** 调用 `_load_experience(path)`
- **THEN** 系统 SHALL 返回内层 frontmatter 的字段（非空字段）
- **AND** 外层占位字段不得覆盖内层

#### Scenario: 113 条经验 before/after 一致或更全

- **GIVEN** 本仓 `.fstdd/experiences/` 下全部 113 条经验文件
- **WHEN** 用修复后的 `_load_experience` 重新解析
- **THEN** 每条经验的字段数 SHALL >= 修复前
- **AND** 不得有任一经验的字段数减少

### Requirement: ci check-failures TC 覆盖扫描 upstream/tests/

#### Scenario: TC-ID 只在 upstream/tests/ 有实现

- **GIVEN** 一个 change 的 test-plan 声明了 TC-ELT-004
- **WHEN** 该 TC 的测试函数只存在于 `upstream/tests/`
- **THEN** `ci check-failures` SHALL 报告 TC 覆盖 1/1（而非 0/1）
- **AND** 不得因扫描路径缺失而报假红

#### Scenario: 双目录扫描不误判

- **GIVEN** `upstream/tests/` 下有 `test_foo.py` 但不含 TC-ID 引用
- **WHEN** `ci check-failures` 扫描
- **THEN** 该文件 SHALL 不被计入 TC 覆盖
- **AND** 只认 docstring 或注释里的 TC-ID 标记

### Requirement: YAML 回写保护手写文件

#### Scenario: 检测手写 YAML

- **GIVEN** 一个 YAML 文件含 `#` 注释行或 `key: |` block scalar
- **WHEN** 调用 `_is_handwritten_yaml(path)`
- **THEN** SHALL 返回 True
- **AND** 纯机器生成 YAML（无注释、无 block scalar）返回 False

#### Scenario: 拦截 yaml.dump 整体回写

- **GIVEN** `version.yaml` 被判定为手写 YAML
- **WHEN** 尝试 `yaml.dump(data, open(path,'w'))`
- **THEN** SHALL 抛出 `HandwrittenYAMLProtection` 或改用正则局部替换
- **AND** 注释行与 block scalar 格式保留

### Requirement: experience list/stats 读无写副作用

#### Scenario: list 后索引 mtime 不变

- **GIVEN** `.experience-index.yaml` 已存在
- **WHEN** 执行 `fstdd experience list`
- **THEN** `.experience-index.yaml` 的 mtime SHALL 不变
- **AND** 输出基于现有索引（不从磁盘重建）

#### Scenario: 索引缺失时提示 reindex

- **GIVEN** `.experience-index.yaml` 不存在
- **WHEN** 执行 `fstdd experience list`
- **THEN** SHALL 打印 warning 提示跑 `fstdd experience reindex`
- **AND** 不自动重建索引（不产生写副作用）

### Requirement: collect_local 水位线过滤

#### Scenario: 跳过已传经验

- **GIVEN** 审计日志含 3 条 `result: success` 的 experience_id
- **WHEN** 调用 `collect_local()`
- **THEN** SHALL 只返回不在已传列表中的经验
- **AND** 已传的 3 条不在返回结果中

#### Scenario: --full 强制全量

- **GIVEN** 审计日志含 3 条已传记录
- **WHEN** 调用 `collect_local(full=True)`
- **THEN** SHALL 返回全部经验（含已传的）
- **AND** 不读水位线

#### Scenario: 水位线缺失回退全量

- **GIVEN** 审计日志为空或不存在
- **WHEN** 调用 `collect_local()`
- **THEN** SHALL 返回全部经验（回退到全量）
- **AND** 不漏传
