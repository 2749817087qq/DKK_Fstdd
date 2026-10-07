# Spec: experience-io-contract

> Change: 2026-10-07-tool-defect-fixes | Auto-generated Human View

## Requirements

### Requirement: 经验库索引 `.fstdd/experiences/.experience-index.yaml` 的落盘 SHALL 使用 LF 行尾，
与仓库 `.gitattributes`（`* text=auto eol=lf`）一致；SHALL NOT 依赖运行平台的行尾翻译。
产出文件 SHALL 保持多行结构（SHALL NOT 因禁用翻译而退化成单行）。


#### Scenario: SC-004

- **GIVEN** `.fstdd/experiences/.experience-index.yaml` 由 `_save_index()` 写入
- **WHEN** 执行任一触发索引落盘的命令（如 `fstdd experience verify <id>`）
- **THEN** SHALL 使产出文件的字节流中不含 `\r\n`
- **AND** 产出文件的行数 SHALL 大于 1（不得退化为单行）
- **AND** `tools/verify_eol.py` 的 TC-EOL-003「混合态文件清零」SHALL 通过

#### Scenario: SC-005

- **GIVEN** `_save_index()` 的 `open(...)` 已补 `newline=""`
- **WHEN** 在 Windows（本机）上写入索引
- **THEN** SHALL 显式产生 `\n` 分隔，使文件为多行
- **AND** 同一索引文件在 Windows 与类 Unix 上的字节内容 SHALL 一致（除 schema 数据差异外无行尾差异）

### Requirement: `fstdd experience list --format json` SHALL 对经验库中**任意**条目均可序列化并正常退出；
SHALL NOT 因条目字段含 `date` / `datetime` 对象而抛 `TypeError`。
同一可序列化归一 SHALL 覆盖该模块内**全部** JSON 输出路径，而非仅报错的那一处。


#### Scenario: SC-006

- **GIVEN** 经验库中存在 `exported_at` 以未加引号日期（如 `2026-09-26`）存盘的条目
- **WHEN** 执行 `fstdd experience list --format json`（不加任何过滤）
- **THEN** SHALL 以退出码 0 结束
- **AND** stdout SHALL 为合法 JSON（可被 `json.loads` 解析）
- **AND** SHALL NOT 出现 `TypeError` 或 `not JSON serializable` 字样

#### Scenario: SC-007

- **GIVEN** `experience.py` 内存在多处 `json.dumps` 调用点
- **WHEN** 扫描该模块并统计 `json.dumps` 调用点，逐一核对是否传入了可序列化归一
- **THEN** SHALL 使「未传归一的调用点」集合为空（集合相等断言，非抽检）
- **AND** 对既有可原生序列化的字段，输出 SHALL 与修复前逐字节一致（归一仅在无法原生序列化时生效）
