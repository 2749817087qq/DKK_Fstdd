# 2026-10-04-github-mirror-secret-remediation 测试报告

> 测试日期：2026-10-04
> 测试环境：Windows / Python 3.13.14（workbuddy default env）/ PyYAML 6.0.3 / pytest / git 2.x
> baseline：8ce867bb9e1399d5e80c17437a864f64070b106d
> 说明：本变更为凭证卫生收口 + 运维手册增补，不新增产品 CLI 能力；覆盖单元 + 集成 + 工具级三层。

## 一、总体概况

| 指标 | 数值 |
|------|------|
| 本变更 TC 数 | 9 TC（TC-CRED-001..009） |
| 新增测试文件 | 1（`upstream/tests/test_no_plaintext_credentials.py`，8 个测试函数 / 12 个用例） |
| 去形态化既有 fixture | 2 文件 / 6 处 |
| 全量回归（`upstream/tests`） | **885 passed, 54 skipped, 0 failed**（Gate 3 实测；收口时并入并行的僵尸 change 后为 **887 passed**） |
| 全量回归（改动前基线 8ce867b） | 预存 **2 failed** → 修复后 0 failed（见 §4） |
| 四自检脚本 | verify_rename 8/8、verify_eol 7/7、verify_skill_standards 7/7、verify_workbuddy_skills PASS |
| 通过率 | 100% |

## 二、按模块统计

| 测试模块 | 关键用例 | 结果 | 说明 |
|----------|----------|------|------|
| `upstream/tests/test_no_plaintext_credentials.py` | `test_rotate_script_has_no_pat_literal` | ✅ | TC-CRED-001：轮换脚本零 PAT 形态字面量，校验正则保留（REQ-001） |
| 同上 | `test_gate_is_collected_by_release_command` | ✅ | TC-CRED-002：门禁落位发布门禁收集目录（REQ-002） |
| 同上 | `test_no_plaintext_credentials_in_tracked_files`（×5 参数） | ✅ | TC-CRED-003：五类形态全仓 tracked 零命中、零白名单（REQ-002/003） |
| 同上 | `test_scan_detects_injected_pat` / `test_scan_detects_private_key_header` | ✅ | TC-CRED-004：正样本检出（防「恒真」假门禁） |
| 同上 | `test_scan_ignores_regex_literals` | ✅ | TC-CRED-005：负样本无误报 |
| 同上 | `test_mirror_runbook_present` | ✅ | TC-CRED-007：手册含 push protection / unblock / 轮换 / 复核 / Release（REQ-004） |
| 同上 | `test_orphan_private_key_untracked_and_ignored` | ✅ | TC-CRED-008：私钥脱离跟踪 + .gitignore 覆盖 + 磁盘保留（REQ-005） |
| `tests/test_share_publish_sanitize.py` | `test_stage_credentials_replaced`（×4 参数）等 | ✅ | TC-CRED-006：fixture 去形态化后原断言全绿（REQ-003） |
| `upstream/tests/test_inbox_endpoint.py` | `test_a17_private_key_content_rejected` | ✅ | TC-CRED-006：端点 422 拒收语义不变 |
| `upstream/tests/test_except_audit.py` + `test_guard_silent_except.py` | `test_aud_002` / `test_grd_001` | ✅ | 范围外必要修复（§4.1），修复后 11 passed |

## 三、工具级验证（发布门禁证据）

| 命令 | 结果 | 退出码 |
|------|------|--------|
| `git grep -nIE -e 'gh[pousr]_[A-Za-z0-9]{20,}' -e 'github_pat_[A-Za-z0-9_]{20,}' -e 'sk-[A-Za-z0-9]{20,}' -e 'AKIA[0-9A-Z]{16}' -e '-----BEGIN [A-Z ]*PRIVATE KEY-----'` | 无输出（零命中） | 1 |
| `git ls-files -- .fstdd/_fstdd003_key_new.txt` | 空 | 0 |
| `git check-ignore -v .fstdd/_fstdd003_key_new.txt` | `.gitignore:55` 命中该路径 | 0 |
| `Test-Path .fstdd/_fstdd003_key_new.txt` | True（磁盘保留） | — |
| `python -m pytest upstream/tests -q` | `884 passed, 54 skipped, 0 failed` | 0 |
| `python tools/verify_rename.py` | 8/8 通过 | 0 |
| `python tools/verify_eol.py --repo .` | 7/7 通过 | 0 |
| `python tools/verify_skill_standards.py` | 7/7 通过 | 0 |
| `python tools/verify_workbuddy_skills.py` | 6 个 skill 全通过（含 1 条影子副本 WARN，与本变更无关） | 0 |
| `python tools/audit_silent_except.py --check` | 通过（0 条提示） | 0 |

