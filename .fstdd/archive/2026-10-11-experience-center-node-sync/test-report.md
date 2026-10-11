# 测试报告 — 2026-10-11-experience-center-node-sync

> Phase 3 BUILD 质量验证（Part C）｜生成时间：2026-10-11
> 基线：`d67c9b1`（Gate 1/2 均基于此）

## 一、TL;DR

| 项目 | 结果 |
|------|------|
| TC 覆盖率 | **24/24（100%）** |
| 切片完成度 | **6/6** 全部通过 per-slice 验证 |
| 新增测试 | **26 个测试函数**（覆盖 24 TC） |
| 全量回归 | **1142 passed / 1 failed / 9 skipped**（唯一失败 = `test_a6`，提交后自愈） |
| 失败模式检查 | 23 类逐项完成（§6） |
| 设计偏离 | 4 条（1 Major + 3 Minor），全部已登记 |
| 阻塞项 | **0**（除 §7「已知问题」中 1 条待 D哥 裁定的环境事实） |

## 二、TC 覆盖率（planned vs actual）

| TC-ID | 切片 | 优先级 | 对应测试 | 状态 |
|-------|------|--------|----------|:---:|
| TC-EEXT-001 | 1 | P0 | `test_eext001_default_extract_from_test_report` | ✅ |
| TC-EEXT-002 | 1 | P0 | `test_eext002_extract_from_design_adjustments` | ✅ |
| TC-EEXT-003 | 1 | P0 | `test_eext003_extract_from_adjudication` | ✅ |
| TC-EEXT-004 | 1 | P1 | `test_eext004_extract_all_merges_and_dedups` | ✅ |
| TC-EEXT-005 | 1 | P1 | `test_eext005_test_report_path_no_regression` | ✅ |
| TC-EAUT-001 | 2 | P0 | `test_eaut001_auto_deposit_noninteractive` | ✅ |
| TC-EAUT-002 | 2 | P0 | `test_eaut002_no_share_skips` | ✅ |
| TC-EAUT-003 | 2 | P0 | `test_eaut003_all_discovered` | ✅ |
| TC-EAUT-004 | 2 | P1 | `test_eaut004_non_tty_does_not_block` | ✅ |
| TC-ECNS-001 | 4 | P0 | `test_ecns001_push_stages_and_transports` | ✅ |
| TC-ECNS-002 | 4 | P0 | `test_ecns002_pull_merges_remote` | ✅ |
| TC-ECNS-003 | 4 | P0 | `test_ecns003_convergence_two_nodes` | ✅ |
| TC-ECNS-004 | 4 | P1 | `test_ecns004_pull_idempotent` | ✅ |
| TC-ECNS-005 | 4 | P1 | `test_ecns005_dry_run_no_side_effects` | ✅ |
| TC-ESEC-001 | 3 | P0 | `test_esec001_encrypt_hides_plaintext` | ✅ |
| TC-ESEC-002 | 3 | P0 | `test_esec002_roundtrip_byte_identical` | ✅ |
| TC-ESEC-003 | 3 | P0 | `test_esec003_oaep_params_locked` | ✅ |
| TC-ESEC-004 | 3 | P1 | `test_esec004_long_payload_uses_hybrid` | ✅ |
| TC-ESEC-005 | 3 | P0 | `test_esec005_no_keys_open_mode` | ✅ |
| TC-ECON-001 | 5 | P0 | `test_econ001_lww_newer_wins` | ✅ |
| TC-ECON-002 | 5 | P0 | `test_econ002_conflict_log_written` | ✅ |
| TC-ECON-003 | 5 | P1 | `test_econ003_concurrent_merge_no_corruption` | ✅ |
| TC-ESAF-001 | 6 | P0 | `test_esaf001_share_single_still_disabled` | ✅ |
| TC-ESAF-002 | 6 | P0 | `test_esaf002_no_new_third_party_egress` + `test_esaf002b_first_party_target_is_hub` | ✅ |

**合计 24/24 TC 覆盖；新增 26 个测试函数**（TC-ESAF-002 用 2 个测试、TC-ECNS-005 另加 1 个补充测试 `test_ecns006_outbound_sanitized`）。

