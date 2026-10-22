# init.py 生成 installation_id + _next_id() 使用前缀 - 测试方案

**change**：`2026-10-21-installation-id-prefix`
**模式**：thorough ｜ **task_type**：code ｜ **锚定**：L2
**修订**：2026-10-22（BUILD 阶段 C1 评审后：修正 TC-IID-003 预期、TC-IID-004 改真路径、
补 TC-IID-006/007、对齐「计划 TC 数」与「实际测试函数数」）

---

## 1. 测试策略

### 1.1 分层原则

| 层 | 手段 | 能证明 | 环境 |
|---|---|---|---|
| L1 单元 | 直接调 `_next_id` / `_ensure_installation_id` / `_write_version_yaml` | ID 格式、回落、写入侧防御 | 本地 tmp_path |
| L2 集成 | `cmd_init` 全流程 + `_cmd_add` 全链路 | 端到端 ID 一致 | 本地 tmp_path |
| L3 回归 | 既有 upstream/tests 全量（1032 例） | 无退化 | 本地 |

### 1.2 判别力判据（本仓黄金标准）

把被测实现切回 baseline（`a489420`）重跑，用例必须变红；否则是假测试。
本文件里 TC-EID-005 / TC-EID-006 是**回归护栏**（守护 2026-09-17 已修好的
「任意 `*.md` 都是经验」约定），对 baseline 不判红，已在此显式标注，不计入判别力统计。

---

## 2. 详细测试案例

### 2.1 `installation-identity`

#### TC-IID-001 ｜ init 后 version.yaml 含合法 installation_id ｜ P0

| 项 | 内容 |
|---|---|
| **ID** | TC-IID-001 |
| 对应 SC | SC-IID-001 |
| 预置 | `temp_project`（conftest 最小骨架） |
| 输入 | `cmd_init(Namespace(force=False, dry_run=False, prefix=None))` |
| 预期 | `installation_id` 匹配 `^[A-Z0-9]{2,8}-[0-9A-F]{8}$` |
| 补充 | `test_init_keeps_existing_version_fields`：既有 `stdd_version` / `source_path` 不被抹掉 |

> 说明：本仓既有 `test_init.py` 全部直接调 `cmd_init`（不走 subprocess），此处保持一致。
> 「CLI 是否真挂上 `--prefix`」由 TC-IID-002 的 `--help` 用例单独覆盖 —— 用 subprocess
> 跑完整 init 会触发网络拉取，既慢又不稳定，收益不抵成本。

#### TC-IID-002 ｜ --prefix 覆盖 + CLI 接线 ｜ P0

| 项 | 内容 |
|---|---|
| **ID** | TC-IID-002 |
| 对应 SC | SC-IID-002 |
| 预置 | `temp_project` |
| 输入 | `cmd_init(Namespace(prefix="MYPROJ"))` |
| 预期 | `installation_id` 以 `MYPROJ-` 开头且形状合法 |
| 补充 1 | 非法 prefix（`"my proj!"`）→ 告警 + 回落项目名派生，不中止 |
| 补充 2 | `python -m fstdd init --help` 输出含 `--prefix`（防「测试全绿但用户敲不出来」） |

#### TC-IID-003 ｜ 项目名派生 PREFIX ｜ P1

| 项 | 内容 |
|---|---|
| **ID** | TC-IID-003 |
| 对应 SC | SC-IID-003 |
| 预置 | 目录名 `my-project` / `云服务器` / `a` / `PROJ_2026` |
| 输入 | `_ensure_installation_id` |
| 预期 | `my-project` → `MYPR-…`（剥掉连字符）；`云服务器` → `FSTDD-…`；全部匹配 `INSTALLATION_ID_RE` |
| 关键断言 | 带连字符的项目名**不得**产出三段 ID（`MY-P-0803ADF7` 会打穿 `split('-')[-1]` 取序号） |

#### TC-IID-004 ｜ upgrade 不覆盖 ｜ P0

| 项 | 内容 |
|---|---|
| **ID** | TC-IID-004 |
| 对应 SC | SC-IID-004 |
| 预置 | version.yaml 含 `installation_id` + `stdd_version` + 自定义字段 `future_field` |
| 输入 | `_write_version_yaml(root, {"stdd_version": "3.1.1", "locked": False})` |
| 预期 | `installation_id`、`future_field` 均存活；`stdd_version` 被更新 |
| 为什么这么测 | `_write_version_yaml` 是 `upgrade` 的**唯一写口**；原设计假设「upgrade 不改项目级 version.yaml」经实测为**假**（覆盖式写入会抹掉 installation_id）。直接测该函数才是真判决，用「再跑一次 `cmd_init(force=True)`」是假路径 |