## 四、失败项详细分析

### 4.1 范围外必要修复：审计活表解析回退到旧表（ADJ-004）

| 项 | 内容 |
|---|---|
| 现象（最小可复现证据） | 在基线 `8ce867b` 建 worktree 复跑，`test_aud_002_table_matches_live_scan` 与 `test_grd_001_check_passes_on_current_repo` 均失败：哨兵报 `guard.py:310/374/466/1203/447` 失效、`317/381/473/535/1265` 等 11 点为「白名单外新增」 |
| 复现命令 | `git worktree add <tmp> 8ce867b` 后 `pytest upstream/tests/test_except_audit.py::test_aud_002... upstream/tests/test_guard_silent_except.py::test_grd_001...` → `2 failed` |
| 根因 | `tools/audit_silent_except.py::_default_table()` 与 2 个测试 helper 在 archive 兜底时取**字典序首个**；维护表 `2026-10-04-baseline-failures-zero` 随 change 归档后，解析回退到最早的 `2026-09-18-detection-silence-fixes` 旧表 |
| 为什么危险 | 「活表随维护 change 迁移」的设计与 change 生命周期耦合：任何 change 一归档，审计哨兵即回退到更早的表，产生**持续性误报**（且只会在下一次全量回归暴露） |
| 更一般的形态 | 「按名称排序取首个」的兜底选择器 + 目录名含时间序 → 归档/追加式目录上会稳定选到最旧者；同类选择器应显式声明「取最新」或按时间字段排序 |
| 处置 | 同一层级改为取字典序**末个**（目录名 `YYYY-MM-DD-` 前缀，字典序即时间序）；3 处同源解析同步修复；提交 `9d3bfb1` |
| 归属 | **非本 change 引入**（基线即失败）；因发布门禁 §三 要求 0 failed 而必须处置 |
| 后续建议 | 将活表落到 change 无关的稳定路径（如 `.fstdd/audit/except-points.yaml`），彻底消除归档耦合（已记入 design-adjustments.yaml 的 revision_inputs） |

### 4.2 `ci check-failures` 的两项工具级限制（非缺陷）

| 项 | 结论 | 处置 |
|---|---|---|
| ✗ TC 实现覆盖 0/9 | 检查器只扫描仓库根 `tests/`；本仓门禁按 design 决策 3 落在 `upstream/tests/`（**必须**如此才能被发布门禁 `pytest upstream/tests` 收集执行） | 记录为工具级布局限制；真实 TC→测试函数映射见 §二。已去重 TC-ID 使 (d) 由 FAIL 转 PASS |
| ⚠ AND 超限 16 | 检查器按 **spec 文件**累计 `**AND**` 数，而非每 Scenario；本 change 每个 Scenario 的 AND 数均为 2（≤5） | 记录为检查器启发式限制（前一 change 为 26，同样告警） |

## 五、功能/测试覆盖对照

| 功能模块 | 涉及文件 | 已有/新增测试覆盖 | 缺失测试 |
|----------|----------|------------------|----------|
| 凭证形态门禁 | `upstream/tests/test_no_plaintext_credentials.py` | 12 个测试函数（正/负样本 + 全仓 + 手册 + 私钥） | 无 |
| 轮换脚本脱敏 | `tools/rotate_github_token.sh` | `test_rotate_script_has_no_pat_literal` + 全仓扫描 | 无 |
| fixture 去形态化 | `tests/test_share_publish_sanitize.py`、`upstream/tests/test_inbox_endpoint.py` | 原用例 28 passed（语义零变化） | 无 |
| 孤儿私钥撤销 | `.gitignore`、`git rm --cached` | `test_orphan_private_key_untracked_and_ignored` | 无 |
| 镜像故障手册 | `docs/DISTRIBUTED_ACCESS.md` §五 | `test_mirror_runbook_present` | 无 |
| 审计活表解析（范围外） | `tools/audit_silent_except.py` | `test_except_audit` + `test_guard_silent_except` 11 passed | 无 |

## 六、设计调整说明

**4 项小偏离，0 项大偏离**（详见 `pending-adjustments.yaml` / `design-adjustments.yaml`）：
ADJ-001 前缀扩为 `gh[pousr]_`；ADJ-002 门禁 fail-open 改 fail-hard；ADJ-003 补 SC-007 自动断言；
ADJ-004 范围外审计表解析修复。均不改对外接口与行为语义。

## 七、C4 失败模式检查（23 类）