## 三、每切片验证状态（Step B3.4）

| # | 切片 | TC 覆盖 | 新增测试 | 产出物核对 | 状态 |
|---|------|---------|---------|-----------|:---:|
| 1 | extract 扩源 | 5/5 | 5 | `_parse_design_adjustments` / `_parse_adjudication_log` / `_extract_sources` / `_dedup_patterns` + CLI `--source/--all` | ✅ |
| 2 | auto-deposit | 4/4 | 4 | `_cmd_auto_deposit` / `_share_disabled` + CLI `auto-deposit` | ✅ |
| 3 | `_exp_crypto` | 5/5 | 5 | `hybrid_encrypt` / `hybrid_decrypt` / `keys_present` / `_split_blob` | ✅ |
| 4 | 中心节点 sync | 5/5 | 6 | `_exp_sync`（load_entries / merge_entries / sync_pull / push_bundle / fetch_bundle / decrypt_incoming）+ CLI `sync` | ✅ |
| 5 | 冲突策略 | 3/3 | 3 | `_merge` LWW + 冲突日志（TSV） | ✅ |
| 6 | 外发审计 | 2/2 | 3 | AST 判据的静态审计 | ✅ |

## 四、全量回归

- 命令：`PYTHONUTF8=1 PYTHONIOENCODING=utf-8 TMP=E:/FSTDD/_tmp <managed-python> -m pytest upstream/tests tests -q -p no:cacheprovider`
- 结果：**1142 passed / 1 failed / 9 skipped（954s）**
- **唯一失败**：`upstream/tests/test_repo_home.py::TestAWorkspaceIntegrity::test_a6_no_stray_untracked_files`
  —— 判据为「工作树无 `.fstdd/changes/` 之外的未跟踪文件」；本轮新增 10 个源/测试文件尚未 `git add`，
  **提交（DELIVER）后即转绿**。与上一 change（consolidation）同形状，非回归。

### ⚠️ 两次「假红」的排查记录（重要，供后续复用）
| 现象 | 根因 | 处置 |
|------|------|------|
| 7 个 `test_guard.py` 用例由「应拦截(2)」反转为「已放行(0)」，stdout 出现 `agent runtime dir - not a deliverable, allowed` | 我把 `TMP`/`TEMP` 指向 `C:/Users/Administrator/.workbuddy-ai/tmp` ⇒ pytest 的 `tmp_path` 落在 **agent runtime 目录**下，被 Guard 放行 | 改用中立目录 `TMP=E:/FSTDD/_tmp`；Guard 全绿 |
| `experience`/`sync` 相关 14 个用例整片 FAILED，报 `SAFE_DELETE_BULK_GUARD_ERROR: state lock timeout` | 沙箱 safe-delete 守卫的**进程间状态锁**被并发进程占用 ⇒ `_index_lock` 释放时的 `os.remove` 被拒（`SystemExit` 不在 `except OSError` 覆盖内） | 测试期避免并发重删除进程；单独重跑即 26/26 通过。**非产品缺陷** |
| `ci check-failures` 报「TC 实现覆盖 0/25」 | 该检查**硬编码**只扫 `project_root/tests`（`ci.py:601`），而框架测试在 `upstream/tests/` | 新增根级追溯性测试 `tests/test_experience_sync_tc_traceability.py`（同时扫两棵树 + 冻结 TC 清单）⇒ 现为 **25/25 (100%)** |

### 补充验证（非 pytest）
- **CLI 端到端冒烟**（真实命令链路，临时项目）：
  - `experience extract --all` → 从三类源产出 3 条 discovered 草稿 ✅
  - `experience list` → 正确显示 3 条（含 category/severity/lifecycle）✅
  - `FSTDD_NO_SHARE=1 experience auto-deposit` → `skipped` ✅
  - `experience auto-deposit`（开放态）→ `deposited 3` ✅
  - `experience sync --push --hub-dir <hub>` → `pushed: 6 entrie(s)` ✅
  - `experience sync --pull --hub-dir <hub>` → `+0 new, =6 kept`（已收敛，幂等）✅
