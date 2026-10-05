# v3.3.5（在办）任务清单

## 1. 活体声明面版本轴显式化（version-nomenclature，P0）

- [x] 1.1 `NOTICE.md` §1：E 轴标明「上游最新发布」并链接 `docs/UPSTREAM_BASELINE.md`；:33 内核注记改 K=3.1.0，删除「上游版本号见 …（3.0.5）」
- [x] 1.2 `README.md` 徽章区：E 轴徽章（上游发布语义）+ K 轴徽章（3.1.0）并列；保留上游 MIT 署名
- [x] 1.3 `skills/fstdd-fin/SKILL.md`：`stdd_version` → `3.1.0`；sources 方法论基底 → K，上游溯源以 E 标注；`version` 保持 1.0.0
- [x] 1.4 `docs/WORKBUDDY_INSTALL_NOTES.md`：:5 来源仓库标 E；:89 去歧义版本词
- [x] 1.5 测试（新增 `tests/test_version_nomenclature.py`）：TC-VNOM-001..005

## 2. 适配层版本字段派生去硬编码（version-nomenclature，P0）

- [x] 2.1 新增 `_vendored_kernel_version()`（读 `.fstdd/version.yaml: upstream_version`，读不到回落 `unknown`）
- [x] 2.2 `_build_frontmatter()`：`version` ← `REPO_VERSION`（R）；`stdd_version` ← K
- [x] 2.3 来源横幅（:377）与 module docstring（:2）去硬编码版本号
- [x] 2.4 测试（新增 `tests/test_install_version_derivation.py`）：TC-VNOM-006/007/008

## 3. 上游基线快照单一事实源（upstream-baseline-alignment，P0）

- [x] 3.1 新增 `docs/UPSTREAM_BASELINE.md`：observed_at + base sha + E 全套（tag/HEAD/pushed_at/Releases/分支）+ 通道排除（Gitee/PyPI）
- [x] 3.2 本仓领先量清单（K=3.1.0 / R=3.3.4）
- [x] 3.3 上游经验库 `leonai42/stdd-experiences` 只读对标（非回传目标 + node 前缀条目数实测值 = 0）
- [x] 3.4 测试（新增 `tests/test_upstream_baseline.py`）：TC-UBL-001..006

## 4. 测试与验证

- [x] 4.1 每个切片完成 Step B3.4 切片验证（TC 覆盖 + 产出物核对 + 测试通过）
- [x] 4.2 四自检脚本全绿（rename 8/8、eol 7/7、skill_standards 7/7、workbuddy_skills PASS）
- [x] 4.3 全量 `pytest upstream/tests` 0 failed（906 passed / 54 skipped / 0 failed，与基线逐字一致）
- [x] 4.4 C1..C7 质量验证 + 23 类失败模式检查 + `test-report.md`
- [x] 4.5 停在 Gate 3 等待用户明确确认