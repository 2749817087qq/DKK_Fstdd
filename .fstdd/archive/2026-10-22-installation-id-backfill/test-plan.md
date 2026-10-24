# installation_id 回填：给已初始化项目补齐身份，且不破坏 version.yaml 的可读文本形态 - 测试方案

**change**：`2026-10-22-installation-id-backfill`
**模式**：standard ｜ **task_type**：code ｜ **锚定**：L2
**基线 commit**：`d86a075`

---

## 1. 测试策略

### 1.1 分层原则

| 层 | 手段 | 能证明 | 环境 |
|---|---|---|---|
| L1 单元 | 直调 `utils.set_top_level_scalar` / `init._ensure_installation_id` / `upgrade._write_version_yaml` | 文本插入位置、自检 4 断言、行尾保持、幂等 | 本地 tmp_path |
| L2 集成 | `cmd_installation_id` 全流程（无 `.fstdd/` → 有 → 重复） | 命令语义、退出码、registry 不写 | 本地 tmp_path |
| L3 回归 | 真实 336 行 `version.yaml` 副本 + 真实 109 条经验库 | 文本形态保留、`last_id` 不跳 | 本仓真实文件（只读副本） |
| L4 全量 | `upstream/tests` + `tests/` 全量 | 无退化 | 本地 |

### 1.2 判别力判据（本仓黄金标准）

把被测实现切回 baseline（`d86a075`）重跑，用例必须变红；否则是假测试。
本 change 的**核心风险是「假绿」**：`yaml.dump` 回写后 `yaml.safe_load` 语义完全等价，
所以「解析成功」「键值相等」这类断言对 baseline **不会判红**。
因此 TC-IID-010 的判红点必须是**文本级断言**（注释行是否存在、块标量标记是否存在），
不是语义断言。这一点在实现测试时须显式验证。

TC-IID-016 是**回归护栏**（守护「8 位 hex 段不被当序号」的既有约定），
对 baseline 不判红，已在此标注，不计入判别力统计。

### 1.3 夹具策略

**不用空文件**。本 change 的 bug 只在「有注释 + 有块标量 + 有既有键」的文件上暴露，
空 YAML 会让所有用例恒绿。夹具分三份：

| 夹具 | 内容 | 用途 |
|---|---|---|
| `real_version_yaml` | 本仓 `.fstdd/version.yaml` 的副本（336 行，4 行注释头 + `changelog: \|`） | 主夹具 |
| `crlf_version_yaml` | 同上但行尾改 CRLF | 行尾保持 |
| `minimal_version_yaml` | 3 键无注释 | 对照（证明普通项目不被误伤） |

---

## 2. 详细测试案例

### 2.1 `installation-identity`

#### TC-IID-008 ｜ 无 `.fstdd/` 时拒绝执行且零副作用 ｜ P0

| 项 | 内容 |
|---|---|
| **ID** | TC-IID-008 |
| 对应 SC | SC-IID-008 |
| 预置 | 空 tmp 目录（无 `.fstdd/`） |
| 输入 | `cmd_installation_id(Namespace(prefix=None, dry_run=False))` |
| 预期 | 抛 `SystemExit` 且 code == 2；stderr 含 `fstdd init` |
| 补充 | 执行后目录仍为空（`list(tmp_path.iterdir()) == []`）；`~/.fstdd/projects.yaml` 字节不变 |

#### TC-IID-009 ｜ 回填只新增 1 行且插在首个顶层键之前 ｜ P0

| 项 | 内容 |
|---|---|
| **ID** | TC-IID-009 |
| 对应 SC | SC-IID-009 |
| 预置 | `real_version_yaml`（336 行） |
| 输入 | `cmd_installation_id(...)` |
| 预期 | 行数 337；首个非注释、非空行 == `installation_id: <IID>`；前 4 行仍为原注释头 |
| 补充 | IID 匹配 `^STDD-[0-9A-F]{8}$`（目录名 `stdd-repo` 派生）；`--prefix MYPROJ` 时为 `MYPROJ-*`；回填后 `experience._next_id(root)` 返回值以该 IID 开头（写读闭环） |

#### TC-IID-010 ｜ 文本形态保留（注释 / 块标量 / 键值深比较） ｜ P0

| 项 | 内容 |
|---|---|
| **ID** | TC-IID-010 |
| 对应 SC | SC-IID-010 |
| 预置 | `real_version_yaml` |
| 输入 | 写入后逐项断言 |
| 预期 | ① 原文件所有 `#` 开头行**逐行**仍在新文件中且顺序一致；② `changelog: \|` 与 `notes: \|` 标记仍在；③ `safe_load(新)` 去掉 `installation_id` 后与 `safe_load(旧)` 深比较相等 |
| 补充 | **判别力关键**：对 baseline（`yaml.dump`）此用例必须在 ① ② 判红（③ 会通过 —— 这正是「语义等价但文本被毁」的证据） |

#### TC-IID-011 ｜ 行尾风格保持（CRLF 夹具） ｜ P1

| 项 | 内容 |
|---|---|
| **ID** | TC-IID-011 |
| 对应 SC | SC-IID-010（行尾 AND） |
| 预置 | `crlf_version_yaml`（行尾全 CRLF） |
| 输入 | 写入 |
| 预期 | 写后 `\r\n` 计数 == 原计数 + 1；孤立 `\n`（非 CRLF）计数为 0 |
| 补充 | 同一夹具转 LF 后再跑一次，断言 `\r\n` 计数恒 0（两个方向都测） |

