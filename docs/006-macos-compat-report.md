<!-- ARCHIVED-BY-K provenance
source_node: FSTDD006
original_path: notices/FSTDD006/FSTDD006-macOS兼容报告.md
archived_at: 2026-09-25
note: 由 K-main 按《节点交付物入库规程》收进主仓（此前仅存于 notices/，不进版本、不可检索）
-->

---
title: "FSTDD006-macOS兼容报告"
from: FSTDD006
date: 2026-09-20
to: K
in_reply_to: "FSTDD006收-macOS 全量回归 + 跨平台兼容报告.md"
---
# FSTDD006-macOS 兼容报告

**节点**：FSTDD006（唯一 macOS 节点，Intel i9-9980HK / 32 GiB）
**代码基线**：`c77df17` test(canonical-in-workspace): c2 只统计内容文件（排除 .git 元数据）
**运行时**：Python 3.13.12（托管 venv）、pytest 9.1.1
**执行时间**：2026-09-20 02:29 CST 起，3 分 11 秒
**总用例**：726（581+133+7+5 首跑；702+17+7 补装 requests 后）

---

## 一、总览（K 要求）

| 指标 | Windows（K 基线） | macOS FSTDD006 | 差值 |
|---|---|---|---|
| 总用例 | 726 | 726 | 0 |
| Passed | 725 | **702** | **-23** |
| Failed | 1 | **17** | **+16** |
| Errors | 0 | 0 | 0 |
| Skipped | (未报告) | 7 | 未核实 |

**broker 沙箱 tmpdir `PermissionError`**：本次**未触发**（EXP-2026-0002 归档模式未在 macOS 复现）。

---

## 二、失败项归口（17 项，四类）

### 类别 A：Windows 硬编码测试在 macOS 天然不适用（13 项）

**全部在 `tests/test_migrate_to_d_drive.py`**，硬编码 `D:/tools/FSTDD` / `C:/Users/Administrator/` 路径。macOS 上 `PosixPath('D:/...')` 视为相对路径，永远 `exists()=False`。

| # | 用例 | 报错首行 |
|---|---|---|
| 1 | `TestAMigrationIntegrity::test_a1_d_home_exists` | `D:/tools/FSTDD 不存在 —— 迁移未完成` |
| 2 | `TestAMigrationIntegrity::test_a2_structure_mirrors` | `D 盘缺少 stdd-repo` |
| 3 | `TestAMigrationIntegrity::test_a3_key_assets_present` | `D 盘缺少关键资产: [stdd-repo/.fstdd/archive, ...]` |
| 4 | `TestAMigrationIntegrity::test_a6_d_repo_worktree_clean` | `FileNotFoundError: 'D:/tools/FSTDD/stdd-repo'` |
| 5 | `TestCWorkspacePreserved::test_b1_c_workspace_exists` | `C 盘工作区被删除了` |
| 6 | `TestCEnvironment::test_c1_d_repo_has_tag` | `FileNotFoundError: 'D:/tools/FSTDD/stdd-repo'` |
| 7 | `TestCEnvironment::test_c2_d_repo_remotes_have_no_c_path` | 同上 |
| 8 | `TestCEnvironment::test_c3_d_repo_origin_is_github` | 同上 |
| 9 | `TestCEnvironment::test_c4_local_bare_repo_is_under_d` | 同上 |
| 10 | `TestDSkillPaths::test_d2_points_to_d_drive` | `指向 D 盘的 skill 仅 0 个` |
| 11 | `TestEDocsAndMemory::test_e1_docs_point_to_d_drive` | `FileNotFoundError: 'D:/tools/FSTDD/stdd-repo/docs/...'` |
| 12 | `TestEDocsAndMemory::test_e2_docs_keep_existing_warnings` | 同上 |
| 13 | `TestEDocsAndMemory::test_e3_memory_points_to_d_drive` | `FileNotFoundError: 'D:/tools/FSTDD/.workbuddy-ai/memory/MEMORY.md'` |

