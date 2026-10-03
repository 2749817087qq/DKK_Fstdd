# 首次跑 install_workbuddy_skills.py + verify — 从 6 FAIL 到 6 PASS

<!-- source_hash: 156e3a9db135a0cf -->
<!-- generated_at: 2026-10-03T02:15:25+00:00 -->
<!-- canonical: canonical/proposals/2026-10-03-skill-install-verify.yaml -->

## Why

连续 5 个 commit 修改了 skill 文件（understand.md +build.md + SKILL.md），
但 .workbuddy-ai/skills 目录根本不存在 — 从来没跑过 install 脚本。
verify 第一次跑报 6 FAIL（所有 skill SKILL.md 不存在）。
install 脚本配了 LOCAL_SKILLS=["fstdd-fin"] + 7 个 skill 的 source 路径，
但没人触发过 mkdir + copy。


## What Changes

- 创建 .workbuddy-ai/skills 目录，首次安装 7 个 FSTDD skill
- 确认 installed skills 包含最新 upstream 变更（understand Step 0.5 + build C4 table）

### New Capabilities

- **skill-install-verified**：install_workbuddy_skills.py + verify_workbuddy_skills.py 全链路跑通，作为后续 upstream sync 基线

## Success Criteria

- [ ] .workbuddy-ai/skills 目录存在，含 7 个子目录（fstdd + 4 阶段 + upgrade + fstdd-fin）
- [ ] verify_workbuddy_skills.py exit code 0
- [ ] installed fstdd-build SKILL.md 包含 22 行 C4 table（确认 upstream 变更同步）
- [ ] installed fstdd-understand SKILL.md 包含 Step 0.5 金融钩子（确认 upstream 变更同步）
