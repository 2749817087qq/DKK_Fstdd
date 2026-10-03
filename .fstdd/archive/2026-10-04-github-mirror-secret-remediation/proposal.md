# 镜像与版本库凭证收口：脱敏占位串/撤销孤儿私钥 + 凭证形态门禁 + GitHub push-protection 处置手册

<!-- source_hash: 5860b3dcf1609c86 -->
<!-- generated_at: 2026-10-03T17:30:02+00:00 -->
<!-- canonical: canonical/proposals/2026-10-04-github-mirror-secret-remediation.yaml -->

## Why

server→GitHub 镜像被 GitHub push protection 拦截，GitHub Release 因此缺失。
根因不是写权限，而是 tools/rotate_github_token.sh 的用法示例行含一段
「ghp_ 前缀 + 36 位」的 PAT 形态字面量：历史提交 6253533 首次引入，
bfc3fa4 只在工作树把该行替换为 ghp_ 前缀 + 34 个 x，但真实形态串仍留在
master 及 v3.1.2 / v3.2.0 / v3.3.0 / v3.3.1 各 tag 的历史中。推送 --all --tags
时该历史随镜像推送，GitHub secret scanning 命中并阻断，服务器侧
mirror-failed.flag 常驻（failed_items=branches tags）。更深一层：经只读实测，
该串正是服务器 github remote 当前在用的镜像凭证
（https://x-access-token:<PAT>@github.com/2749817087qq/DKK_Fstdd.git），
即一枚在用生产凭证被写进了版本库历史，属凭证泄露，须轮换。
真值源（服务器裸库）与 local 已落库、数据安全；受损面是 GitHub 侧镜像与 Release。
同一次盘点另发现第二枚同类泄露：tracked 文件 .fstdd/_fstdd003_key_new.txt 是一份
OPENSSH 私钥（8 行，私钥头为 OPENSSH PEM 格式），自提交 3493217
起入库，全仓零引用（孤儿文件），属同一「明文凭证入库」缺陷的又一体。两者同属本变更收口范围。


## What Changes

- 脱敏触发串：把 tools/rotate_github_token.sh 用法示例/注释中的占位串改为不可被
扫描器误判为 PAT 的形态（如 `ghp_<YOUR_PAT>` 与 `$0 <new_github_pat>`），
消除工作树中的 PAT 形态字面量。文件内的前缀校验正则
（`^ghp_[A-Za-z0-9]{36}$`）语义不变 —— 正则字面量本身不构成 PAT 形态。

- 新增版本库凭证形态门禁测试 upstream/tests/test_no_plaintext_credentials.py：
用 `git grep -nIE` 扫描全部 tracked 文件，命中任一高置信凭证形态
（ghp_/gho_/ghu_/ghs_/ghr_ 前缀 + ≥20 位、github_pat_ + ≥20 位、
sk- + ≥20 位、AKIA + 16 位、`-----BEGIN ... PRIVATE KEY-----`）即判失败，
使「明文凭证入库」在发布门禁（全量 pytest upstream/tests）内不可通过。

- 既有 fixture 去形态化：tests/test_share_publish_sanitize.py 的 BAD_TOKEN 常量
及 parametrize 中 ghp_/github_pat_/sk- 共 4 处凭证形态字面量、以及
upstream/tests/test_inbox_endpoint.py 私钥头 fixture（docstring + payload 共 2 处）
改为运行时拼接构造（如 "ghp_" + "ABCD..."、"-----BEGIN RSA " + "PRIVATE KEY-----"），
运行值不变、断言与脱敏/拒收语义不变，使 C2 门禁无需任何白名单即可全仓零命中。

- 处置手册：docs/DISTRIBUTED_ACCESS.md §五「故障处置」新增一行
「推送被 GitHub push protection / secret scanning 拦截」，给出只读诊断
（tools/check_mirror.sh）、GitHub 一次性 unblock 链接、服务器侧凭证轮换命令
（tools/rotate_github_token.sh <new_pat>）、以及重推触发镜像重试与 Release 补发路径。

- 撤销孤儿私钥入库：对 .fstdd/_fstdd003_key_new.txt 执行 `git rm --cached`（保留磁盘文件、
不删任何数据）并在 .gitignore 的「SSH 私钥绝不入库」段补入该路径，使该私钥不再随仓库
分发；后续同类私钥形态由 C2 门禁兜底。密钥本身的撤销/轮换属人工步骤（见 constraints）。


### New Capabilities

- **repo-credential-hygiene**：版本库凭证卫生门禁：任何 tracked 文件都不得含高置信凭证形态字面量；由
upstream/tests 内的门禁测试强制，且不依赖白名单（测试 fixture 亦去形态化）。


### Modified Capabilities

- **mirror-failure-alert**：镜像失败处置覆盖「GitHub secret scanning / push protection 拦截」这一类
非网络类失败：诊断路径、解除步骤（unblock + 凭证轮换）、恢复验证与 Release 补发。


## Success Criteria

- [ ] 全量 tracked 文件对高置信凭证形态（ghp_/github_pat_/sk-/AKIA/私钥头）的 `git grep` 命中数为 0。
- [ ] `.fstdd/_fstdd003_key_new.txt` 不再被 git 跟踪（`git ls-files` 无此项），且 .gitignore 覆盖该路径。
- [ ] 全量 tracked 文件对私钥头形态零命中（测试夹具已去形态化，未加白名单）。
- [ ] 新增门禁测试 upstream/tests/test_no_plaintext_credentials.py 通过，且被全量 `pytest upstream/tests` 收集执行（0 failed）。
- [ ] tools/rotate_github_token.sh 不含任何「ghp_ 前缀 + ≥20 连续字母数字」的字面量；示例行明确标注为占位而非真实 token。
- [ ] docs/DISTRIBUTED_ACCESS.md §五 含 push-protection 处置行，指向 unblock 链接与 rotate 命令。
- [ ] 全量 `python -m pytest upstream/tests -q` 为 0 failed；四个自检脚本（verify_rename/verify_eol/verify_skill_standards/verify_workbuddy_skills）全绿。
