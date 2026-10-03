# Spec: yagni-ladder-gate

> Change: 2026-10-03-build-yagni-ladder | Auto-generated Human View

## Requirements

### Requirement: 新增 YAGNI-7 梯子填表模板 SHALL 存在，且含 7 级全部判定问题文本（顺序不可乱）

#### Scenario: SC-YLG-001

- **GIVEN** `.fstdd/templates/yagni-ladder.md`
- **WHEN** 读取模板内容
- **THEN** SHALL 依次含 7 级关键词：真需要 / 本仓已有 / 标准库 / 平台原生 / 已装依赖 / 一行 / 最小实现
- **AND** SHALL 说明「首个成立的级别即为答案，逐级自问」

#### Scenario: SC-YLG-002

- **GIVEN** `upstream/.fstdd/templates/yagni-ladder.md` 与 `.fstdd/templates/yagni-ladder.md`
- **WHEN** 比对两份模板
- **THEN** SHALL 均存在且内容一致

### Requirement: 模板 SHALL 含 carve-out 豁免清单，明确安全类事项永不因 YAGNI 跳过

#### Scenario: SC-YLG-003

- **GIVEN** yagni-ladder.md 模板
- **WHEN** 读取 carve-out 章节
- **THEN** SHALL 含 4 项豁免：安全 / 信任边界校验 / 防数据丢失的错误处理 / 无障碍
- **AND** SHALL 显式声明这 4 项永不跳过（永不因 YAGNI 删减）

### Requirement: BUILD C4 #23 的检查动作 SHALL 强制对每个新增功能点逐级回答 7 阶梯子

#### Scenario: SC-YLG-004

- **GIVEN** build.md 的 C4 表第 23 行「BUILD 检查动作」列
- **WHEN** 读取检查动作文本
- **THEN** SHALL 描述：对每个新增功能点/新文件/新依赖逐级回答 7 阶梯子，首个成立级别即答案

### Requirement: 上游变更安装后，三平台 SKILL.md 的 C4 SHALL 含 #23 与 YAGNI

#### Scenario: SC-YLG-005

- **GIVEN** install_workbuddy_skills.py --platform <p>（p ∈ workbuddy/claude-code/trae）
- **WHEN** 安装并读取目标平台 fstdd-build SKILL.md
- **THEN** SHALL 含 '#23' 与 'YAGNI'
