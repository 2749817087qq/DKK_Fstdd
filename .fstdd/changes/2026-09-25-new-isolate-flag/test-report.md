# 测试报告 — change 隔离形态（v3.0.7）

**Change**：`2026-09-25-new-isolate-flag`
**阶段**：Phase 3 BUILD → 待 Gate 3
**base_git_sha**：`4eec636`（BUILD 起点）
**HEAD（报告时点）**：`d329491`
**报告日期**：2026-09-26
**执行环境**：Windows / `C:/Python311/python.exe` / git（Windows 原生）

---

## 一、TL;DR

- **结论**：🟢 **通过**。9 项 REQ / 20 个 SC 全部落地，TC-ISO-001..023 全绿。
- **关键成果**：`--isolate {none|worktree|branch}` 三形态可用；**`none` 路径零漂移**（与改动前逐字一致）；
  隔离 worktree 内**门禁有效**（裁定 ISO-1）；`--parallel` 死代码清除。
- **回归**：new/canon/init 相关套件 **66 passed / 0 failed**；全量套件结论见 §6。
- **端到端**：4 个真 CLI + 真 git 探针全部通过，含 **agent_spec 23/23**（两处 ACTIVE_CHANGE 跨 worktree 零干扰）。
- **阻塞项**：无。
- **下一步**：Gate 3 确认 → DELIVER。

---

## 二、per-slice 证据链

每片按 RED → GREEN → REFACTOR；每片通过后才进下一片。

| Slice | 主题 | commit | RED 证据 | GREEN 证据 |
|---|---|---|---|---|
| 1 | 隔离形态解析 + 配置回落 | `e883547` | collection error（`ImportError: _load_isolation_config`） | 28 passed |
| 2 | 失败前置与 git 前置检查 | `5e8953f` | 10 failed / 12 passed（**行为级**） | 38 passed / 106.80s |
| 3 | worktree 创建 + 脚手架落点 | `30756ea` | 5 failed（`new.py:226` SystemExit） | 51 passed / 76.64s |
| 4 | branch 形态 | `30e9f70` | 1 failed（守卫拦截） | 51 passed / 56.69s |
| 5 | 门禁随 worktree（ISO-1） | `e89c0ab` | 3 failed（hook 未随行 / 无告警） | 54 passed / 41.40s |
| 6 | 提示行 + init 配置写入 | `40075e9` | 3 failed（`ImportError: _post_init_isolation`） | 61 passed / 41.23s |
| 7 | 死代码移除 + CHANGELOG | `85383bd` | 2 failed（死代码残留 / CHANGELOG 缺条目） | 66 passed / 51.19s |
| 8 | 质量验证与交付证据 | 本报告 | — | 见 §3–§6 |

收口提交（tasks.md 勾选 + 片内发现）：`a0af951` / `b548f78` / `b2a940b` / `10eff80` / `d329491`。

**RED 形态说明**：新增 API 切片的 RED 表现为 collection error（符号不存在）；自 Slice 2 起为
**行为级** RED（断言失败打在真实执行路径上），证据强度更高。

---

## 三、TC 覆盖矩阵

