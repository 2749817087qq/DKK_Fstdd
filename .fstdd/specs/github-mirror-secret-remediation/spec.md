# Spec: github-mirror-secret-remediation

> Change: 2026-10-04-github-mirror-secret-remediation | Auto-generated Human View

## Requirements

### Requirement: 触发脚本 `tools/rotate_github_token.sh` SHALL 不含任何可被判为 PAT 形态的字面量；
其 PAT 前缀校验语义 SHALL 保持不变。


#### Scenario: SC-001

- **GIVEN** 脚本第 40 行原为「示例: $0 ghp_ + 34 个 x」形态占位
- **WHEN** 以凭证形态正则扫描该脚本全文
- **THEN** SHALL 使 ghp_ 前缀 + ≥20 连续字母数字 的字面量命中数为 0
- **AND** 示例行 SHALL 明确标注为占位（如 `ghp_<YOUR_PAT>`），不得形如真实 token
- **AND** 参数校验正则 `^ghp_[A-Za-z0-9]{36}$` SHALL 保持不变（正则字面量不构成 PAT 形态）

### Requirement: 本仓 SHALL 设有一道可执行门禁，使「任何 tracked 文件含高置信凭证形态字面量」
在发布门禁内不可通过，且该门禁 SHALL 被全量 `pytest upstream/tests` 自动收集。


#### Scenario: SC-002

- **GIVEN** 门禁测试置于 upstream/tests/test_no_plaintext_credentials.py
- **WHEN** 执行全量 `python -m pytest upstream/tests -q`
- **THEN** SHALL 收集并执行该门禁，且结果为通过（0 failed）
- **AND** 门禁 SHALL 以 `git grep -nIE` 扫描全部 tracked 文件
- **AND** 门禁 SHALL 只读，不写任何文件

#### Scenario: SC-003

- **GIVEN** fixture 去形态化（C3）与孤儿私钥撤销（C5）均已落地
- **WHEN** 对全部 tracked 文件执行高置信凭证形态扫描
- **THEN** SHALL 使 ghp_/github_pat_/sk-/AKIA/私钥头 五类形态命中数均为 0
- **AND** SHALL 不依赖任何白名单/豁免清单
- **AND** 门禁 SHALL 覆盖 `.fstdd/`、`tools/`、`upstream/`、`tests/` 全域 tracked 文件

#### Scenario: SC-004

- **GIVEN** 构造两段样本文本：一段含 ghp_ 前缀 + 30 位、一段只含正则字面量 `ghp_[A-Za-z0-9]{20,}`
- **WHEN** 分别送入纯函数 scan_text_for_credentials()
- **THEN** SHALL 对前者报出命中，对后者不报命中
- **AND** SHALL 使门禁具备可判定的正/负样本，避免「恒真」假门禁
- **AND** 命中结果 SHALL 含行号，便于定位

### Requirement: 为使门禁保持零白名单，既有合法测试夹具 SHALL 去形态化，且其运行值与断言语义
SHALL 保持不变。


#### Scenario: SC-005

- **GIVEN** 两处 fixture 原以连续字面量嵌入 ghp_/github_pat_/sk- 与 PEM 私钥头
- **WHEN** 改为运行时字符串拼接构造后执行原用例
- **THEN** SHALL 使原断言全部通过（脱敏替换 / 端点 422 拒收语义不变）
- **AND** 拼接后的运行值 SHALL 与去形态化前逐字节相同
- **AND** SHALL 不新增/删除任何用例，只改字面量构造方式

### Requirement: 镜像故障处置手册 SHALL 覆盖「GitHub push protection / secret scanning 拦截」这一类
非网络类失败，并给出可执行的解除路径。


#### Scenario: SC-006

- **GIVEN** docs/DISTRIBUTED_ACCESS.md §五「故障处置」原表未覆盖 secret scanning 类
- **WHEN** 检索该文件的 §五 处置表
- **THEN** SHALL 含一行同时指向 push protection 诊断、一次性 unblock 链接与凭证轮换命令
- **AND** SHALL 区别于「GitHub 不可达」行，明确其非网络性质
- **AND** SHALL 指明恢复验证手段（tools/check_mirror.sh）与 Release 补发

### Requirement: 孤儿私钥文件 SHALL 从版本库撤销跟踪，且 SHALL 被 .gitignore 覆盖，使同类私钥
无法再被误提交。


#### Scenario: SC-007

- **GIVEN** .fstdd/_fstdd003_key_new.txt 为 tracked 的 OPENSSH 私钥且全仓零引用
- **WHEN** 执行 `git rm --cached` 并在 .gitignore 补入该路径后检查
- **THEN** SHALL 使 `git ls-files` 不再包含该文件
- **AND** .gitignore SHALL 在「SSH 私钥绝不入库」段含该路径
- **AND** 磁盘文件 SHALL 保留（不删除数据）

### Requirement: 本变更 SHALL 不破坏既有基线：全量测试 0 failed，四个自检脚本全绿。


#### Scenario: SC-008

- **GIVEN** C1..C5 全部落地
- **WHEN** 执行全量 pytest 与四个自检脚本
- **THEN** SHALL 得到 `pytest upstream/tests -q` 0 failed 与四个自检脚本全绿
- **AND** SHALL 不新增 skip 以掩盖失败
- **AND** 基线失败数 SHALL 保持为 0
