# build-runbook.md — P3 BUILD 执行手册（change 2026-10-10-p0-pre-audit-baseline）

**前置**: Gate 1 ✅（18:26）/ Gate 2 ✅（18:32）+ 本目录全部工件
**执行环境**: E:/FSTDD/stdd-repo（本地真值源；GitHub 镜像数据仅作方向性预验证，D-4）
**总原则**: 切片内 RED→GREEN→REFACTOR；每切片完成即记录 test-report；发现 spec 与仓库现实冲突 → **停刀上报，不静默改 spec**

## 切片 1 · packaging（T1.1–T1.4，预计 ≤0.5 天）
1. 复制 `pyproject.toml` → 仓库根
2. `python -m venv .venv-test && .venv-test\Scripts\activate`
3. `pip install -e ".[test]"` → `fstdd --help`（期望退出码 0）
4. `pytest upstream/tests` 全绿
5. wheel 不含 skills/tools/docs：`pip wheel . -w /tmp/w && unzip -l` 人工核对
- 记录: 安装日志 + pytest 摘要入 test-report.md

## 切片 2 · patches-registry（T2.1–T2.2，≤0.5 天）
1. 复制 `UPSTREAM_PATCHES.md` → `docs/UPSTREAM_PATCHES.md`
2. 将「待登记」区 experience.py:428 一行移入正式表（动它之前先登记——登记表先于修改）
3. T2.1 脚本解析核对表头/基线声明；T2.2 人工

## 切片 3 · validate 检查项（T3.1–T3.4，≤1 天）
1. 复制 `validate_upstream_patches.py` → `tools/`
2. 集成点（须先实读 upstream/fstdd/ 的 validate 命令组，确认挂载位置）：
   推荐以子进程方式挂载：validate 执行到该检查项时调用
   `python tools/validate_upstream_patches.py --repo <repo-root>`，映射退出码 0/1
3. 复制 `tests/test_governance_baseline.py` → `tools/tests/`（夹具与测试同批入库）
4. `pytest tools/tests -q` → 12 passed（T3.x 六项 + T4.1–T4.3 五项 + 只读/退出码一项）
5. 变异自检: 将检查器的表头比对临时改为 7 列 → T3.1 必须变红 → 恢复
- 冲突预案: validate 无子进程挂载点 / 退出码语义不同 → 停刀上报，附实读的 validate 代码段

## 切片 4 · 审计脚本入库 + 真实基线（T4.4–T4.6，≤0.5 天）
1. 复制 `audit_experience_baseline.py` → `tools/`
2. 实跑：
   `python tools/audit_experience_baseline.py --repo . --out .fstdd/experiences/audit-2026-10-experience-baseline.json`
3. T4.4 退出码 0 + JSON 结构核对（schema 见 design.md §4）
4. T4.5 对账（关键判据）: affected_files vs 团队 46 文件清单逐一对账
   - 完全一致 → 基线可信，记录「对账一致」
   - 不一致 → 以实跑为准，逐条记录差异原因（镜像滞后/本地新增/清单过时），不得改脚本凑数
5. T4.6 复核 EXP-1BA44745.md 的 eid_match（镜像显示 false；本地若不同，记录差异）
6. 基线 JSON 连同 test-report 归档；git HEAD 写入 audit_meta（脚本自动）与 test-report

## 完成定义（Gate 3 准入自检）
- [ ] 切片 1–4 全部完成，test-report.md 含每切片证据
- [ ] `fstdd validate` 四自检全绿（干净工作树）
- [ ] 本 change 未触碰范围外任何文件（git diff --name-only 核对白名单：
      pyproject.toml / docs/UPSTREAM_PATCHES.md / tools/validate_upstream_patches.py /
      tools/audit_experience_baseline.py / tools/tests/test_governance_baseline.py）
- [ ] T4.5 对账结论落档
- [ ] 变异自检记录（切片 3）

## 已知留待后续 change（不得顺手做）
- experience.py:428 修复 + reindex 归一化（Phase 1.1 修复批次）
- CRLF（上游 PR 路线）/ archive 两阶段 / ci 三面三数
- 哈希级 upstream 漂移检测（D-2：下次同步上游前必须落地）