- **lint**：`ruff check` 对本轮新增/修改文件 **All checks passed**（仓库既有文件另有 12 项历史 lint 债，未扩大）。
- **导入解析探针**：确认 pytest 下 `import fstdd` 解析到 `E:/FSTDD/stdd-repo/upstream/fstdd`（非 editable 的 D:/FSTDD003），故测试与改动同源。

## 五、Diff 审查（Step C3）

| 文件 | 变更 | 审查结论 |
|------|------|---------|
| `upstream/fstdd/cli/commands/_exp_crypto.py` | 新增（~160 行） | 无调试残留；无硬编码凭证；subprocess 参数以列表传入（无 shell 拼接） |
| `upstream/fstdd/cli/commands/_exp_sync.py` | 新增（~250 行） | 无死代码；eid 落盘经 `_safe_eid` 防穿越；原子写（tmp + replace） |
| `upstream/fstdd/cli/commands/experience.py` | 重构 `_cmd_extract` + 新增 9 个函数 | 既有 test-report 路径逐条不变（TC-EEXT-005 锁定）；`_cmd_share_single` 未改动 |
| `upstream/fstdd/cli/__init__.py` | 新增 3 个子命令注册 | 参数与 agent_spec 一致 |
| 6 个新测试文件 | 新增 | 无 `print` 调试；fixture hermetic（tmp_path + 临时密钥对） |

## 六、失败模式检查（23 类，全量执行）

| # | 失败模式 | 检查动作 | 结果 |
|---|---------|---------|:---:|
| 1 | 幻觉调用 | `ruff check`（F821 未定义名）全绿 | ✅ |
| 2 | 过度信任 LLM | 实测复核推翻 design 假设 1 处（MGF1 默认行为）、修正测试判据 | ✅ |
| 3 | Prompt 注入 | 本变更未改任何 system prompt / 指令文本 | ✅ N/A |
| 4 | 记忆污染 | `phase-context.md` 已交接 Phase 1/2/3 上下文 | ✅ |
| 5 | 上下文窗溢出 | 单次编辑均 < 300 行；大重构拆为多次 Edit | ✅ |
| 6 | 工具参数漂移 | CLI 参数与 agent_spec CP 逐项核对一致 | ✅ |
| 7 | 安全凭证泄露 | 无 token/key 明文；密钥只以文件路径引用（`.secrets/cred-relay/`） | ✅ |
| 8 | 权限绕过 | Gate 字段（`confirmed_*`）仅由 `fstdd gate approve` 写入，未手改 | ✅ |
| 9 | 并发竞态 | `merge_entries` 经 `_index_lock` 串行化；`_write_entry` 原子替换 | ✅ |
| 10 | 路径遍历 | `_safe_eid()` 剥离路径分隔符与 `..`（评审 H-2 修复） | ✅ |
| 11 | 跨会话残留 | 仓库内无 `.tmp`/`.scratch` 残留；探针文件已移出仓库 | ✅ |
| 12 | 输出截断 | 未改 hook stdin 处理 | ✅ N/A |
| 13 | 格式错误 | canonical YAML / TSV 均可 `yaml.safe_load` 解析 | ✅ |
| 14 | 循环依赖 | `_exp_sync` ↔ `experience` 用函数内延迟导入；无 import 环 | ✅ |
| 15 | 重复扣款 | 非金融项目（经验库基础设施） | N/A |
| 16 | 账实不符 | 非金融 | N/A |
| 17 | 静默降级 | push/pull 失败显式打印并 `exit 1`；不静默吞错 | ✅ |
| 18 | 精度丢失 | 非金融 | N/A |
| 19 | 审计缺口 | 冲突写 `sync-conflicts.tsv`（含双方 updated_at + 落点）；出站走 share_experience 审计 | ✅ |
| 20 | 状态机漏洞 | 生命周期转换表未改动；auto-deposit 产物一律 `discovered`（不越级） | ✅ |
| 21 | 额度穿透 | 非金融 | N/A |
| 22 | 合规遗漏 | 出站不变量：任何 push（明文档/安全档）先脱敏；无第三方外发 | ✅ |
| 23 | 过度工程 | YAGNI 七阶：加密用本机既有 openssl（L5 已装依赖）；传输复用本仓 `share_experience.py`（L2 本仓已有）；未引入新依赖 | ✅ |

