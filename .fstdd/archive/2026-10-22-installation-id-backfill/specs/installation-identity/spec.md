# Spec: installation-identity

> Change: 2026-10-21-installation-id-prefix | Auto-generated Human View

## Requirements

### Requirement: `fstdd init` SHALL 在 `.fstdd/version.yaml` 中写入合法形状的 `installation_id`， 且 SHALL NOT 丢弃该文件中的既有字段。

#### Scenario: SC-IID-001

- **GIVEN** 在空目录执行 `fstdd init`
- **WHEN** init 完成，读取 `.fstdd/version.yaml`
- **THEN** SHALL 含 `installation_id` 字段，值匹配 `^[A-Z0-9]{2,8}-[0-9A-F]{8}$`
- **AND** HEX 段 SHALL 由 `secrets.token_hex(4).upper()` 生成（8 位大写十六进制）
- **AND** PREFIX SHALL 由项目名派生，或由 `--prefix` 参数覆盖
- **AND** 若 version.yaml 已存在且含其它字段（如 `stdd_version`），写入后这些字段 SHALL 保持不变

#### Scenario: SC-IID-002

- **GIVEN** 执行 `fstdd init --prefix MYPROJ`
- **WHEN** init 完成，读取 `installation_id`
- **THEN** PREFIX SHALL 为 `MYPROJ`，完整值形如 `MYPROJ-A1B2C3D4`
- **AND** `--prefix` 值 SHALL 先 `strip().upper()`；满足 `^[A-Z0-9]{2,8}$` 才采纳
- **AND** 不合法时 SHALL 向 **stderr** 告警并回落项目名派生，SHALL NOT 中止 init（原设计为 exit 1，评审后改为降级：init 的其它步骤不应因一个可选参数失败）

#### Scenario: SC-IID-003

- **GIVEN** 项目目录名为 `my-project`（含连字符）
- **WHEN** init 缺省无 --prefix
- **THEN** PREFIX SHALL 取 `MYPR`（剥掉非 `[A-Z0-9]` 字符后取前 4 位）
- **AND** 派生结果 SHALL 恒满足 `^[A-Z0-9]{2,8}$` —— 否则 ID 会变成三段（`MY-P-0803ADF7`），打穿 `split('-')[-1]` 取序号的既有假设
- **AND** 项目名为纯中文（清洗后不足 2 位）时，PREFIX SHALL 回落 `FSTDD`
- **AND** 修订记录：本 SC 原写「含连字符保留 → `MY-P`」，与「ID 恒为两段」冲突；2026-10-22 评审后改为清洗语义，代码与规格同时对齐

### Requirement: `installation_id` SHALL 只在首次 init 时生成一次；后续 `fstdd upgrade`、 `fstdd init --force`、`experience add` 均 SHALL NOT 覆盖或重新生成。

#### Scenario: SC-IID-004

- **GIVEN** 项目已有 `installation_id: WBCC-0803ADF7`
- **WHEN** 执行 `fstdd upgrade`（其唯一写口是 `upgrade._write_version_yaml`）
- **THEN** `installation_id` SHALL 保持不变
- **AND** `_write_version_yaml` SHALL 采用「读既有 → 合并 → 写」语义，而非整体覆盖
- **AND** version.yaml 中**未在该次写入参数里出现**的既有字段 SHALL 一并存活（防止下一个新增字段重蹈 installation_id 覆辙）

#### Scenario: SC-IID-005

- **GIVEN** init 过程到达 `_post_init_self_check`
- **WHEN** 自检运行
- **THEN** SHALL 输出 `installation_id: ✅ <实际生效值>`（值取自 version.yaml 且形状合法）
- **AND** 拿不到合法值时 SHALL 输出 `installation_id: ⚠️ 未写入（新经验将使用旧格式 EXP-YYYY-NNNN）`
- **AND** SHALL NOT 在未生效时打印 ✅（原实现按「字段存在」判 ✅，字段坏值也打 ✅，属恒真断言）

### Requirement: `installation_id` 的**写入口径** SHALL 与**读取口径**一致：读取端拒收的值， 写入端不得保留或打印为已生效。

#### Scenario: SC-IID-006

- **GIVEN** version.yaml 中 `installation_id` 为非法形状（如 `../etc/passwd`、`WBCC`）或非字符串（如 `[A, B]`）
- **WHEN** 执行 `fstdd init`
- **THEN** SHALL 向 **stderr** 告警并重新生成合法值覆盖
- **AND** 覆盖时 SHALL 保留 version.yaml 的其它字段
- **AND** 生成后 `experience._next_id` SHALL 立即产出带该前缀的 ID（写进去的值必须真被读取端采用）
- **AND** **空串 / 缺失** 视为「未设置」的等价写法（模板默认值、手工清空），SHALL NOT 告警，直接生成

#### Scenario: SC-IID-007

