# 实现任务清单 — 2026-10-21-installation-id-prefix

> 状态图例：✅ 完成 ｜ ⚠️ 完成但有已知缺口 ｜ ⬜ 未做

## S1 ｜ installation_id 生成与写入

| # | 任务 | 状态 | 证据 |
|---|---|---|---|
| 1.1 | `utils.INSTALLATION_ID_RE` 单一常量（生成端/读取端共用） | ✅ | `upstream/fstdd/cli/utils.py` |
| 1.2 | `init._generate_installation_id`（`secrets.token_hex(4)`） | ✅ | TC 单元用例 |
| 1.3 | `init._get_prefix`（`--prefix` 校验 + 项目名清洗 + `FSTDD` 兜底） | ✅ | `test_get_prefix_exact_expectations`（6 组钉死） |
| 1.4 | `init._ensure_installation_id`（合并写 / 不覆盖 / 坏值重生成 / 损坏不写） | ✅ | TC-IID-001/004/006/007 |
| 1.5 | `cli/__init__.py` 注册 `--prefix` | ✅ | `test_cli_parser_exposes_prefix_flag`（subprocess `--help`） |
| 1.6 | `_post_init_self_check` 打印实际生效值 | ✅ | TC-IID-005（正向 + 反向） |
| 1.7 | dry-run 分支展示「将生成 / 已存在」而非随机假 ID | ✅ | `test_dry_run_previews_without_writing` |

## S2 ｜ `_next_id` 使用前缀

| # | 任务 | 状态 | 证据 |
|---|---|---|---|
| 2.1 | `utils.read_installation_id`（形状校验 + stderr 告警） | ✅ | TC-EID-002（6 种坏值） |
| 2.2 | `experience._next_id(index, project_root=None)` | ✅ | TC-EID-001/002/003 |
| 2.3 | `_cmd_add` 透传 `project_root` | ✅ | TC-EID-004（全链路） |
| 2.4 | 确认 `_rebuild_index` 数字提取兼容带前缀 ID | ✅ | TC-EID-007（含 HEX 段反例） |

## S3 ｜ `upgrade` 合并写

| # | 任务 | 状态 | 证据 |
|---|---|---|---|
| 3.1 | `_write_version_yaml` 改「读-合并-写」 | ✅ | TC-IID-004（`future_field` 反向断言） |
| 3.2 | `_read_version_yaml` 损坏容错（避免写侧容错变死代码） | ✅ | 静态审查 |

## S4 ｜ 下游枚举口径 + 门禁扩围

| # | 任务 | 状态 | 证据 |
|---|---|---|---|
| 4.1 | `tools/share_experience.py` 改任意 `*.md` | ✅ | FSD-004 门禁（扩围后扫到） |
| 4.2 | `tools/fstdd003_daily_share.py` 同上 | ✅ | 同上 |
| 4.3 | `tools/audit_experience_baseline.py` 正则允许多段前缀 | ✅ | 手工核 regex |
| 4.4 | `upstream/.fstdd/hooks/session-end.py` 对齐 `hooks.py` 内嵌版本 | ✅ | 同上 |
| 4.5 | FSD-004 门禁扫描根扩到 `tools/` + `.fstdd/hooks/`，读文件改 `utf-8-sig` | ✅ | 门禁 11 例全绿 |

## S5 ｜ 证据链与经验

| # | 任务 | 状态 | 证据 |
|---|---|---|---|
| 5.1 | `audit/except-points.yaml` 刷新（25 点，零漂移，新增吞异常点 0） | ✅ | `test_aud_except_audit` + `test_grd_001` |
| 5.2 | 经验沉淀 `EXP-2026-0038/0039/0040` | ✅ | `.fstdd/experiences/` |
| 5.3 | 规格/设计/测试方案与实现对齐（评审后 4 轮修订） | ✅ | 见 `design-adjustments.yaml` |

## 已知缺口

| 项 | 说明 |
|---|---|
| 无 installation_id 碰撞检测 | `secrets.token_hex(4)` 2^32 空间，不做全局查重（proposal 已登记为非目标） |
| `_load_experience` 跳过无 frontmatter 的 `.md` | 2026-09 起既有语义，本 change 不改；TC-EID-005 已按此调整 |
| `tools/heartbeat.py` 带 BOM | 既有问题，本 change 只在门禁里做 `utf-8-sig` 兼容，未改该文件 |
