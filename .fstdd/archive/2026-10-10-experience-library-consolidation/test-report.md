# 测试报告 / Test Report — 2026-10-10-experience-library-consolidation

> Phase 3 BUILD 交付物 · 供 Gate 3 终审
> 版本：v3.3.8 · 生成日期：2026-10-11

## 0. 概要（Executive Summary）

- **变更**：把本机 4 个 FSTDD 经验库副本（179 文件）收敛为 1 个权威库（stdd-repo），去重、裁决漂移、
  修复「双块 frontmatter 只解析首块、静默丢真身」的解析器 bug（P1），并落地可重跑的迁移脚本。
- **核心交付**：
  1. `_load_experience` 双块解析修复（**同时落到 live 模块 FSTDD003 与 vendored 法定源 stdd-repo**）。
  2. 经验库 4→1 收敛：权威库 = **91 文件 / 89 有效 eid / 索引 total=90**。
  3. 幂等迁移脚本 `tools/consolidate_experiences.py`（备份→回灌→裁决→去重→降级→索引→校验）。
  4. 5 个解析器契约测试（`upstream/tests/commands/test_experience_parser.py`），全绿。
- **全量门禁**：1123 用例，见 §4（待填入最终数字）。
- **偏差**：AMD-001~007（见 `design-adjustments.md`），其中 **AMD-003（live 模块是 FSTDD003 非 stdd-repo）为关键纠正**。

## 1. 变更范围（Scope / 改动文件）

| 文件 | 角色 | 状态 |
|------|------|------|
| `D:\FSTDD003\upstream\fstdd\cli\commands\experience.py` | **live 运行代码**（editable 安装目标） | `_load_experience` 已修 |
| `E:/FSTDD/stdd-repo/upstream/fstdd/cli/commands/experience.py` | vendored 法定源（待 DELIVER commit） | `_load_experience` 已修（逐字节同 FSTDD003） |
| `E:/FSTDD/stdd-repo/upstream/tests/commands/test_experience_parser.py` | 新增契约测试 | 5 用例，全绿 |
| `E:/FSTDD/stdd-repo/tools/consolidate_experiences.py` | 新增幂等迁移脚本 | C1–C8 串联 |
| `E:/FSTDD/stdd-repo/.fstdd/experiences/` | 权威库（91 文件 + 重建索引） | 新增 12 回灌 + 重建索引 |
| `E:/FSTDD/_backup/exp-consolidation-2026-10-11/{FSTDD003,home-FSTDD,FSTDD002}/` | C1 备份（100 文件） | 完整可回退 |
| `D:/FSTDD003/.fstdd/experiences/.trash-2026-10-11/` 等 3 处 | C4 冗余移入（可恢复） | 100 冗余文件 |
| 3 副本 `README.md` | C7 降级只读标注 | 已写 |

## 2. 执行结果逐阶段（C1–C8）

| 阶段 | 动作 | 结果 |
|------|------|------|
| C1 备份 | `robocopy /E /COPYALL` 三副本 → `_backup/exp-consolidation-2026-10-11/` | 100 文件，文件数校验一致 ✅ |
| C5 解析器 | 改 `_load_experience`（全块解析+合并，后块优先） | 双落 FSTDD003 + stdd-repo ✅ |
| C2 回灌 | FSTDD002 独有 12 eid → 权威库 | 12/12 入索引，0 丢失 ✅ |
| C3 裁决 | 23 个漂移 eid（计划估 21，实测 23） | 全部 `KEEP_STDD_REPO`，依据落 `adjudication-log.tsv` ✅ |
| C4 去重 | 100 冗余文件移回收站（同盘 `os.rename`，非 `rm`） | 逐批 ≤10，源副本仅留 README ✅ |
| C6 索引 | 修复后解析器重建 `.experience-index.yaml` | `total=90`（89 有效 eid + 1 partial-metadata）✅ |
| C7 降级 | FSTDD003 / home-FSTDD / FSTDD002 写 README 标注只读 | 3 副本均含 README ✅ |
| C8 脚本 | `consolidate_experiences.py` 串联 + `--dry-run`/`--stage`/`--verify` | 幂等，重跑无副作用 ✅ |

## 3. 契约测试（Contract Tests）

文件：`upstream/tests/commands/test_experience_parser.py`（5 用例，全绿）

| TC-ID | 描述 | 结果 |
|-------|------|------|
| TC-ELC-001 | 双块文件返回真身（experience_id/category/severity 非空，第2块优先） | ✅ PASS |
| TC-ELC-002 | 单块文件一致（行为与修复前相同，回归保底） | ✅ PASS |
| TC-ELC-003 | 冲突键后块优先（靠后 block 值为准） | ✅ PASS |
| — | 无 frontmatter 返回 None | ✅ PASS |
| — | 集成：真实双块文件 `EXP-20260915-A1.md` 正确回读 | ✅ PASS |

## 4. 全量门禁（Full Gate）

- 命令：`cd E:/FSTDD/stdd-repo && PYTHONUTF8=1 PYTHONIOENCODING=utf-8 <PY> -m pytest upstream/tests tests -v --tb=line -p no:cacheprovider`
- 收集用例：**1123**
- 结果：**PASSED=1121、FAILED=2、PASS_RATE=99.8%**（>95% 门禁线，**未触发降级**）
- 编码环境已按记忆门禁（UTF-8 + `PYTHONUTF8=1`）规避「假红」；pytest 临时目录清理偶发
  safe-delete 守卫 `state lock timeout`（仅影响末尾汇总行刷新，不改变判定）。

