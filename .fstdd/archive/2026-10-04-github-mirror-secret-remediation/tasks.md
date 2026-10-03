# 实现任务清单 — 2026-10-04-github-mirror-secret-remediation

> mode: standard | task_type: code
> 目标文件：`tools/rotate_github_token.sh`、`upstream/tests/test_no_plaintext_credentials.py`、
> `tests/test_share_publish_sanitize.py`、`upstream/tests/test_inbox_endpoint.py`、
> `docs/DISTRIBUTED_ACCESS.md`、`.gitignore`、`.fstdd/_fstdd003_key_new.txt`（撤销跟踪）

## 切片 S1：凭证形态门禁（P0 / TC-CRED-002..005）

- [x] T1.1 新建 `upstream/tests/test_no_plaintext_credentials.py`：`git grep -nIE` 扫 tracked 文件，零白名单
- [x] T1.2 纯函数 `scan_text_for_credentials()` + 正/负样本（注入 PAT 须命中 / 正则字面量不得误报）
- [x] T1.3 RED 实证：4 类形态命中既有违规（脚本/fixture/私钥）+ 手册缺失 → 5 failed
- [x] T1.4 门禁落位 `upstream/tests/`，随发布门禁 `python -m pytest upstream/tests -q` 自动收集

## 切片 S2：轮换脚本脱敏（P0 / TC-CRED-001）

- [x] T2.1 `tools/rotate_github_token.sh` L20/21/40 占位示例改 `ghp_<YOUR_PAT>`
- [x] T2.2 保留参数校验正则 `^ghp_[A-Za-z0-9]{36}$`（正则字面量不构成凭证形态）

## 切片 S3：既有 fixture 去形态化（P0 / TC-CRED-003 / TC-CRED-006）

- [x] T3.1 `tests/test_share_publish_sanitize.py`：`BAD_TOKEN` + parametrize 3 处改运行时拼接（4 处）
- [x] T3.2 `upstream/tests/test_inbox_endpoint.py`：A17 docstring + payload 改运行时拼接（2 处）
- [x] T3.3 运行值逐字节不变；原断言全绿（脱敏替换 / 端点 422 拒收）

## 切片 S4：孤儿私钥撤销跟踪（P0 / TC-CRED-008）

- [x] T4.1 `git rm --cached .fstdd/_fstdd003_key_new.txt`（磁盘文件保留，不删数据）
- [x] T4.2 `.gitignore`「SSH 私钥绝不入库」段补该路径

## 切片 S5：镜像故障处置手册（P0 / TC-CRED-007）

- [x] T5.1 `docs/DISTRIBUTED_ACCESS.md` §五 增补 push protection / secret scanning 行（非网络类）
- [x] T5.2 含 unblock 链接指引 + `rotate_github_token.sh` 轮换 + `check_mirror.sh` 复核 + Release 补发

## 切片 S6：全量回归与发布门禁（P0 / TC-CRED-009）

- [x] T6.1 `pytest upstream/tests -q` 至 0 failed
- [x] T6.2 四自检脚本（verify_rename / verify_eol / verify_skill_standards / verify_workbuddy_skills）全绿
- [x] T6.3 工作树提交后干净（verify_eol TC-EOL-005 通过）
- [x] T6.4 更新 traceability（spec_scenarios=8 / tc_cases=9）