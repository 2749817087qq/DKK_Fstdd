# 测试套件环境健壮性与遗留债务清理

<!-- source_hash: f4c5b29793c2d38f -->
<!-- generated_at: 2026-10-06T13:52:26+00:00 -->
<!-- canonical: canonical/proposals/2026-10-06-legacy-debt-cleanup.yaml -->

## Why

四项经实测确认的遗留债务长期挂账，共同后果是「门禁不可信」—— 红灯可能是环境噪声，
绿灯可能漏测：
1) 测试套件对环境编码敏感：用例普遍用 subprocess(text=True) 而不指定 encoding=，
   解码因此走 locale。同一份代码在「控制台 UTF-8 + PYTHONUTF8=1」下 906 passed /
   0 failed，一旦换环境即红 —— 不设 PYTHONUTF8 时 9 例因用 gbk 解本仓 CLI 的 UTF-8
   输出而炸；只设 PYTHONUTF8 而控制台非 UTF-8 时，PowerShell 的 GBK 输出被按 UTF-8
   解而炸（tests/test_multi_platform.py 2 例）。
2) 发布清单与实际仓库结构不符，且根 tests/ 带预存失败：
   .fstdd/standards/release-and-docs.md 明文写「仓库根**没有** `tests/`」，
   而根 tests/ 实际存在（9 个测试文件）；tests/test_finance_content.py::test_L1_11
   硬编码 fstdd_version == "3.3.0"，自 3.3.1 起已过期；tests/test_multi_platform.py
   2 例失败与 (1) 同源。
3) 一条归档 change 的 canonical 哈希欠账：
   canon verify 2026-09-18-inbox-api-only-write 仅 1/2，DC-HASH 源哈希不一致
   （YAML 29c0012fe4d0b612 vs 归档 proposal.md 16fa0e448d063e2a）。
4) _scratch/ 误入库 20MB：git ls-files 显示 27 条目已跟踪（25 普通文件 +
   2 个 gitlink/内嵌 git 仓库），含 13.4MB red_pytest.log；.gitignore 从未包含
   _scratch/。2026-09-18 change 的 test-report 曾声称「_scratch/ 已 gitignored」，
   该断言为假。


## What Changes

- 测试套件环境健壮性（modified）：为 upstream/tests、tests/、tools/ 下 16 文件 36 处 subprocess(text=True) 显式补 encoding="utf-8", errors="replace"，使门禁在任意 locale 下稳定，不再依赖 PYTHONUTF8/控制台编码
- 发布清单纠错（modified）：.fstdd/standards/release-and-docs.md 更正「仓库根没有 tests/」的失真表述，改为反映根 tests/ 的存在与其执行口径
- 预存失败修正（modified）：tests/test_finance_content.py::test_L1_11 由硬编码 "3.3.0" 改为动态读取 .fstdd/version.yaml 的 fstdd_version；tests/test_multi_platform.py 2 例随编码修复转绿
- canonical 哈希补齐（modified）：.fstdd/archive/2026-09-18-inbox-api-only-write/proposal.md 的 source_hash 16fa0e448d063e2a 改为 29c0012fe4d0b612，使 canon verify 恢复 2/2
- _scratch 取消跟踪（removed）：git rm -r --cached _scratch/（27 条目，含 2 个 gitlink）+ .gitignore 增 _scratch/；磁盘文件一律保留

### Modified Capabilities

- **test-suite-portability**：测试套件在任意 locale / 控制台编码下结果稳定：subprocess 文本调用显式指定 UTF-8 解码，门禁不再依赖 PYTHONUTF8 与 chcp 的隐式配合
- **release-tooling-accuracy**：发布清单与实际仓库结构一致；根 tests/ 断言不再硬编码过期版本号，改为动态读取单一事实源
- **canonical-hash-integrity**：canonical proposal 的 YAML 与 MD 源哈希一致，canon verify 全绿
- **repo-hygiene**：非发布物（_scratch/）不入库：取消跟踪 + gitignore，仓库体积回落，内嵌 git 仓库引用解除

## Success Criteria

- [ ] 权威门禁环境（控制台 UTF-8 + PYTHONUTF8=1 + PYTHONIOENCODING=utf-8）下全量 pytest 0 failed
- [ ] 非 UTF-8 环境下 tests/test_multi_platform.py 2 例（test_install_sh_passes_platform / test_install_ps1_passes_platform）不再因 UnicodeDecodeError 失败
- [ ] canon verify 2026-09-18-inbox-api-only-write = 2/2
- [ ] git ls-files _scratch/ 为空，且 _scratch/ 在 .gitignore 中，且磁盘文件与 2 个 gitlink 实体仍在
- [ ] tests/test_finance_content.py::test_L1_11 在任意 fstdd_version 下动态通过
- [ ] 四自检脚本全绿：verify_rename 8/8、verify_eol 7/7、verify_skill_standards 7/7、verify_workbuddy_skills PASS