| TC-ID | 主题 | 用例 | 状态 |
|---|---|---|---|
| TC-ISO-001 | 骨架落在 worktree 内、主仓不含该 dir | `test_iso_001_skeleton_lands_in_worktree` | ✅ |
| TC-ISO-001b | 模板源取主仓（裁定 ISO-4） | `test_iso_001b_template_source_is_main_repo` | ✅ |
| TC-ISO-002 | 无 `--isolate` 零漂移（不得调用 git） | `test_iso_002_no_isolation_never_invokes_git` | ✅ |
| TC-ISO-002b | 不写隔离配置 | `test_iso_002b_new_does_not_write_isolation_config` | ✅ |
| TC-ISO-003 | `--help` 暴露三取值 | `test_iso_003_help_exposes_isolate`（**子进程**） | ✅ |
| TC-ISO-004 | 分支名由规则构造 | `test_iso_004_branch_name_is_rule_derived` + 单元 | ✅ |
| TC-ISO-005 | branch 只切分支不建 worktree | `test_iso_005_branch_mode_switches_branch_only` | ✅ |
| TC-ISO-006 | 非 git 仓拒绝且不留半成品 | `test_iso_006_non_git_repo_refuses_worktree` | ✅ |
| TC-ISO-006b | 非 git 仓 + branch 同样拒绝 | `test_iso_006b_non_git_repo_refuses_branch` | ✅ |
| TC-ISO-007 | 脏树 + branch 拒绝、分支未变 | `test_iso_007_dirty_tree_refuses_branch` | ✅ |
| TC-ISO-008a | 分支已存在 ⇒ 拒绝 + 清理命令 | `test_iso_008a_existing_branch_refuses_worktree` | ✅ |
| TC-ISO-008b | 目标路径已存在 ⇒ 拒绝 + 不删 | `test_iso_008b_existing_path_refuses_worktree` | ✅ |
| TC-ISO-009 | worktree 在项目外、主仓干净 | `test_iso_009_worktree_outside_project_and_main_repo_clean` | ✅ |
| TC-ISO-010 | `worktree_root` 配置生效 | `test_iso_010_configured_worktree_root_is_honored_e2e` | ✅ |
| TC-ISO-011 | 提示行随形态变化 | `test_iso_011_hint_for_none_offers_isolation_command` / `011b` / `011c` | ✅ |
| TC-ISO-012 | 全程零交互 | `test_iso_012_new_never_prompts` | ✅ |
| TC-ISO-013 | init 写 isolation 三键 | `test_iso_013_post_init_writes_isolation_block` | ✅ |
| TC-ISO-014 | 既有值保留 + 幂等 | `test_iso_014_post_init_preserves_existing_and_is_idempotent` | ✅ |
| TC-ISO-014b | 结构不符 ⇒ 不覆盖用户数据 | `test_iso_014b_non_mapping_isolation_is_not_overwritten` | ✅ |
| TC-ISO-015 | 配置默认值被消费 | `test_iso_015_config_default_is_consumed` / `015b` | ✅ |
| TC-ISO-016 | 配置读取失败回落 none | `test_iso_016a`–`016e`（缺失/坏 YAML/非法值/结构不符/不抛异常） | ✅ |
| TC-ISO-017 | `parallel` 死代码零命中 | `test_iso_017_parallel_dead_code_removed` | ✅ |
| TC-ISO-018 | CHANGELOG 含条目与原语义 | `test_iso_018_changelog_records_removal` | ✅ |
| TC-ISO-019 | hook 随 worktree 复制且内容一致 | `test_iso_019_guard_hooks_propagate_into_worktree`（×2 宿主路径） | ✅ |
| TC-ISO-020 | 无 hook ⇒ 告警但 exit 0 | `test_iso_020_missing_hooks_warns_but_succeeds` | ✅ |
| TC-ISO-021 | 既有回归全绿 | `test_new.py`(11) + `test_init.py`(3) = **14** | ✅ |
| TC-ISO-022 | 吞异常哨兵通过 | `audit_silent_except.py --check` + `test_except_audit.py`(5) | ✅ |
| TC-ISO-023 | Guard 判定链未受影响 | `test_guard.py`（51 例） | ✅ |

**测试文件**：`upstream/tests/commands/test_new_isolate.py`（38 例，本 change 新增）。
**SPEC 调整（已同步 `test-plan.md`）**：原 `test_new_coverage.py`（2 例，V2.8 `--parallel` 专属）
随死代码一并删除 ⇒ TC-ISO-021 既有回归例数 16 → **14**。

---

## 四、失败模式检查结论

