# Spec: installation-identity

> Change: 2026-10-21-installation-id-prefix | Human View
> 修订: 2026-10-22（与 canonical/specs/code/installation-identity.yaml 同步）

## Requirements

### Requirement: `fstdd init` SHALL 在 `.fstdd/version.yaml` 中写入合法形状的 `installation_id`，且 SHALL NOT 丢弃既有字段

#### Scenario: SC-IID-001

- **GIVEN** 在空目录执行 `fstdd init`
- **WHEN** init 完成，读取 `.fstdd/version.yaml`
- **THEN** SHALL 含 `installation_id`，值匹配 `^[A-Z0-9]{2,8}-[0-9A-F]{8}$`
- **AND** HEX 段 SHALL 由 `secrets.token_hex(4).upper()` 生成（8 位大写十六进制）
- **AND** PREFIX SHALL 由项目名派生，或由 `--prefix` 覆盖
- **AND** 若文件已存在且含其它字段（如 `stdd_version`），写入后这些字段 SHALL 保持不变

#### Scenario: SC-IID-002

- **GIVEN** 执行 `fstdd init --prefix MYPROJ`
- **WHEN** init 完成，读取 `installation_id`
- **THEN** PREFIX SHALL 为 `MYPROJ`，完整值形如 `MYPROJ-A1B2C3D4`
- **AND** `--prefix` 值 SHALL 先 `strip().upper()`；满足 `^[A-Z0-9]{2,8}$` 才采纳
- **AND** 不合法时 SHALL 向 **stderr** 告警并回落项目名派生，SHALL NOT 中止 init
  （原设计为 exit 1，评审后改为降级：可选参数不该让 init 全盘失败）

#### Scenario: SC-IID-003

- **GIVEN** 项目目录名为 `my-project`（含连字符）
- **WHEN** init 缺省无 `--prefix`
- **THEN** PREFIX SHALL 取 `MYPR`（剥掉非 `[A-Z0-9]` 字符后取前 4 位）
- **AND** 派生结果 SHALL 恒满足 `^[A-Z0-9]{2,8}$` —— 否则 ID 变三段（`MY-P-0803ADF7`），
  打穿 `split('-')[-1]` 取序号的既有假设
- **AND** 项目名为纯中文（清洗后不足 2 位）时，PREFIX SHALL 回落 `FSTDD`

### Requirement: `installation_id` SHALL 只在首次 init 生成一次，后续 upgrade / init --force / experience add 均不得覆盖

#### Scenario: SC-IID-004

- **GIVEN** 项目已有 `installation_id: WBCC-0803ADF7`
- **WHEN** 执行 `fstdd upgrade`（其唯一写口是 `upgrade._write_version_yaml`）
- **THEN** `installation_id` SHALL 保持不变
- **AND** `_write_version_yaml` SHALL 采用「读既有 → 合并 → 写」语义，而非整体覆盖
- **AND** version.yaml 中未在该次写入参数里出现的既有字段 SHALL 一并存活
  （防止下一个新增字段重蹈 installation_id 被抹掉的覆辙）

#### Scenario: SC-IID-005

- **GIVEN** init 过程到达 `_post_init_self_check`
- **WHEN** 自检运行
- **THEN** SHALL 输出 `installation_id: ✅ <实际生效值>`（取自 version.yaml 且形状合法）
- **AND** 拿不到合法值时 SHALL 输出 `installation_id: ⚠️ 未写入（新经验将使用旧格式 EXP-YYYY-NNNN）`
- **AND** SHALL NOT 在未生效时打印 ✅（原实现按「字段存在」判 ✅，坏值也打 ✅，属恒真断言）

### Requirement: 写入口径 SHALL 与读取口径一致 —— 读取端拒收的值，写入端不得保留或打印为已生效

#### Scenario: SC-IID-006

- **GIVEN** version.yaml 中 `installation_id` 为非法形状（如 `../etc/passwd`、`WBCC`、空串）
- **WHEN** 执行 `fstdd init`
- **THEN** SHALL 向 **stderr** 告警并重新生成合法值覆盖
- **AND** 覆盖时 SHALL 保留 version.yaml 的其它字段
- **AND** 生成后 `experience._next_id` SHALL 立即产出带该前缀的 ID

#### Scenario: SC-IID-007

- **GIVEN** version.yaml 存在但 YAML 不可解析
- **WHEN** 执行 `fstdd init`
- **THEN** SHALL NOT 写入任何内容（文件字节保持不变），并 SHALL 向 **stderr** 告警提示先修复
- **AND** `_ensure_installation_id` SHALL 返回 None，自检随之报 `⚠️ 未写入`
