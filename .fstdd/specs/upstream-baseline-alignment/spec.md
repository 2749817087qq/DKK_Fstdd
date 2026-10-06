# Spec: upstream-baseline-alignment

> Change: 2026-10-05-upstream-baseline-alignment | Auto-generated Human View

## Requirements

### Requirement: 仓库 SHALL 新增 `docs/UPSTREAM_BASELINE.md`，把上游基线快照固化为**可核验证据**：
观测时点（带时区）+ 观测时本仓 base git sha + 外部锚 E 的 tag / HEAD sha / pushed_at /
Releases 状态 + 其他通道排除结论；SHALL 使后续对标可直接引用而无需再次联网探针。
其中数值 SHALL 与实测一致。


#### Scenario: SC-001

- **GIVEN** 仓库当前无上游基线快照文档；每次「有没有新版本」都需重新联网探针
- **WHEN** 检查 `docs/UPSTREAM_BASELINE.md` 是否存在并读取其证据段
- **THEN** SHALL 存在该文件，且含观测时点（带时区的 observed_at）与观测时本仓 base git sha
- **AND** SHALL 含外部锚 E 的 tag、master HEAD sha、pushed_at 三项
- **AND** SHALL 含 Releases 状态与分支状态（仅 master / 未归档）
- **AND** SHALL 含其他通道排除结论（Gitee / PyPI）

#### Scenario: SC-002

- **GIVEN** 上游基线探针已在观测时点完成（本机不可直连 github.com:443，经服务器出网）
- **WHEN** 把 `docs/UPSTREAM_BASELINE.md` 记录的快照数值与实测值逐一比对
- **THEN** SHALL 使 tag=v3.0.5、master HEAD sha=b9a4af62b5f4fd2747884c0a61febbc341792ac2、pushed_at=2026-08-17T15:25:43Z、Releases 为空 与实测一致
- **AND** SHALL 记录观测通道（经 ssh fstdd-hub 只读查询）
- **AND** SHALL NOT 记录任何凭证、内网私密路径或用户数据

#### Scenario: SC-003

- **GIVEN** 本仓 vendored 内核 K=3.1.0 与发行版 R=3.3.4 均领先于上游最新发布 E=v3.0.5
- **WHEN** 检查 `docs/UPSTREAM_BASELINE.md` 是否含领先量清单
- **THEN** SHALL 含「本仓领先量清单」，逐项列出本仓相对外部锚 E 的增量
- **AND** 清单 SHALL 至少覆盖 vendored 内核轴（K）与发行版轴（R）两个维度
- **AND** 清单中的版本数值 SHALL 与机器可读源一致

### Requirement: `docs/UPSTREAM_BASELINE.md` SHALL 固化上游经验库 `leonai42/stdd-experiences` 的**只读**
对标结论：明确其**非**我方回传目标、给出「清单中我方 node 前缀条目数」的只读核对实测值，
并给出可借鉴增量。对标 SHALL NOT 修改、外发或接入回传链路。


#### Scenario: SC-004

- **GIVEN** 我方经验回传目标锁定为 2749817087qq/Fstdd-experiences（share_experience.py DEFAULT_EXP_REPO）
- **WHEN** 读取 `docs/UPSTREAM_BASELINE.md` 的经验库对标段
- **THEN** SHALL 明确 leonai42/stdd-experiences 非我方回传目标
- **AND** SHALL 指明我方回传目标为 2749817087qq/Fstdd-experiences
- **AND** SHALL 记录该上游经验库的最近推送时点（观测值）

#### Scenario: SC-005

- **GIVEN** 对标为只读核对（经 ssh fstdd-hub 拉取清单，不写入上游仓库）
- **WHEN** 检查对标段中的「我方 node 前缀条目数」
- **THEN** SHALL 给出该计数的只读核对实测值（含 0 也是有效实测值）
- **AND** SHALL 写明计数口径（我方 node 前缀形如 FSTDD003 / FSTDD-003）
- **AND** SHALL 与观测时点绑定，标注为实测值而非估计

#### Scenario: SC-006

- **GIVEN** 快照数字（sha / pushed_at / Releases）易变，多处分维护必然再漂移
- **WHEN** 扫描 NOTICE.md 与 README.md 是否复制了快照数字
- **THEN** SHALL 使 NOTICE.md 与 README.md 中不出现快照型的 sha / pushed_at 字面量
- **AND** NOTICE.md / README.md 引用基线时 SHALL 以链接指向 docs/UPSTREAM_BASELINE.md
- **AND** 快照数字 SHALL 仅存在于 docs/UPSTREAM_BASELINE.md 一处（单一事实源）