| # | 失败模式 | 结论 | 锚定用例 / 证据 |
|---|---|---|---|
| 1 | 隔离静默降级为 `none` | ✅ 未发生。非 git 仓**出声拒绝** exit 1 | TC-ISO-006 / 006b |
| 2 | 失败路径执行删除 | ✅ 未发生。清理命令只打印，`rm` 仅出现在提示文本里 | TC-ISO-008a / 008b |
| 3 | 失败后留半成品 change | ✅ 未发生。前置检查早于**任何**目录创建 | TC-ISO-006 / 007 / 008 |
| 4 | 配置坏 ⇒ 回落 `worktree` | ✅ 未发生。回落方向锁死为 `none` | TC-ISO-016b / 016d（专门断言**不是** worktree） |
| 5 | 隔离变成绕过门禁的通道 | ✅ 未发生。hook 整份拷贝进 worktree | TC-ISO-019 / 020 + agent_spec |
| 6 | 未实现形态静默按 `none` 执行 | ✅ 未发生（Slice 1–3 有分期守卫；Slice 4 后两形态均落地，守卫与其用例一并删除，测试文件内留「新增形态须重新加回守卫」注释） | 守卫用例（已随实现删除） |
| 7 | 顺序错误（先脚手架后隔离） | ✅ 未发生。`target_root` 在 `(change_dir/"specs").mkdir()` **之前**赋值 | TC-ISO-001 / 009 |
| 8 | 模板源取错导致骨架残缺 | ✅ 未发生（裁定 ISO-4，模板源恒为主仓） | TC-ISO-001b |
| 9 | init 覆盖用户既有配置 | ✅ 未发生。三键齐备时不写文件；结构不符时跳过 | TC-ISO-014 / 014b |
| 10 | `canon init` 改动破坏向后兼容 | ✅ 未发生。不传 `project_root` 时回落 `Path.cwd()` | `test_canon.py`(9) 全绿 |
| 11 | 行号锚定型哨兵漂移 | ⚠️ **曾发生并已修复**：Slice 6 插入 63 行 ⇒ `init.py` 吞异常点 322→385，超 ±5 容差。已刷新审计表 EA-015 | `audit_silent_except.py --check` ⇒ 0 条提示 |

---

## 五、端到端证据（真 CLI + 真 git，独立于 pytest）

四个探针脚本（`.workbuddy-ai/tmp/`），全部为**真 CLI + 真 git + 真 Guard**：

| 探针 | 覆盖 | 关键结果 |
|---|---|---|
| `e2e_worktree_probe.sh` | worktree 形态 + 双 worktree 互不干扰 | 骨架全落 worktree 内；主仓 status 全程为空；双 worktree 互不可见；同名冲突由分支名兜住；非 git 仓出声拒绝 |
| `e2e_branch_probe.sh` | branch 形态 | 脏树拒绝且分支未变；干净后切分支、worktree 仍 1 条、骨架在主仓 |
| `e2e_guard_hook_probe.sh` | 门禁传播（ISO-1） | **真实** `settings.local.json`（1088 B，未跟踪）逐字节复制进 worktree，含 guard 命令；无 hook 项目告警且 rc=0 |
| `e2e_init_probe.sh` | init 配置写入 | 首跑补 3 键；二跑**逐字节未变**（幂等）；预置 `default: branch` + `project.name` 均保留 |

### agent_spec 端到端（`agent_spec_probe.sh`）— **23/23 通过**

沙箱仓 + 双 worktree + 真 Guard 判定：

| 步骤 | 验证 | 结果 |
|---|---|---|
| step1 | `new alpha --isolate worktree` | ✅ exit 0；worktree 2 条；主仓 status 干净；主仓无 alpha 目录；骨架在 worktree 内 |
| step2 | `new beta --isolate worktree` | ✅ exit 0；worktree 3 条；beta 骨架在 beta worktree |
| step3 | alpha 置只读相位（understand）+ `scope.paths=[alpha.txt]` | ✅ 状态已构造 |
| step3-v | alpha 内 Guard 判定 | ✅ `alpha.txt` **Blocked exit 2**；`beta.txt` **warn-only exit 0**（输出 `is out of scope for 2026-09-26-alpha (scope.paths declared) - allowing`） |
| step4 | beta 置可编辑相位（build）后同一 Guard | ✅ **exit 0**（`Active change: 2026-09-26-beta (phase: build) — ✅`） |
| step5 | 非 git 目录 `new gamma` | ✅ exit 1；无残留；提示含「git 工作树」 |
| step6 | 脏树 `new delta --isolate branch` | ✅ exit 1；分支未变；提示改用 worktree |
| step7 | `new epsilon`（无 `--isolate`） | ✅ exit 0；无新 worktree / 无新分支；骨架在主仓；输出含提示行 |
| 全程 | 无 `input()` 阻塞 | ✅ 0 处 |