#### TC-IID-012 ｜ 幂等：重复执行字节不变 + dry-run 不落盘 ｜ P0

| 项 | 内容 |
|---|---|
| **ID** | TC-IID-012 |
| 对应 SC | SC-IID-011 |
| 预置 | 已回填过的 `real_version_yaml` |
| 输入 | 再执行一次；另起一次 `--dry-run` |
| 预期 | 第二次：bytes 不变、mtime 不变、exit 0、stdout 含现值；`--dry-run`：bytes 不变 |
| 补充 | `--dry-run` 在**未回填**文件上也须不落盘，且打印 `将生成 STDD-<8位HEX>` |

#### TC-IID-013 ｜ 回填不写全局 registry ｜ P1

| 项 | 内容 |
|---|---|
| **ID** | TC-IID-013 |
| 对应 SC | SC-IID-012 |
| 预置 | 重定向 `HOME`/`USERPROFILE` 到 tmp（避免碰真实 registry） |
| 输入 | 回填一次 |
| 预期 | 重定向后的 `projects.yaml` 不存在或字节不变 |
| 补充 | 契约断言：`cmd_installation_id` 源码中不出现 `_register_project`（AST 扫描） |

#### TC-IID-014 ｜ `upgrade._write_version_yaml` 保留注释与块标量 ｜ P0

| 项 | 内容 |
|---|---|
| **ID** | TC-IID-014 |
| 对应 SC | SC-IID-013 |
| 预置 | `real_version_yaml` + 已有 `installation_id` |
| 输入 | `_write_version_yaml(root, {"fstdd_version": "9.9.9"})` |
| 预期 | 注释行全在；`changelog: \|` 仍在；`installation_id` 不变；`fstdd_version == "9.9.9"` |
| 补充 | 同时断言「未在该次参数中出现的字段一并存活」（沿用 SC-IID-004） |

#### TC-IID-015 ｜ 两路径 PREFIX 一致（契约） ｜ P1

| 项 | 内容 |
|---|---|
| **ID** | TC-IID-015 |
| 对应 SC | SC-IID-014 |
| 预置 | 参数化：目录名 `my-project` / `stdd-repo` / `云服务器`；`--prefix` 取 `None` / `MYPROJ` / `BAD!` |
| 输入 | 分别走 `init._get_prefix` 与 `cmd_installation_id` 的派生分支 |
| 预期 | 同参数下 PREFIX 完全相同；`BAD!` 场景两路径都告警（stderr）且回落，都不中止 |
| 补充 | 反向断言：两处源码都引用 `utils.INSTALLATION_ID_RE`，无第二份正则字面量 |

#### TC-IID-016 ｜ 真实 109 条经验库 `last_id` 恒 40 ｜ P1（回归护栏）

| 项 | 内容 |
|---|---|
| **ID** | TC-IID-016 |
| 对应 SC | SC-IID-015 |
| 预置 | 本仓真实 `.fstdd/experiences/`（只读，不修改） |
| 输入 | `_rebuild_index(exp_dir)` 前后各一次 |
| 预期 | 两次 `last_id` 均为 40 |
| 补充 | 对 baseline 不判红（回归护栏）；同时断言 `len(glob("*.md")) == 109` 且无文件被改名 |

---

## 3. 测试执行矩阵

| 功能 | L1 单元 | L2 集成 | L3 真实夹具 | L4 全量 |
|---|---|---|---|---|
| 回填命令语义（拒绝/写入/幂等） | TC-008/012 | ✓ | — | ✓ |
| 文本插入位置 | TC-009 | ✓ | ✓ | — |
| 文本形态保留 | TC-010/011 | — | ✓ | — |
| upgrade 写口 | TC-014 | — | ✓ | ✓ |
| PREFIX 一致性 | TC-015 | ✓ | — | — |
| registry 不写 | TC-013 | ✓ | — | — |
| 经验库不回归 | — | — | TC-016 | ✓ |

## 4. 回归风险矩阵

| 改动区域 | 风险 | 说明 |
|---|---|---|
| `init._ensure_installation_id` 写策略 | **高** | 上一 change 的 SC-IID-001/006/007 全部依赖它；换写实现必须保证那 3 条不退化 |
| `upgrade._write_version_yaml` | **高** | 上一 change 的 SC-IID-004（合并语义）在此；改文本插入后合并语义须保持不变 |
| `cli/__init__.py` 子命令注册 | 中 | 新增 parser 可能影响 `--help` 快照类断言 |
| `utils.py` 公共面 | 中 | 新增 `set_top_level_scalar` 被两个命令共用，改签名会波及两处 |
| 经验库 | 低 | 本 change 不改任何经验文件；TC-016 守护 |
| `~/.fstdd/projects.yaml` | 低 | 回填命令不写；但**测试本身**若误调 `cmd_init` 会写（FU-008），夹具须重定向 HOME |

## 5. 建议补充顺序

| 优先级 | TC | 理由 |
|---|---|---|
| P0 | TC-008 / TC-009 / TC-010 / TC-012 / TC-014 | 命令语义 + 文本形态 + 幂等 + upgrade 同修，缺一即功能不成立 |
| P1 | TC-011 / TC-013 / TC-015 / TC-016 | 行尾边界、registry 契约、两路径一致、经验库回归 |
| P2 | — | 本 change 无 P2 |

**TC 统计**：9 个（P0 × 5 / P1 × 4 / P2 × 0），对应 8 个新增 Scenario（SC-IID-008..015），
其中 SC-IID-010 由 TC-010 + TC-011 两条覆盖（语义保留 / 行尾保持）。
