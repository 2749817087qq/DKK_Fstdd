# 测试方案 — 2026-10-04-github-mirror-secret-remediation

> capability: repo-credential-hygiene（新）/ mirror-failure-alert（增补）
> 对应规格：`canonical/specs/code/2026-10-04-github-mirror-secret-remediation.yaml`（REQ-001..006 / SC-001..008）
> baseline: `8ce867bb9e1399d5e80c17437a864f64070b106d`

## 一、范围与策略

| 项 | 内容 |
|---|---|
| 变更性质 | 安全收口（凭证卫生）+ 运维手册增补；不新增产品 CLI 能力 |
| 测试层次 | 单元（纯函数正/负样本） + 集成（全仓 tracked 扫描） + 工具级（git/grep 断言） + 回归（全量 pytest + 四自检） |
| 外部动作 | unblock / PAT 轮换 / 私钥撤销 / 重推恢复镜像 / Release 补发 **不在自动测试内**（人工步骤，见 design.md 决策 1） |
| 门禁载体 | 新测试落 `upstream/tests/`，随发布门禁 `python -m pytest upstream/tests -q` 自动执行 |
| 只读要求 | 门禁与全部验证命令**不写任何文件**（避免并发/双发副作用） |

## 二、TC 清单

| TC-ID | 对应 SC | 用例 / 命令 | 预置条件 | 期望结果 |
|---|---|---|---|---|
| TC-CRED-001 | SC-001 | `upstream/tests/test_no_plaintext_credentials.py::test_rotate_script_has_no_pat_literal` | `tools/rotate_github_token.sh` 已脱敏 | ghp_ 前缀 + ≥20 连续字母数字 命中数 = 0 |
| TC-CRED-002 | SC-002 | 全量 `python -m pytest upstream/tests -q`（收集计数） | 门禁文件已落 `upstream/tests/` | 该门禁被收集且通过（0 failed） |
| TC-CRED-003 | SC-003 | `...::test_no_plaintext_credentials_in_tracked_files` | fixture 去形态化 + 私钥撤销已落地 | 五类形态全仓 tracked 命中数均为 0（无白名单） |
| TC-CRED-004 | SC-004 | `...::test_scan_detects_injected_pat` | 样本文本含 ghp_ 前缀 + 30 位 | 纯函数报出命中，且结果含行号 |
| TC-CRED-005 | SC-004 | `...::test_scan_ignores_regex_literals` | 样本文本仅含正则字面量 `ghp_[A-Za-z0-9]{20,}` | 纯函数不报命中（无误报） |
| TC-CRED-006 | SC-005 | `python -m pytest tests/test_share_publish_sanitize.py upstream/tests/test_inbox_endpoint.py -q` | 两处 fixture 已去形态化 | 原断言全绿（脱敏替换 / 端点 422 拒收语义不变） |
| TC-CRED-007 | SC-006 | `...::test_mirror_runbook_present` | `docs/DISTRIBUTED_ACCESS.md` §五 已增补 | 含 push protection + unblock + rotate_github_token.sh 关键字 |
| TC-CRED-008 | SC-007 | `git ls-files --error-unmatch .fstdd/_fstdd003_key_new.txt`（期望失败）+ `git check-ignore -v` 该路径 | `git rm --cached` 与 `.gitignore` 已落地 | 文件已脱离跟踪；`.gitignore` 命中该路径 |
| TC-CRED-009 | SC-008 | 全量 `pytest upstream/tests -q` + 四自检脚本 | C1..C5 全部落地 | 0 failed；verify_rename/verify_eol/verify_skill_standards/verify_workbuddy_skills 全绿 |

## 三、工具级验证（发布门禁证据）

| 命令 | 期望 | 用途 |
|---|---|---|
| `git grep -nIE -e 'gh[pousr]_[A-Za-z0-9]{20,}' -e 'github_pat_[A-Za-z0-9_]{20,}' -e 'sk-[A-Za-z0-9]{20,}' -e 'AKIA[0-9A-Z]{16}' -e '-----BEGIN [A-Z ]*PRIVATE KEY-----'` | 退出码 1（无命中） | 全仓 tracked 零命中（TC-CRED-003 的独立复核） |
| `git ls-files | grep _fstdd003_key_new` | 无输出 | 私钥已脱离跟踪（TC-CRED-008） |
| `python -m pytest upstream/tests -q` | `0 failed` | 发布门禁 §三 第一项 |
| `python tools/verify_rename.py` / `verify_eol.py` / `verify_skill_standards.py` / `verify_workbuddy_skills.py` | 全绿 | 发布门禁 §三 第二项 |

## 四、退出准则

- 必备：TC-CRED-001..009 全绿；全量 pytest `0 failed`；四自检脚本全绿；工作树提交后干净。
- 禁止：以 skip 掩盖失败；以白名单豁免 fixture；删除用例。
- 不覆盖（显式声明）：GitHub unblock、PAT/私钥轮换、镜像收敛与 Release 补发 —— 人工步骤，
  由 `docs/DISTRIBUTED_ACCESS.md` §五 手册承载，结果在变更说明与 CHANGELOG 中记录为偏离/待办。