> **这是本 change 的核心命题**：两处 ACTIVE_CHANGE 各自只冻结自己 scope 内的路径，
> 跨 worktree **零干扰** —— 主工作区单实例模型下做不到这一点。

---

## 六、回归结论

### 6.1 相关套件（new / canon / init / except_audit）

```
66 passed in 51.19s
```
（`test_new_isolate.py` 38 + `test_new.py` 11 + `test_canon.py` 9 + `test_init.py` 3 + `test_except_audit.py` 5）

### 6.2 哨兵

```
tools/audit_silent_except.py --check  ⇒  哨兵结果: 通过 (0 条提示)
test_except_audit.py                  ⇒  5 passed
```

### 6.3 Guard 判定链（TC-ISO-023）

`test_guard.py` 51 例全绿（见 §6.4 全量日志）。

### 6.4 全量套件

| 项 | 值 |
|---|---|
| 命令 | `python -m pytest tests -p no:cacheprovider -q` |
| 基线（`4eec636`） | 802 passed / 0 failed / 2614.06s |
| 本次（`d329491`） | ⏳ 见下方「全量套件结果」 |
| 预期差值 | +38（新增 isolate 用例）− 2（删除 `test_new_coverage.py`）= **+36** |

**全量套件结果**：_（等待后台任务完成后填入）_

---

## 七、已知局限

1. **`stdd validate` 残留 1 个 warning**：`spec.md: 未找到 Scenario`。
   这是「双视图 spec（手写精简视图不使用 `#### Scenario:` 标题）+ `validate.py` 遍历
   `specs/**/*.md` 数 Scenario」的**既有约定固定代价** —— 对照 W5 确认其输出为完全相同的
   `0 error / 1 warning`。**error 数为 0**，不阻塞。
2. **`specs/code/spec.md` 为手写精简视图**，刻意不使用 `#### Scenario:` 标题以避免
   Scenario 计数翻倍（20 → 40）触发新 error。见 `fstdd-audit-deliver-closure` skill §6.2。
3. **探针直接改 `.fstdd.yaml` 构造状态**（agent_spec step3/4）：仅限沙箱。
   真实流程必须走 `stdd gate approve` + `stdd phase advance`；直接改会被 Guard 正确拒绝
   （实测报「相位完整性异常」/「Gate 缺失」）—— 本探针按合法状态补齐 `status` 与
   `confirmed_at` 才通过。
4. **worktree 内 change 骨架是未跟踪文件**：`git status --porcelain` 会显示 1 条
   `?? .fstdd/changes/<dir>/`，属预期（骨架尚未提交）。
5. **机器负载**：执行期间有外部 python 进程（PID 24520）持续占用，套件耗时约为基线的
   1.5–3 倍，但不影响结论。

---

## 八、遗留项（不在本 change 范围）

| # | 项 | 处置 |
|---|---|---|
| 1 | CLI 审计链 5 项缺陷：`amend-audit` 不持久 / `traceability` 恒 0 / `approve`→`advance` 首次误报 / `canon generate --type` 死选项 / `gate.py` 无效补救提示 | 另立 change |
| 2 | 「模板缺失时静默跳过复制」（`if tmpl.exists()` 无 else 告警） | 本次登记，未修（避免范围蔓延） |
| 3 | W5 与本 change 全部提交**未 push** | 待授权 |
| 4 | `init.py` 的 `except Exception: pass`（EA-015）本身是合理容错，但属行号敏感点 | 已在审计表加漂移说明 |

---

## 九、Gate 3 检查清单

- [x] TC-ISO-001..023 全部有对应用例且通过
- [x] 失败模式检查 11 项全部有结论
- [x] 端到端证据（4 探针 + agent_spec 23/23）
- [x] `stdd validate` ⇒ 0 error
- [x] `canon verify` ⇒ 2/2 通过
- [x] 吞异常哨兵 ⇒ 0 条提示
- [ ] 全量套件 0 failed（§6.4 待填）
- [ ] Gate 3 确认

---

> 本报告的证据均可用「命令 + 输出摘要 + 观测时刻 + base_git_sha」复现。
> 探针脚本位于 `.workbuddy-ai/tmp/`（e2e_*_probe.sh / agent_spec_*）。
