# Code Structure Delta — 2026-10-11-share-hardening-audit-fixes
> 生成时间: 2026-10-12T12:30:03+00:00 | Git commit: a4673cc
> 置信度: 0.70 (AI-generated — 以源代码为准)

## 变更文件

- `caveman_summary.txt`

<!-- 以下为人工补全（CLI 自动段只列出 change 目录内的 1 个文件，判据过窄；见 ADJ-007） -->

## 变更文件（人工补全，以 `git status` + `git diff --stat` 为准）

### 修改（8）
- `install.sh`（+33/-8）— `--py`/`--platform` 参数校验 + 未知参数 WARN
- `skills/fstdd-fin/SKILL.md`（+3/-2）— 红线 7 / 交付清单 / 测试维度 三处补充
- `tools/install_workbuddy_skills.py` — `strip_frontmatter` 逐行扫描、`_render_template`（StrictUndefined）、三常量外置为模板 + 回落、去重复 `REPO_ROOT`
- `tools/share_experience.py` — 3 条脱敏规则、`OUTBOUND_RESIDUAL_RE` 同源、`_validate_remote_path`（白名单 + 拒 `..` + 拒前导 `-`）、`_check_token_file_permissions`、`SCP_SYNTAX_RE` 重命名、`publish(pre_staged=)`
- `tools/verify_workbuddy_skills.py` — 冒烟 `SMOKE_TIMEOUT`（默认 30s，可 env 覆盖，非法值回落）
- `upstream/fstdd/cli/utils.py` — `MAX_SOURCE_DEPTH` + `_find_source_root()`
- `upstream/tests/test_silent_share.py` — publish 测试桩 3 处同步 `pre_staged`
- `tests/test_experience_sync_tc_traceability.py` — change 目录支持 `archive/` 回退

### 新增（6）
- `tools/templates/security_note_deliver.md.j2`
- `tools/templates/security_block_deliver.md.j2`
- `tools/templates/upgrade_duty.md.j2`
- `tests/test_share_hardening.py`（15 函数 / 31 用例）
- `tests/test_install_script_robustness.py`（15 函数 / 15 用例）
- `tests/test_share_hardening_tc_traceability.py`（3 函数 / 3 用例）

### change 目录内产出
- `slices.md` / `tasks.md` / `phase-context.md` / `test-report.md`
- `pending-adjustments.yaml` / `design-adjustments.yaml`
- `audit/except-points.yaml`（裸 except 审计活表，承接 25 点）
- `code-structure-delta.md`（本文件）

## 新增/变更的公共符号
- `tools/share_experience.py`：`_REMOTE_PATH_OK_RE`、`_validate_remote_path`、`_check_token_file_permissions`、`SCP_SYNTAX_RE`（原 `SCP_LIKE_RE`）、`publish(pre_staged=)`
- `tools/install_workbuddy_skills.py`：`TEMPLATES_DIR`、`_render_template`、`_SECURITY_NOTE_DELIVER_FALLBACK`、`_SECURITY_BLOCK_DELIVER_FALLBACK`、`_UPGRADE_DUTY_FALLBACK`、`_POLICY_CTX`
- `tools/verify_workbuddy_skills.py`：`SMOKE_TIMEOUT`、`_smoke_timeout`
- `upstream/fstdd/cli/utils.py`：`MAX_SOURCE_DEPTH`、`_find_source_root`