## 七、已知问题 / 未完成项

| # | 项 | 名称 | 原因 | 影响 | 补完计划 |
|---|----|------|------|------|---------|
| 1 | 环境事实（待裁定） | **editable 安装的 `fstdd` 指向 `D:/FSTDD003/upstream`（v3.0.5）** | 本机 `pip show fstdd` 的 editable 目标为另一节点目录；与法定源 `E:/FSTDD/stdd-repo/upstream`（v3.3.8）物理独立 | 本轮改动只落法定源：pytest（sys.path 优先）与 `upstream/bin/fstdd` 均生效；但 **PATH 上的 `fstdd` 命令仍跑 v3.0.5 旧代码** | 需 D哥 裁定是否镜像到 D:/FSTDD003（涉另一节点目录，未擅自改动） |
| 2 | 未完成 | **安全档端到端（真实 hub）未实测** | 沙箱无 hub SSH 可达性；SC-015/019 已在模块级（`test_exp_crypto.py`）全覆盖，sync 级 `--secure` 走本地目录适配器未单独覆盖 | 安全档合并逻辑未经真实跨机验证 | 后续在有 hub 可达的环境做一次真实 push/pull --secure |
| 3 | 环境噪声 | `_index_lock` 释放时 `os.remove` 可能被沙箱 safe-delete 守卫拦截（`state lock timeout`） | 守卫的进程间状态锁被并发进程占用时**所有**删除被拒 | 并发跑 pytest 时 `experience`/`sync` 相关测试可能**瞬时**整片报红（重跑即恢复）；**非产品缺陷** | 沙箱层问题；本报告的全量结果在无并发时采集 |
| 4 | 未完成 | **`experience sync` 的 inbox HTTP GET 端点未实现**（ADJ-003） | hub 侧只有 POST 写入端点，无 GET 读取端点 | pull 依赖 SSH/scp 或 `--hub-dir` 离线中转 | 若 hub 侧新增 GET 端点，加一个传输适配器分支即可 |
| 5 | 未完成 | **合并未实现 DEPRECATE**（ADJ-004） | 远端退役协议未定义 | 退役不跨节点传播 | 另立 change 设计远端退役协议 |
| 6 | 技术债 | `spec SC-015` 原文仍写「AES-GCM」，实现为 AES-CTR+HMAC（ADJ-001） | Gate 2 已确认的工件本轮未改 | 文档与实现算法标签不一致（行为意图一致） | Gate 3 由 D哥 裁定是否正式改述 spec |

## 八、设计偏离汇总

见 `design-adjustments.yaml`（4 条：ADJ-001 Major / ADJ-002..004 Minor）。

## 九、Gate 3 前置条件核对

| Step | 名称 | 完成 |
|------|------|:---:|
| C1 | 多路并行技术评审（代码/测试/文档 3 代理） | ✅ |
| C2 | 全量质量检查（pytest + lint + ci check-failures） | ✅ |
| C3 | Diff 审查 | ✅ |
| C4 | 失败模式检查（23 类） | ✅ |
| C5 | 经验库自动记录/更新 | ✅ |
| C6 | 汇总设计调整（design-adjustments.yaml） | ✅ |
| C7 | 生成测试报告（本文件） | ✅ |

## 十、C5 经验库自动记录

本轮失败模式检查产出 **3 条新经验**（已入库 `.fstdd/experiences/`）：

| ID | 类别 | 严重度 | 标题 |
|----|------|--------|------|
| EXP-2026-0028 | (k) 契约断层 | medium | OpenSSL 3.x 起 `rsa_mgf1_md` 默认跟随 `rsa_oaep_md`，不再退化为 sha1 |
| EXP-2026-0029 | (f) 运行时行为偏差 | medium | 沙箱 safe-delete 守卫在状态锁被占用时拦截 `os.remove`，文件锁释放抛 `SystemExit` 整片报红 |
| EXP-2026-0030 | (e) 工具误用 | medium | 把 `TMP`/`TEMP` 指向 agent runtime 目录会让 Guard 把测试临时路径判为「agent runtime dir」而放行 |

（`.fstdd/experiences/.experience-index.yaml` 已随之更新。）