#### TC-IID-005 ｜ self_check 输出实际生效值 ｜ P0

| 项 | 内容 |
|---|---|
| **ID** | TC-IID-005 |
| 对应 SC | SC-IID-005 |
| 预置 | 正常 init |
| 预期 | stdout 含 `installation_id: ✅ <落盘值>`（精确匹配，非子串模糊） |
| 反向 | version.yaml 不可解析时 → 必须 `⚠️` 且**不得**出现 `✅`（原实现按「字段存在」判 ✅，恒真） |

#### TC-IID-006 ｜ 既有坏值重新生成 ｜ P1

| 项 | 内容 |
|---|---|
| **ID** | TC-IID-006 |
| 对应 SC | SC-IID-006 |
| 预置 | `installation_id: ../etc/passwd` + `stdd_version: '3.0.5'` |
| 输入 | `_ensure_installation_id` |
| 预期 | ① 返回值合法；② 落盘值 == 返回值且 `stdd_version` 保留；③ `_next_id` 立刻产出 `{新值}-EXP-YYYY-0001`（写入口径必须真被读取端采用） |

#### TC-IID-007 ｜ 损坏 version.yaml 不覆写 ｜ P1

| 项 | 内容 |
|---|---|
| **ID** | TC-IID-007 |
| 对应 SC | SC-IID-007 |
| 预置 | version.yaml 为非法 YAML |
| 输入 | `_ensure_installation_id` |
| 预期 | 返回 None；文件字节**完全不变**；stdout 含「无法解析」 |

### 2.2 `experience-id-generation`

#### TC-EID-001 ｜ _next_id 带前缀 ｜ P0

| 项 | 内容 |
|---|---|
| **ID** | TC-EID-001 |
| 对应 SC | SC-EID-001 |
| 预置 | `installation_id: STDD-A1B2C3D4` |
| 输入 | `_next_id({"last_id": 0}, project_root)` |
| 预期 | `STDD-A1B2C3D4-EXP-{year}-0001` |
| 补充 | `last_id=41` → `…-0042`（序号推进不被前缀干扰） |

#### TC-EID-002 ｜ 回落旧格式 ｜ P0

| 项 | 内容 |
|---|---|
| **ID** | TC-EID-002 |
| 对应 SC | SC-EID-002 |
| 预置 | ① 无 version.yaml ② 有文件无字段 ③ 字段形状非法（6 种值） |
| 预期 | 三者均返回 `EXP-{year}-0001`；③ 另需在 stderr 出声 |

#### TC-EID-003 ｜ project_root=None ｜ P1

| 项 | 内容 |
|---|---|
| **ID** | TC-EID-003 |
| 对应 SC | SC-EID-003 |
| 输入 | `_next_id({"last_id": 5}, None)` |
| 预期 | `EXP-{year}-0006`，不抛异常 |

#### TC-EID-004 ｜ experience add 全链路 ｜ P0

| 项 | 内容 |
|---|---|
| **ID** | TC-EID-004 |
| 对应 SC | SC-EID-004 |
| 预置 | 含 `installation_id` 的项目 |
| 输入 | `_cmd_add(args, exp_dir, project_root)` |
| 预期 | 生成 `{iid}-EXP-{year}-0001.md`；frontmatter `experience_id` 一致；索引 `last_id == 1` |

#### TC-EID-005 ｜ 带前缀 ID 被枚举并进索引 ｜ P0（回归护栏）

| 项 | 内容 |
|---|---|
| **ID** | TC-EID-005 |
| 对应 SC | SC-EID-005 |
| 预置 | `STDD-A1B2C3D4-EXP-2026-0001.md`（含最小 frontmatter） |
| 预期 | `_iter_experience_files` 返回它；`_rebuild_index` 的 eid 集合含完整带前缀 ID，`last_id == 1` |
| 注 | `_load_experience` 对**完全无 frontmatter** 的 .md 返回 None（2026-09 起既有语义），故必须带最小 frontmatter |

