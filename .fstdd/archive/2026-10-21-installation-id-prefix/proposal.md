# init.py 生成 installation_id + _next_id() 使用前缀，消除多项目递增编号撞号

<!-- source_hash: 2d26fb929a300754 -->
<!-- generated_at: 2026-10-22T14:29:30+00:00 -->
<!-- canonical: canonical/proposals/2026-10-21-installation-id-prefix.yaml -->

## Why

`_next_id()` 使用全局递增 `EXP-{year}-{NNNN}`，每个 `fstdd init` 的项目各自 从种子库（18 条）复制一份、各自递增编号，互不感知。当两个项目都走到 `EXP-2026-0019` 时，两份经验内容完全无关却同 ID，合并时必然冲突。 实测（2026-10-21）：ccreits-site 项目的 0019~0022/0030/0031 与上游仓库 `.fstdd/experiences/` 的同 ID 条目内容完全不同，6 条撞号。

## What Changes

- `init.py` 的 `cmd_init` 在创建 `.fstdd/` 骨架后、`_register_project` 之前， 生成 `installation_id`（`secrets.token_hex(4).upper()`，格式 `{PREFIX}-{8HEX}`， PREFIX 由 `--prefix` 参数或项目名自动派生），写入 `.fstdd/version.yaml` 新增字段 `installation_id`。
- `experience.py` 的 `_next_id()` 改为从 `.fstdd/version.yaml` 读取 `installation_id`，返回 `f"{install_id}-EXP-{year}-{NNNN:04d}"`。 `version.yaml` 不存在或无 `installation_id` 字段时，回落到旧的 `EXP-{year}-{NNNN}` 格式（向后兼容）。
- `experience.py` 的 `_iter_experience_files()` 与 `_rebuild_index()` 确认可识别带前缀的文件名（`WBCC-*-EXP-*` / `FSTDD00X-*-EXP-*`）， 从 frontmatter `experience_id` 或文件名 stem 提取完整 ID。 已有实现（2026-09-17 修复）已支持任意 `.md` + frontmatter `experience_id`， 需确认带前缀的文件名 stem 也能被正确提取。
- `init.py` 的 `_post_init_self_check` 打印 `installation_id` 的**实际生效值** （形状合法才打 ✅，否则打 ⚠️ 未写入）。`version.yaml` 模板 （`upstream/.fstdd/version.yaml`）**不改**：该字段由 init 运行时生成， 模板不参与 `FILES_TO_COPY` 复制清单，写空值既无效果又会被误读成「已配置」。
- `upgrade.py` 的 `_write_version_yaml` 从「整体覆盖」改为「读既有 → 合并 → 写」。 否则 `fstdd upgrade` 会把 installation_id 连同其它新增字段一起静默抹掉 （2026-10-22 实测故障路径），撞号缺陷复发且零报错。
- 下游枚举口径统一为「任意 `*.md`（排除 `.` 开头）」：`tools/share_experience.py` （回传通道）、`tools/fstdd003_daily_share.py`、`tools/audit_experience_baseline.py` 的 `INDEX_ITEM_RE`、`upstream/.fstdd/hooks/session-end.py` 四处原有 `EXP-*` 前缀假设，带前缀 ID 后会全部漏读。同时把 FSD-004 门禁的扫描根从 `fstdd/cli` 扩到 `tools/` 与 `.fstdd/hooks/`，让同类回归立刻变红。

## Capabilities

<!-- 机读声明：`fstdd ci check-failures` 的 (b) 范围检查只认 `- capability: <name>` 行，
     而 `fstdd canon generate` 不产出该行（见 FU-005）。每次重新生成 Human View 后需手工补回。 -->
- capability: installation-identity
- capability: experience-id-generation

### New Capabilities

- **installation-identity**：每个 `fstdd init` 的项目获得一个全局唯一的 `installation_id`， 写入 `.fstdd/version.yaml`，作为该项目所有经验条目 ID 的前缀。

### Modified Capabilities

- **experience-id-generation**：`_next_id()` 产出的 ID 从 `EXP-{year}-{NNNN}` 变为 `{installation_id}-EXP-{year}-{NNNN}`，保证多项目间不撞号。

## Success Criteria

- [ ] `fstdd init` 后 `.fstdd/version.yaml` 含 `installation_id` 字段（非空）
- [ ] `installation_id` 格式为 `{PREFIX}-{8HEX}`（如 `STDD-A1B2C3D4`），PREFIX 恒为 `[A-Z0-9]{2,8}` 且 ID 恒为两段
- [ ] `fstdd experience add` 产出的 ID 含 installation_id 前缀
- [ ] 既有项目（无 installation_id）的 `experience add` 回落到旧格式 `EXP-{year}-{NNNN}`
- [ ] `fstdd experience list` 能列出带前缀的条目
- [ ] `fstdd upgrade` 后 installation_id 仍在（version.yaml 合并写），且未登记的既有字段一并存活
- [ ] 回传通道（tools/share_experience.py）能枚举到带前缀的新经验
- [ ] 新增回归测试全绿
- [ ] 既有 upstream/tests 全量不退化
