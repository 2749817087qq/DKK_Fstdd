# 实现任务清单 — 2026-10-03-share-publish-sanitize

> mode: standard | task_type: code | 目标文件：tools/share_experience.py, tests/test_share_publish_sanitize.py

## 切片 S1：stage_sanitized 收口原语（P0）

- [ ] T1.1 新增模块常量 `OUTBOUND_RESIDUAL_RE`（复刻服务端判据 `/(?:home|Users)/[^\s/]+` + 凭证模式）
- [ ] T1.2 新增 `stage_sanitized(out_dir) -> (staged_dir, skipped)`：读入→`sanitize(text, True)`→残余自检→写独立临时目录→frontmatter `sanitized:` 改写
- [ ] T1.3 测试 TC-SOS-001 POSIX 家目录路径被清除
- [ ] T1.4 测试 TC-SOS-002 凭证片段被替换
- [ ] T1.5 测试 TC-SOS-003 正常标识符不被误伤
- [ ] T1.6 测试 TC-SOS-004 原目录不可变 + staged 独立
- [ ] T1.7 测试 TC-SOS-005 frontmatter sanitized 修正
- [ ] T1.8 测试 TC-SOS-006 残余命中条目被剔除且报告
- [ ] T1.9 测试 TC-SOS-007 判据常量直接断言

## 切片 S2：四条出站路径收口（P0）

- [ ] T2.1 `publish_via_inbox`：入口 stage，发送源改 staged_dir，finally 清理
- [ ] T2.2 `publish_via_scp`：入口 stage，scp 源改 staged_dir，finally 清理
- [ ] T2.3 `publish()` GitHub 分支：拷贝源改 staged_dir
- [ ] T2.4 `publish_via_pr`：拷贝源改 staged_dir
- [ ] T2.5 测试 TC-SOS-008 inbox POST body 无残留（本地 stub 端点）
- [ ] T2.6 测试 TC-SOS-009 scp 源为 stage
- [ ] T2.7 测试 TC-SOS-010 GitHub 直推拷贝源为 stage
- [ ] T2.8 测试 TC-SOS-011 fork+PR 拷贝源为 stage
- [ ] T2.9 测试 TC-SOS-012 端到端静默回传零阻塞 + 审计留痕
- [ ] T2.10 全量回归无新增失败