- **GIVEN** version.yaml 存在但 YAML 不可解析
- **WHEN** 执行 `fstdd init`
- **THEN** SHALL NOT 写入任何内容（文件字节保持不变），并 SHALL 向 **stderr** 告警提示先修复
- **AND** `_ensure_installation_id` SHALL 返回 None，自检随之报 `⚠️ 未写入`

### Requirement: 已初始化但缺 `installation_id` 的项目 SHALL 能通过 `fstdd installation-id` 补齐身份； 该命令 SHALL 只做这一件事（零副作用），且写入 SHALL 保留 `.fstdd/version.yaml` 的 可读文本形态（注释头、块标量标记、行尾），SHALL NOT 用 `yaml.dump` 整体回写。

#### Scenario: SC-IID-008

- **GIVEN** 当前目录**没有** `.fstdd/version.yaml`
- **WHEN** 执行 `fstdd installation-id`
- **THEN** SHALL 向 stderr 输出明确错误（提示先 `fstdd init`）并以非 0 退出
- **AND** SHALL NOT 创建 `.fstdd/` 目录或任何文件
- **AND** SHALL NOT 写全局 `~/.fstdd/projects.yaml`

#### Scenario: SC-IID-009

- **GIVEN** 已初始化项目，version.yaml 无 `installation_id`
- **WHEN** 执行 `fstdd installation-id`
- **THEN** SHALL 写入一行 `installation_id: <PREFIX>-<8HEX>`，值匹配 `^[A-Z0-9]{2,8}-[0-9A-F]{8}$`
- **AND** 该行 SHALL 插在**首个顶层键行之前**（注释头仍在文件最上方）
- **AND** 写入后文件总行数 SHALL 只增加 1 行
- **AND** PREFIX SHALL 由目录名派生（`stdd-repo → STDD`），或由 `--prefix` 覆盖
- **AND** 回填后 `experience._next_id(project_root)` SHALL 返回以该 `installation_id` 开头的 ID（写进去的值必须真被读取端采用）

#### Scenario: SC-IID-010

- **GIVEN** version.yaml 含注释头、`changelog: |` 字面块、CRLF 或 LF 行尾
- **WHEN** 执行 `fstdd installation-id` 写入
- **THEN** 写入后 `yaml.safe_load` 的既有键值 SHALL 与写入前逐键相等（深比较）
- **AND** 原文件所有以 `#` 开头的注释行 SHALL 仍全部存在（顺序不变）
- **AND** 原文件中 `^[A-Za-z_]\w*: \|$` 形态的块标量标记 SHALL 仍全部存在
- **AND** 行尾风格 SHALL 与写入前一致（CRLF 文件写后仍为 CRLF，且 `\r\n` 计数只 +1）
- **AND** 上述任一不满足时 SHALL NOT 落盘，并报错退出（非 0）

#### Scenario: SC-IID-011

- **GIVEN** version.yaml 已有合法 `installation_id`
- **WHEN** 再次执行 `fstdd installation-id`
- **THEN** SHALL 打印现值并以 0 退出
- **AND** 文件字节 SHALL 保持不变（含 mtime 不变）
- **AND** `--dry-run` 时 SHALL 只打印将生成/现存的 ID，SHALL NOT 落盘

#### Scenario: SC-IID-012

- **GIVEN** 全局 `~/.fstdd/projects.yaml` 存在
- **WHEN** 执行 `fstdd installation-id`
- **THEN** 该文件 SHALL NOT 被修改（字节级不变）
- **AND** 命令 SHALL NOT 调用 `upgrade._register_project`

#### Scenario: SC-IID-013

- **GIVEN** version.yaml 含注释头与块标量，且含 `installation_id`
- **WHEN** 调用 `upgrade._write_version_yaml(project_root, {...})`
- **THEN** 注释行与块标量标记 SHALL 全部保留，`installation_id` SHALL 不变
- **AND** 传入的新字段 SHALL 被写入
- **AND** 未在该次参数中出现的既有字段 SHALL 一并存活（沿用 SC-IID-004）

#### Scenario: SC-IID-014

- **GIVEN** 同一目录名（如 `my-project`）与同一 `--prefix` 取值
- **WHEN** 分别经 `fstdd init` 与 `fstdd installation-id` 派生 PREFIX
- **THEN** 两条路径产出的 PREFIX SHALL 完全一致
- **AND** 两路径 SHALL 共用 `utils.INSTALLATION_ID_RE` 做形状校验，不得各写一份正则
- **AND** `--prefix 'BAD!'` 时两路径 SHALL 都向 stderr 告警并回落，SHALL NOT 中止

#### Scenario: SC-IID-015

- **GIVEN** 本仓真实经验库（含 `EXP-2026-00XX` / `EXP-009-*` / `EXP-XXXXXXXX` / `FSTDD002-*` 四族）
- **WHEN** 回填 `installation_id` 前后分别调用 `_rebuild_index`
- **THEN** `last_id` SHALL 恒为 40（8 位 hex 段不得被当作序号）
- **AND** 回填 SHALL NOT 改动任何既有经验文件的文件名或 frontmatter `experience_id`