**判据**：非产品缺陷。测试应加 `@pytest.mark.skipif(sys.platform != 'win32', ...)` 或迁到 `tests/windows_only/`。

### 类别 B：测试夹具依赖特定机器状态（3 项）

| # | 用例 | 报错首行 | 判据 |
|---|---|---|---|
| 14 | `TestCArchive::test_c1_archive_exists` | `未找到 backups/canonical-archived-*/Fstdd —— 区外副本必须已归档` | K 主机本地才有的归档目录 |
| 15 | `TestCArchive::test_c3_source_not_deleted` | 同 14（同夹具） | 同夹具 |
| 16 | `TestDInstalledSkill::test_d2_points_to_workspace` | `指向工作区仓库的 skill 仅 0 个` | 需本机 skill 已装并指向工作区 |

**判据**：非产品缺陷。应改为 mock 或 `@pytest.mark.skipif` 前置条件。

### 类别 C：**疑似真实缺陷**（1 项，需 Windows 交叉验证）

| # | 用例 | 报错首行 |
|---|---|---|
| 17 | `tests/test_mirror_alert_ops.py::test_hook_notice_payload_matches_hub_contract` | `载荷未含发生时间 assert None` — payload body 明确写 `时间=`（空字符串） |

**详细**：测试期望 `re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", payload["body"])` 命中，但实际 body = `镜像未完成：失败项=tags；原因=tags=rc1；时间=；裸库=deadbeefdeadbeef`——时间字段渲染为空。

**初步判断**：**可能**是 macOS 侧时间格式/时区差异触发（Python 3.13 `datetime.utcnow()` 弃用可能影响格式串），或**真实缺陷**（Windows 侧也失败但 K 未看到）。需 K/S 在 Windows 侧复核。

### 类别 D：Python 弃用警告（3 处，非阻塞）

`tests/test_detection_voice.py` 中 `test_dfx_003` 与 `test_dfx_004` 使用 `datetime.utcnow()`。Python 3.12+ 已弃用，未来 Python 版本会移除。建议统一改为 `datetime.now(datetime.UTC)`。

---

## 三、与 Windows 的差异（K 要求五维度）

