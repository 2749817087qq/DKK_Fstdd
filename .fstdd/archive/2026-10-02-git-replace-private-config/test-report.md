# test-report.md — git-replace-private-config

## 测试概览

| 项 | 值 |
|---|---|
| 时间 | 2026-10-02T11:10:00+08:00 |
| Slice | S1 |
| TC 覆盖 | TC-GRP-001..TC-GRP-005（5/5 PASS） |
| 新增测试 | 0（零代码改动 change，实测即 TC） |
| 失败模式检查 | ✅ 14 类全量 |

## 证据（实测即 TC 结果）

### TC-GRP-001: refs/replace 不为空
`
$ git replace -l
d75b0bfdc2c5b450300a6122383af04ad8554a94  ✅
`

### TC-GRP-002: refs/replace 不在 git 索引
`
$ git ls-files | Select-String replace
(空)  ✅
`

### TC-GRP-003: gc 不清理 replace refs
`
$ git cat-file -t replace/d75b0bf...
commit  ✅ （真正 commit 对象，仅无引用才会被 gc）
`

### TC-GRP-004: merge-base 在 pull 后仍有效
`
$ git merge-base HEAD server/master
c383be798f0d2d0dea6d37b115d4a675525659ae  ✅
`

### TC-GRP-005: 远程无 replace refs
`
$ git ls-tree -r server/master | Select-String replace
(空)  ✅
`

## 14 类失败模式检查

| 类别 | 状态 | 说明 |
|---|---|---|
| 凭证泄漏 | ✅ N/A | 零代码改动 |
| 远程同步断裂 | ✅ PASS | replace refs 固化为 commit 对象 |
| merge-base 丢失 | ✅ PASS | convert-graft-file 已执行 |
| git gc 清理 | ✅ PASS | commit 对象只被 refs/replace 引用 |
| 远程污染 | ✅ PASS | 远程 server/master 无 replace refs |
| 本地配置丢失 | ✅ PASS | .git/objects 持久 |
| 权限 | ✅ PASS | 只读 .git/objects，无权限变更 |
| 并发 | ✅ PASS | 单 replace ref，无竞态 |
| 网络 | ✅ N/A | 无网络操作 |
| 资源 | ✅ N/A | 仅新增 1 个 commit 对象 |
| 异常边界 | ✅ PASS | git merge-base 失败可重跑 graft |
| 零回归 | ✅ PASS | tools/test_verify_notices.py 21 passed |
| 审计链 | ✅ PASS | merge commit 5094ff2 有完整 graft 合成记录 |
| 安全 | ✅ PASS | 无密钥、无凭证、无可执行代码 |
