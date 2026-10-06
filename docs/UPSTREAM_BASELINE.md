# 上游基线快照（E 轴单一事实源）

> 本文件是**上游基线快照证据的唯一出处**。`NOTICE.md` 与 `README.md` 对基线只**链接**本文件，
> **不复制**其中的 sha / pushed_at 等易变数字 —— 避免多处分维护再次漂移。
> 相关 change：`2026-10-05-upstream-baseline-alignment`（决策 2 / 决策 4）。
> 版本三轴口径：**E** 外部上游锚 / **K** 本仓 vendored 内核 / **R** 本仓发行版。

## 一、观测记录

| 项 | 值 |
|----|----|
| observed_at | `2026-10-05T12:02:00+08:00` |
| observed_base_git_sha | `1046f5eaffa4f4c80b533ca2d24700fd7b0a46f2` |
| 观测通道 | 经 `ssh fstdd-hub` 只读查询 GitHub REST API（本机不可直连 `github.com:443`） |

> `observed_at` 是**信息采集时刻**，不是本文件的生成时刻。下节所有数值均为该时点的**实测值**，非估计。

## 二、E 轴：上游项目 `leonai42/stdd` 的最新发布

| 项 | 实测值 |
|----|--------|
| 仓库 | https://github.com/leonai42/stdd |
| 最新 tag | `v3.0.5` |
| tag / master HEAD sha | `b9a4af62b5f4fd2747884c0a61febbc341792ac2` |
| master pushed_at | `2026-08-17T15:25:43Z` |
| Releases | 空（0 条） |
| 分支状态 | 仅 `master`（`default_branch=master`），未归档（`archived=false`） |
| 历史 tags（同期可见） | `v2.9.5` / `v2.9.2` / `v2.9.1` / `v2.9.0` / `v2.8.0` / `v2.7.0` / `v2.5.0` / `v2.4.0` / `V2.3.0` / `V2.2` |

**结论**：E 轴自 **2026-08-17 起未再推送**，最新发布仍是 `v3.0.5`（tag 指向的 commit 即 master HEAD）。

## 三、其他通道排除

| 通道 | 探针结果 | 结论 |
|------|----------|------|
| Gitee `leonai42/stdd` | 页面 HTTP `404` | 不存在镜像 |
| PyPI `pypi.org/pypi/stdd` | HTTP `200`；version=`0.1.0`，summary=`Universal template for PyQt6 + PyMySQL applications with role-based access control` | **同名无关包**（与 FSTDD 无关的第三方便携模板） |
| PyPI `fstdd` | HTTP `404` | 未发包 |

**结论**：上游项目仅有 GitHub 一个发布通道；Gitee 与 PyPI 均不可作为基线来源。

## 四、本仓领先量清单

本仓两轴均**领先**于外部锚 E（`v3.0.5`）：

| 轴 | 版本 | 机器可读事实源 | 相对 E 的增量 |
|----|------|----------------|---------------|
| **K** vendored 内核 | `3.1.0` | `.fstdd/version.yaml: upstream_version`；`upstream/pyproject.toml: version` | 内核含本仓衍生改动，**领先**上游最新发布；`upstream/CHANGELOG.md` 有 V3.1.0（2026-09-26）条目 |
| **R** 本仓发行版 | `3.3.5` | `.fstdd/config.d/project.yaml: stdd_version`；`.fstdd/version.yaml: fstdd_version` | 本仓发布号，随本仓 release 漂移（独立于 E） |

> 口径提醒：`upstream/` **不是**逐字节冻结的上游快照 —— 它被本仓按 change 流程持续修改并**在本仓内单独编版本**
> （K），因此 K ≠ E。任何把 K 或 R 写作 `3.0.5` 的声明都是错的。

## 五、上游经验库对标（只读）

| 项 | 实测值 / 结论 |
|----|---------------|
| 上游经验库 | `leonai42/stdd-experiences` |
| 该库 pushed_at | `2026-10-05T00:31:25Z` |
| 该库状态 | `default_branch=main`，未归档（`archived=false`） |
| 是否为我方回传目标 | **否** —— `leonai42/stdd-experiences` **非我方回传目标** |
| 我方回传目标 | `2749817087qq/Fstdd-experiences`（源：`tools/share_experience.py: DEFAULT_EXP_REPO`） |

**我方 node 前缀条目数（实测）**：`0`

- **计数口径**：条目文件名以 `FSTDD003-` 或 `FSTDD-003-` 开头（我方节点导出命名为
  `<node_id>-EXP-<YYYYMMDD>-<seq>.md`）；并辅以对 `HEAD` 归档的全文扫描（检索 `FSTDD003` / `FSTDD-003` 字符串）。
- **实测结果**：文件名前缀命中 **0**；全文命中 **0**。`0` 为**有效实测值**（表示我方条目尚未进入该库）。
- **观测时点**：`2026-10-05T12:02:00+08:00`；标注为**实测**值而非估计。
- **可借鉴增量**（只读对标，不接入回传链路）：该库以 `packs/<领域>/<版本>/` 组织经验包
  （`business-logic` / `frontend` / `go` / `judgment-integrity` / `python` / `python-testing` / `typescript`），
  另有 `audit/authoring-notes/` 记录各语言审阅要点 —— 可作为我方经验包分组与审阅要点的组织参考。

> 边界：本节为**只读核对**，不修改、不外发、不接入回传实现；我方回传链路与目标保持不变。

## 六、引用约定

- 需引用基线事实的活体声明面（`NOTICE.md`、`README.md`）**只链接本文件**，不复制本文件中的 sha / pushed_at 字面量。
- 快照数值变更时**只改本文件一处**。