| # | 失败模式 | 结果 | 证据 / 处置 |
|---|----------|------|-------------|
| 1 | 幻觉调用 | ✅ | 仅用 `re`/`subprocess`/`pathlib` 标准库；无未 import 标识符 |
| 2 | 过度信任 LLM | ✅ | 每条断言以实跑为准；「改脚本即可断言通过」的疑问经 `git worktree` 基线复跑证伪/证实后修正 |
| 3 | Prompt 注入 | ✅ | 无 system prompt 改动 |
| 4 | 记忆污染 | ✅ | 本 change 结论均以实测证据为准，未沿用先前会话的口头结论 |
| 5 | 上下文窗溢出 | ✅ | 单文件改动均 < 300 行 |
| 6 | 工具参数漂移 | ✅ | git/pytest 参数与官方语义一致（`git grep -nIE`、`-q`） |
| 7 | **安全凭证泄露** | ✅ | 本 change 主题即此；新增门禁自证：五类形态全仓 tracked 零命中；变更制品自扫零命中 |
| 8 | 权限绕过 | ✅ | 未手改 `.fstdd.yaml` 确认字段；Gate 1/2 记 dialog + 证据原文 |
| 9 | 并发竞态 | ✅ | 门禁与全部验证命令只读；`verify_eol TC-EOL-005` 备份/原子还原索引 |
| 10 | 路径遍历 | ✅ | 仅按 `REPO_ROOT` 相对路径读写；无 `../` 逃逸 |
| 11 | 跨会话残留 | ✅ | 临时 worktree 已 `git worktree remove --force` + `prune`；工作树提交后干净 |
| 12 | 输出截断 | ✅ | 全量输出重定向文件后读取，无截断 |
| 13 | 格式错误 | ✅ | canonical YAML `yaml.safe_load` 通过；`canon verify` 2/2 |
| 14 | 循环依赖 | ✅ | 无新增模块依赖 |
| 15 | 重复扣款 | n/a | 无资金流 |
| 16 | 账实不符 | n/a | 无账本 |
| 17 | 静默降级 | ✅ | 门禁不得 fail-open 已由 ADJ-002 显式堵死（git 执行错误 → 硬失败）；`_git_grep` 仅 git 未安装时 skip |
| 18 | 精度丢失 | n/a | — |
| 19 | 审计缺口 | ✅ | 审计活表 25 点与实况零漂移；`--check` 哨兵通过 |
| 20 | 状态机漏洞 | n/a | — |
| 21 | 额度穿透 | n/a | — |
| 22 | 合规遗漏 | ✅ | 处置手册覆盖 secret scanning 类；外部人工步骤显式声明不纳入自动门禁 |
| 23 | 过度工程 | ✅ | 7 阶梯子：门禁用标准库 + 既有 `git grep`（阶梯 3/2）；未新增依赖、未新增抽象层 |

## 八、已知问题与未完成项

| 项 | 名称 | 原因 | 影响 | 补完计划 |
|---|---|---|---|---|
| 1 | GitHub 一次性 unblock | 需仓库管理员浏览器操作，agent 不能代做 | GitHub Release 缺失（CHANGELOG §[3.3.1] 已记偏离） | 人工执行；链接与步骤见 `docs/DISTRIBUTED_ACCESS.md` §五 |
| 2 | PAT 轮换 + SSH 私钥撤销 | 涉及生产凭证，须人工持有新凭证 | 历史泄露凭证仍在用（**数据安全不受影响**：真值源在服务器裸库与 local） | 人工执行 `tools/rotate_github_token.sh ghp_<YOUR_PAT>` + 私钥撤销 |
| 3 | 重推恢复镜像 + Release 补发 | 依赖第 1/2 项完成 | 镜像滞后于 local（`mirror-failed.flag` 在位） | 完成 1/2 后再次 push，`tools/check_mirror.sh` 复核收敛（退出码 0） |
| 4 | 审计活表落位重构 | 本 change 仅做最小修复 | 归档耦合仍在（已由「取最近」缓解） | 后续 change 落 `.fstdd/audit/` 稳定路径 |

> 前 3 项为**显式声明的外部人工步骤**，不纳入本 change 的 SC（否则 Gate 3 无法客观判定），
> 由手册承载、结果在变更说明与 CHANGELOG 记录。

## 九、结论

**可进入 Gate 3。** 全量 `upstream/tests` **884 passed / 54 skipped / 0 failed**；四自检脚本全绿；
`canon verify` 2/2；五类凭证形态全仓 tracked 零命中；孤儿私钥已脱离跟踪且磁盘保留。
风险等级：**低**。唯一残留为 4 项外部人工步骤（显式声明，不阻塞仓库侧交付）。