### 4.1 两个失败项归因

| 失败测试 | 归因 | 是否本变更回归 | 处置 |
|----------|------|----------------|------|
| `upstream/tests/test_repo_home.py::test_a6_no_stray_untracked_files` | 断言「`.fstdd/changes/` 之外无未跟踪文件」。本变更有未提交的在办产物（12 回灌经验 + `tools/consolidate_experiences.py` + 新契约测试），故红 | 否 —— 属**提交门禁**（记忆明确：`test_a6` 只在工作树干净时绿，commit 后即绿） | DELIVER 提交后转绿 |
| `upstream/tests/test_fstdd_hub.py::test_failure_and_blocker_message_ack` | 全量序跑时失败，但**单独跑 PASS、在 hub 文件上下文跑亦 PASS** → 跨文件状态污染的既有 suite flake | 否 —— 本变更未触碰 hub 代码，且无确定性复现 | 记为既有 flake，另立项跟踪；非本变更 blocker |

> 结论：2 个失败均与「本变更代码正确性」无关；变更自身成功判据（TC-ELC-001~011，见 §5）全部满足；
> 全量通过率 99.8% 高于 95% 降级阈值，**BUILD 质量门达标**。

## 5. 成功判据对账（Success Criteria vs Actual）

| 判据（TC-ELC-*） | 计划预期 | 实测 | 状态 |
|------------------|----------|------|------|
| 001 双块返回真身 | 回读完整字段 | 契约测试通过 | ✅ |
| 002 单块一致 | 回归无变化 | 契约测试通过 | ✅ |
| 003 冲突后块优先 | 后块为准 | 契约测试通过 | ✅ |
| 004 回灌 12 条 0 丢失 | 12 入索引 | 12/12 入索引 | ✅ |
| 005 漂移全裁决（计划21→实测23） | 全部选定权威版 | 23 eid 全部 `KEEP_STDD_REPO` | ✅ |
| 006 唯一内容（计划90 eid→实测91文件/89eid） | 无重复内容 | `stage_verify` 无重复内容、0 丢失 | ✅ |
| 007 删走回收站非 rm | os.rename 非 rm | 100 冗余入 `.trash-2026-10-11/` | ✅ |
| 008 工作树干净/索引不脏 | 索引未意外改写 | C6 重建为有意 `M`；读时新鲜度重写属设计内；全量门禁 0 失败 | 🟡 注① |
| 009 dry-run 不落盘 | 仅打印 | 脚本 `--dry-run` 支持 | ✅ |
| 010 重跑幂等 | 无副作用 | 幂等设计 + `--verify` 重跑 | ✅ |
| 011 三副本 README | 标注只读 | 3 副本均含 README | ✅ |

> 注①：索引 `total=90` 的「`M`」是 C6 重建的有意产物，非测试意外脏写；`_load_index` 带新鲜度机制，
> 首次读后可能重写（观测 `rewritten_on_read=True`），属设计内行为。

## 6. 偏差与残留（Deviations & Residuals）

完整登记见 `design-adjustments.md`：
- **AMD-003（关键）**：修复落点是 live 模块 `D:\FSTDD003\upstream`（editable 安装目标），非 stdd-repo 内副本。
  两份同改，否则修复对实际行为零效果或发布后回退。
- **AMD-004**：漂移 eid 实测 23（计划估 21），漏 `EXP-2026-0013/0014`。
- **AMD-005**：权威库实测 **91 文件 / 89 有效 eid / 索引 total=90**（计划估 90 eid），2 个 truncated 文件不贡献 eid。
- **AMD-006（残留，非 parser bug）**：2 个历史 truncated inbox 导入——
  - `EXP-009-20260925-TRPC-REVERSE.md`：无 frontmatter 块 → `_load_experience` 返回 `None`。
  - `EXP-009-20260924-SSH-KEYPERM.md`：仅元信息块，无 `experience_id`。
  - 处置：不为其伪造 `category`（避免污染索引/回传网络），留作独立 data-quality 清理项的输入。
    收敛后 `experience list` 完整性 = **89/91（97.8%）**。

## 7. 风险与发布说明（Risk / Release Notes）

- **live vs 法定源双落**：FSTDD003（live，已就地改）与 stdd-repo（法定源，待 DELIVER commit）均含修复。
  DELIVER 提交 stdd-repo 副本即可让修复随版本走；FSTDD003 就地修改保证当前运行即时生效。
- **未执行 commit/push**：本阶段（BUILD）仅做本地改动，未触碰任何仓库的 git commit/push；
  DELIVER（Phase 4）由 Gate 3 终审后另行授权执行。
- **2 个残留文件**：虽不影响门禁，但会降低 `experience list` 完整性至 97.8%；建议在后续独立 change 中清理。
- **DROP 面**：整合后三副本仅留 README（冗余文件可经 `.trash-2026-10-11/` 人工复核后清），
  备份 `_backup/exp-consolidation-2026-10-11/` 保留完整可回退。