#### TC-EID-006 ｜ frontmatter 优先 ｜ P1（回归护栏）

| 项 | 内容 |
|---|---|
| **ID** | TC-EID-006 |
| 对应 SC | SC-EID-006 |
| 预置 | `random-name.md`，frontmatter `experience_id: STDD-X-EXP-2026-0001` |
| 预期 | 索引里出现 frontmatter 的 ID，且**不出现**文件名 stem |

#### TC-EID-007 ｜ _rebuild_index 数字提取 ｜ P0

| 项 | 内容 |
|---|---|
| **ID** | TC-EID-007 |
| 对应 SC | SC-EID-007 |
| 预置 | 混合 `…-EXP-2026-0005.md` 与 `EXP-2026-0003.md` |
| 预期 | `last_id == 5` |
| 补充 | 单独放 `WBCC-0803ADF7-EXP-2026-0002.md` → `last_id == 2`（HEX 段 `0803ADF7` 不得被当序号） |

---

## 3. 测试执行矩阵

| 功能 | L1 单元 | L2 集成 | L3 回归 |
|---|---|---|---|
| init 生成 installation_id | — | ✅ TC-IID-001 | — |
| --prefix 覆盖 + CLI 接线 | ✅ | ✅ TC-IID-002 | — |
| 项目名派生（含中文/连字符） | ✅ TC-IID-003 | — | — |
| upgrade 不覆盖 | ✅ TC-IID-004 | — | — |
| self_check 输出实际值 | — | ✅ TC-IID-005 | — |
| 写入侧坏值修复 | ✅ TC-IID-006 | — | — |
| 写入侧损坏不覆写 | ✅ TC-IID-007 | — | — |
| _next_id 带前缀 | ✅ TC-EID-001 | — | — |
| _next_id 回落 | ✅ TC-EID-002/003 | — | — |
| experience add 全链路 | — | ✅ TC-EID-004 | — |
| 带前缀 ID 枚举/索引 | ✅ TC-EID-005/006 | — | — |
| _rebuild_index 数字提取 | ✅ TC-EID-007 | — | — |
| 下游 `EXP-*` 通配不再假设 | — | — | ✅ FSD-004 门禁（已扩围 tools/ + hooks/） |
| 既有测试不退化 | — | — | ✅ pytest upstream/tests 全量 |

---

## 4. 回归风险矩阵

| 改动区域 | 风险等级 | 可能影响 | 回归手段 |
|---|---|---|---|
| `_next_id` 签名变更 | 中 | 全仓唯一调用点是 `_cmd_add`；漏传静默回落旧格式 | TC-EID-001~003 + grep 复核 |
| `init.py` cmd_init / `_ensure_installation_id` | 中 | version.yaml 写入 / 自检输出 | TC-IID-001~007 |
| `upgrade._write_version_yaml` 改合并写 | **高** | 所有 `upgrade` / `lock` / `unlock` 的 version.yaml 写入 | TC-IID-004 + 既有 upgrade 测试 |
| `utils.read_installation_id` 新增 | 中 | init 自检 + experience add 共用 | TC-IID-005/006 + TC-EID-001/002 |
| `tools/*` 枚举口径放宽 | 中 | 回传通道是否会多推/漏推 | 既有 tools 测试 + FSD-004 门禁 |
| FSD-004 门禁扩围 | 低 | 新增扫描 `tools/` 与 `.fstdd/hooks/` | 门禁自测（11 例） |

---

## 5. 建议补充顺序

| 优先级 | 内容 |
|---|---|
| P0 | TC-IID-001/002/004/005 + TC-EID-001/002/004/005/007 |
| P1 | TC-IID-003/006/007 + TC-EID-003/006 |

---

## 6. 覆盖统计

| 指标 | 值 |
|---|---|
| Spec Requirements | 3（IID 3 组） |
| Spec Scenarios | 7（SC-IID-001~007） |
| Spec Requirements（EID） | 4 |
| Spec Scenarios（EID） | 7（SC-EID-001~007） |
| TC Cases（计划） | 14（IID 7 + EID 7） |
| TC Cases（实际测试函数） | 29 |
| TC 覆盖率 | 14/14 = 100% |
| 判别力用例（baseline 必红） | 27 / 29（TC-EID-005/006 为回归护栏） |
| P0 / P1 | 9 / 5 |