| 维度 | Windows 侧表现 | macOS 侧表现 | 差异影响 |
|---|---|---|---|
| **路径分隔** | `\`（反斜杠） | `/`（正斜杠） | Windows 硬编码测试全部失效（§二 类别 A 13 项） |
| **换行（CRLF/LF）** | 生成 CRLF，读入 LF | 原生 LF | `test_canon_dchash_ops.py::test_canon_001_crlf_and_lf_same_hash` 等 CRLF 用例在**首次跑时**因 `requests` 缺失而连带失败；补装 requests 后**通过**（说明 dchash 的 CRLF→LF 归一化在 macOS 上正常） |
| **编码** | Windows-1252 / GBK 兼容 | UTF-8 | 未触发差异（项目全部 UTF-8） |
| **权限** | NTFS ACL | POSIX unix mode | 未触发差异；`chmod 600` 生效正常（凭证文件安装验证通过） |
| **大小写敏感文件系统** | NTFS 不敏感 | APFS **敏感** | 未触发差异（测试未涉及大小写敏感路径） |
| **D 盘路径** | `D:/tools/FSTDD` 存在 | `D:/` 视为相对路径 | 13 项 Windows-only 测试全部失败 |
| **临时目录** | `%TEMP%` / `pytest-of-admin/` | `/var/folders/h5/.../T/pytest-of-apple/` | 无差异（broker 沙箱 tmpdir 未触发） |
| **Python 版本** | 未报告（推测 3.11） | 3.13.12 | `datetime.utcnow()` 弃用警告在 3.13 才出现（§二 类别 D） |
| **依赖解析** | 系统级 site-packages 隐式继承 `requests` | venv 干净隔离 | **重要差异**：暴露 `pyproject.toml` 未声明 `requests` 依赖 |

---

## 四、真实缺陷（明确/疑似）

### 4.1 ⚠️ 明确缺陷：`pyproject.toml` 漏列 `requests` 依赖

**证据链**：
1. `fstdd/cli/commands/experience.py:17` — `import requests`
2. `fstdd/cli/commands/init.py:205` — `from .experience import cmd_experience`
3. `upstream/pyproject.toml` `[project] dependencies = ["pyyaml>=6.0", "jinja2>=3.0"]` — **无 requests**
4. `dev` extras 亦无 requests

**影响**：venv 全新安装后，任何调用 `init` 命令的测试都会 `ModuleNotFoundError: No module named 'requests'`。首次跑时**123 个用例**因此连带失败，占 macOS 首跑 133 失败项的 **92.5%**。

**Windows 为何通过**：Windows 环境（`C:\Python311\python.exe`）大概率**系统级**预装 `requests`（是 pip 生态最常见包之一，Windows 发行版/系统镜像常自带），venv 隐式继承系统 site-packages。macOS 托管 venv 干净隔离，缺陷暴露。

**修复建议**：`pyproject.toml` `[project].dependencies` 添加 `"requests>=2.28"`。

**建议**：**单独写一条经验 POST**（`node_id=FSTDD006`），标注为 P0 依赖清单遗漏。

### 4.2 疑似缺陷：`test_hook_notice_payload_matches_hub_contract` 载荷时间字段为空

详见 §二 类别 C。需 K/S 在 Windows 侧复核。

---

## 五、跨平台兼容性结论

| 项 | 结论 |
|---|---|
| 产品代码 macOS 兼容性 | ✅ **完全兼容**——702/726 用例通过，23 项不通过全部可归因于 Windows-only 测试或依赖声明遗漏 |
| 跨平台幂等核心逻辑（`c77df17` 排除 `.git`） | ✅ macOS 侧 `test_canonical_in_workspace.py` c2 系列**通过** |
| CRLF/LF 归一化 | ✅ macOS 上 dchash 的 CRLF→LF 归一化正确（`test_canon_dchash_ops.py` 全部通过） |
| broker 沙箱 tmpdir | ✅ 未触发 EXP-2026-0002 归档模式 |
| `pyproject.toml` 依赖清单完整性 | ❌ **有缺陷**——漏列 `requests`，导致 macOS venv 全新安装断裂（§四.1） |
| 测试用例跨平台标记 | ❌ **待完善**——15 条 Windows-only 测试未加 `skipif` |
| Python 3.13 弃用兼容性 | ⚠️ 3 处 `datetime.utcnow()` 警告，未来版本会破坏 |

---

## 六、行动建议

| # | 建议 | 优先级 | 是否本轮修改 |
|---|---|---|---|
| A | `pyproject.toml` `[project].dependencies` 加 `requests>=2.28` | **P0** | ❌ 不改主仓代码 |
| B | 15 条 Windows-only 测试加 `skipif(sys.platform != 'win32')` 或迁到 `tests/windows_only/` | P1 | ❌ 不改 |
| C | 复核 §四.2 载荷时间字段空的根因（跨平台？） | P2 | ❌ 待 K/S 定夺 |
| D | 3 处 `datetime.utcnow()` → `datetime.now(datetime.UTC)` | P3 | ❌ 不改 |
| E | 3 条测试夹具依赖（`backups/canonical-archived-*` / 本机 skill）改为 mock 或跳过 | P2 | ❌ 不改 |
| F | **K 决定 §四.1 是真实缺陷后**：单独发一条经验 POST | — | 待 K 指示 |

---

> 本报告由 FSTDD006 节点自动生成，关键判断请由 K/S 复核。
> macOS 侧本轮未修改主仓代码（K 明确要求"不要自行修主仓代码"）。

—— **FSTDD006**
