# Spec: caveman-compressor

> Change: 2026-10-03-caveman-kg-sync | Auto-generated Human View

## Requirements

### Requirement: caveman 必须是独立 Python 库（fstdd/caveman.py），任何模块可直接 import，不绑定 hub_client 或 canon.py

#### Scenario: CAVE-SC-001

- **GIVEN** fstdd caveman.py 已实现 compress() + compress_dict()
- **WHEN** 任何模块执行 `from fstdd.caveman import compress, compress_dict`
- **THEN** SHALL 成功导入，无循环 import；无 hub_client / canon 依赖

#### Scenario: CAVE-SC-002

- **GIVEN** compress(text, max_chars=200) 被调用
- **WHEN** 输入是纯文本/Markdown 字符串
- **THEN** SHALL 返回 ≤max_chars 长度的字符串

#### Scenario: CAVE-SC-003

- **GIVEN** compress_dict(d, keep_keys=[...]) 被调用
- **WHEN** 输入是 dict（如 multihub task scope）
- **THEN** SHALL 返回只保留 keep_keys 中 key 的 dict，值不变

### Requirement: 压缩按 proposal §implementation.algorithm 执行：field_weights + trim_rules + budget_allocation

#### Scenario: CAVE-SC-004

- **GIVEN** 输入文本含 motivation 段落（背景故事）
- **WHEN** compress() 执行
- **THEN** SHALL 直接砍 motivation（weight=1, max_chars=0），输出里无 motivation 文本

#### Scenario: CAVE-SC-005

- **GIVEN** 输入含中文修饰词（如'在 Windows 环境下使用 PowerShell'）
- **WHEN** compress() 执行
- **THEN** SHALL 应用中文修饰词 regex 砍去'的'前后各 2 字 → 'Win + PS5'

#### Scenario: CAVE-SC-006

- **GIVEN** 输入含英文停用词（the/a/an/is/are/in/on...）
- **WHEN** compress() 执行
- **THEN** SHALL 移除停用词

#### Scenario: CAVE-SC-007

- **GIVEN** 单字段（如 summary）超过分配的 max_chars
- **WHEN** compress() 执行
- **THEN** SHALL 先应用 trim_rules 砍；还超 → 砍最低 weight 字段

#### Scenario: CAVE-SC-008

- **GIVEN** 总输出超过 max_chars 预算且 mandatory_fields 不全
- **WHEN** compress() 执行 final check
- **THEN** SHALL 截断优先级倒转：先砍 summary（weight=10）让 constraints（weight=5）进来，而不是砍 constraints

### Requirement: 压缩结果必须包含 mandatory_fields（做什么/怎么做/约束/deadline）；缺失则失败或倒转截断优先级

#### Scenario: CAVE-SC-009

- **GIVEN** compress() 生成的输出 ≤max_chars 但缺 constraints
- **WHEN** final check 执行
- **THEN** SHALL 截断优先级倒转 → 砍 summary 腾出空间 → constraints 补进来

#### Scenario: CAVE-SC-010

- **GIVEN** 输入不含 deadline（非必需）
- **WHEN** compress() 执行
- **THEN** SHALL 跳过 deadline 校验，不影响其他字段

#### Scenario: CAVE-SC-011

- **GIVEN** 输入是 dict（compress_dict）
- **WHEN** default_keep_keys 被应用
- **THEN** SHALL 包含 task_id + idempotency_key（multihub 必需字段）

### Requirement: compress() 必须 deterministic，同输入多次调用返回完全相同输出

#### Scenario: CAVE-SC-012

- **GIVEN** 同一段输入文本
- **WHEN** 连续调用 compress() 3 次
- **THEN** SHALL 三次输出字符级完全一致（可用于 git diff）

### Requirement: fstdd CLI 新增 caveman 子命令

#### Scenario: CAVE-SC-013

- **GIVEN** 命令行 `fstdd caveman proposal.yaml`
- **WHEN** 执行
- **THEN** SHALL 输出压缩文本到 stdout（或 --out 指定路径）

#### Scenario: CAVE-SC-014

- **GIVEN** 命令行 `fstdd caveman --max 100 text.txt`
- **WHEN** 执行
- **THEN** SHALL 用 100 字预算（默认 200）

#### Scenario: CAVE-SC-015

- **GIVEN** 输入文件不存在
- **WHEN** 执行
- **THEN** SHALL exit code non-zero + stderr 提示

### Requirement: canon/spec generate + hub_client issue/complete 自动附带 caveman 输出

#### Scenario: CAVE-SC-016

- **GIVEN** fstdd canon generate 完成 proposal.yaml
- **WHEN** canon.py 内置 caveman 钩子
- **THEN** SHALL 自动在同目录追加 caveman_summary.txt（≤200 字）

#### Scenario: CAVE-SC-017

- **GIVEN** hub_client.issue(scope=dict) 被调用
- **WHEN** issue() 内置 caveman 钩子
- **THEN** SHALL scope dict 自动附带 scope_min 键（compress_dict 结果）

#### Scenario: CAVE-SC-018

- **GIVEN** hub_client.complete(result=long_string) 被调用且 result 长度 >200
- **WHEN** complete() 内置 caveman 钩子
- **THEN** SHALL result dict 自动附带 result_min 键（compress 结果）；result ≤200 则不加

### Requirement: trim_rules 必须精确实现 proposal 中定义的 4 条规则

#### Scenario: CAVE-SC-019

- **GIVEN** 输入含中文修饰词'在 Windows 环境下使用 PowerShell 处理用户要求更新到最新版的请求'
- **WHEN** compress() 执行中文修饰词 regex
- **THEN** SHALL 输出类似'Win + PS5: 更新请求处理'

#### Scenario: CAVE-SC-020

- **GIVEN** 输入含英文停用词'The implementation is in the file for testing'
- **WHEN** compress() 执行停用词移除
- **THEN** SHALL 输出类似'implementation file testing'

#### Scenario: CAVE-SC-021

- **GIVEN** 输入含重复命令（如'git pull ... git pull ...'）
- **WHEN** compress() 执行重复合并
- **THEN** SHALL 只保留一次

### Requirement: multihub 实测 scope_min vs full scope token 差 ≥ 50%

#### Scenario: CAVE-SC-022

- **GIVEN** 用 release-validation-framework 的 task scope 做基准
- **WHEN** compress_dict() 生成 scope_min
- **THEN** SHALL token_count(scope_min) ≤ token_count(full_scope) * 0.5
