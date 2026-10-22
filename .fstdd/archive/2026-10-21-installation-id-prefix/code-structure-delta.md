# Code Structure Delta — 2026-10-21-installation-id-prefix
> 生成时间: 2026-10-22T14:28:19+00:00 | Git commit: a489420
> 置信度: 0.70 (AI-generated — 以源代码为准)
> 备注: `fstdd structure delta` 自动扫描产出为空/错乱（与 `code-structure/deltas/` 下 10 份历史 delta 一致的工具缺陷），
> 本节由人工按 `git status --porcelain` 补齐，清单与 working tree 实况一致。

## 变更文件

### 生产代码 — CLI 内核（`upstream/fstdd/`）

| 文件 | 性质 | 说明 |
|---|---|---|
| `cli/utils.py` | MODIFIED | 新增 `INSTALLATION_ID_RE` 与 `read_installation_id()`：installation_id 形状的**唯一事实来源**，生成端（`init.py`）与读取端（`experience.py`）共用同一常量 |
| `cli/commands/init.py` | MODIFIED | 新增 `_generate_installation_id()` / `_get_prefix()` / `_ensure_installation_id()`；`cmd_init` dry-run 分支打印真实预览（不再打印假随机值）；`_post_init_self_check` 回读实际写入值 |
| `cli/commands/experience.py` | MODIFIED | `_next_id()` 增加 `project_root` 参数，有 installation_id 时产出 `{IID}-EXP-{year}-{NNNN}`；`_read_installation_id` 退化为 `utils.read_installation_id` 转发 |
| `cli/commands/upgrade.py` | MODIFIED | `_write_version_yaml()` 由覆盖写改为**读-合并-写**，否则 `fstdd upgrade` 会抹掉 `installation_id` |
| `cli/__init__.py` | MODIFIED | `fstdd init` 暴露 `--prefix` 参数 |

### 下游枚举口径（`tools/` 与 hooks）

| 文件 | 性质 | 说明 |
|---|---|---|
| `tools/share_experience.py` | MODIFIED | `glob("EXP-*.md")` → `glob("*.md")` 排除 dotfiles。**经验回传通道**，漏读会导致静默只推旧格式经验 |
| `tools/fstdd003_daily_share.py` | MODIFIED | 同上（重复提交由 submitted 日志去重） |
| `tools/audit_experience_baseline.py` | MODIFIED | `INDEX_ITEM_RE` 由「允许一段前缀」放宽为「允许任意多段前缀」 |
| `upstream/.fstdd/hooks/session-end.py` | MODIFIED | 经验计数由 `EXP-*.md` 改为 `*.md` 排除 dotfiles |

### 测试

| 文件 | 性质 | 说明 |
|---|---|---|
| `upstream/tests/commands/test_installation_id.py` | NEW | 40 例，覆盖 IID/EID 全部 14 个 TC，含判别力验证 |
| `upstream/tests/commands/test_init.py` | MODIFIED | `test_init_dry_run_creates_nothing` 由零断言 `try/except: pass` 重写为真断言 |
| `upstream/tests/commands/test_experience_glob_consistency.py` | MODIFIED | 门禁扩围：扫描 `cli/` + `tools/` + `.fstdd/hooks/` 三棵树 |
| `tests/test_installation_id_traceability.py` | NEW | 4 例，固化 `ci.py` 硬编码 `tests_dir` 的框架缺陷 + 冻结 14 个 TC 清单 |

### 规范（canonical 双轨）

| 文件 | 性质 |
|---|---|
| `.fstdd/canonical/proposals/2026-10-21-installation-id-prefix.yaml` | NEW |
| `.fstdd/canonical/specs/code/installation-identity.yaml` | NEW |
| `.fstdd/canonical/specs/code/experience-id-generation.yaml` | NEW |
| `.fstdd/canonical/specs/agent/installation-identity.yaml` | NEW |
| `.fstdd/canonical/specs/agent/experience-id-generation.yaml` | NEW |

### 经验库

| 文件 | 性质 |
|---|---|
| `.fstdd/experiences/EXP-2026-0038.md` | NEW（merge-vs-overwrite 配置写入口） |
| `.fstdd/experiences/EXP-2026-0039.md` | NEW（ID 格式加前缀打穿下游通配） |
| `.fstdd/experiences/EXP-2026-0040.md` | NEW（写读口径不一致 → 配了不生效） |
| `.fstdd/experiences/.experience-index.yaml` | MODIFIED（last_id 37 → 40） |

## 模块影响

- **无新增模块**，无目录层级变化。
- `upstream/fstdd/cli/utils.py` 的公共面扩大（新增 2 个导出符号），调用方仅 `init.py` 与 `experience.py`。
- `.fstdd/version.yaml` schema 增加可选键 `installation_id`（本仓自身仍未设置，见 FU-004）。
