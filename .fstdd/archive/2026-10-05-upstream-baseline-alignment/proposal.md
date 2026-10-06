# 上游基线对齐：固化基线快照 / 消除版本口径漂移 / 经验库对标

<!-- source_hash: b3badcb8dd9a928b -->
<!-- generated_at: 2026-10-05T03:25:03+00:00 -->
<!-- canonical: canonical/proposals/2026-10-05-upstream-baseline-alignment.yaml -->

## Why

本仓库自我定位为「上游 leonai42/stdd（MIT）的 WorkBuddy 适配层与金融扩展」，
但「上游版本」这一口径在本仓**自相矛盾**，且缺少可核验的基线快照证据：
1) 对外声明把两个不同对象混为一谈 —— ①外部上游项目的**最新发布**（= v3.0.5）；
   ②本仓 vendored 内核 `upstream/` 的**实际版本**（= 3.1.0，含本仓衍生改动）。
   NOTICE.md §1 表格写「版本 V3.0.5（master 分支）」，而同一节注记又写
   「上游版本号见 upstream/pyproject.toml（3.0.5）」—— 该文件现为 3.1.0，
   同一节内互相打架，读者无法判定哪个是真。
2) 适配层脚本 tools/install_workbuddy_skills.py 把 `version: "3.0.5"` /
   `stdd_version: "3.0.5"` 与来源横幅「来自开源项目 FSTDD … V3.0.5」**硬编码**，
   而同一脚本已能读到本仓真实发行版号（REPO_VERSION = 3.3.4）——
   生成的 skill 因此同时携带两个互相矛盾的版本号。
3) 缺少固化的上游基线快照：每次「有没有新版本」都要重新联网探针，且无从判断
   「基线是否已变」。唯一仍在活跃的上游资产 leonai42/stdd-experiences 也从未被
   纳入对标栅格。
结果：任何外部读者或协作节点按 NOTICE / README / skill 判断「本仓处于哪个版本」，
都会得到错误或矛盾答案。


## What Changes

- 版本口径双轴显式化（modified）：NOTICE.md / README.md 明确区分「外部上游项目最新发布（v3.0.5，外部锚点，附 sha / pushed_at）」与「本仓 vendored 内核版本（3.1.0）」两个口径，消除 NOTICE §1 内部自相矛盾的版本声明
- 适配层硬编码消除（modified）：tools/install_workbuddy_skills.py 的 generated frontmatter `version` / `stdd_version` 与来源横幅不再写死 3.0.5，改为由既有 REPO_VERSION + vendored 内核版本派生，使生成 skill 的版本号自洽
- 上游基线快照证据固化（new）：新增 docs/UPSTREAM_BASELINE.md，固化观测时点 / tag / HEAD sha / pushed_at / Releases 空 / 通道排除结论 + 本仓领先量清单，供后续对标直接引用，免重复联网探针
- 上游经验库对标栅格（new）：记录 leonai42/stdd-experiences 的只读对标结论 —— 我方回传边界（非回传目标）、清单中是否含我方 node 条目（实测值）、可借鉴增量
- 余留口径对齐（modified）：skills/fstdd-fin/SKILL.md 与 docs/WORKBUDDY_INSTALL_NOTES.md 的上游版本表述与上述双轴口径一致

### New Capabilities

- **upstream-baseline-alignment**：上游基线对标产物：可核验的基线快照证据（tag / HEAD sha / pushed_at / Releases 空 / 通道排除）+ 本仓领先量清单 + 经验回传边界与对标结论，单一出处、免重复探针

### Modified Capabilities

- **version-nomenclature**：版本口径双轴分离 —— 「外部上游发布」与「本仓 vendored 内核」分别声明、互不冒充；NOTICE / README / fstdd-fin / 安装文档 / 安装脚本同源自洽，不再硬编码 3.0.5

## Success Criteria

- [ ] 全仓**活体声明面**（NOTICE.md、README.md、skills/fstdd-fin/SKILL.md、docs/WORKBUDDY_INSTALL_NOTES.md、tools/install_workbuddy_skills.py）不再把本仓 vendored 内核版本写作 3.0.5；NOTICE §1 内不再存在互相矛盾的版本声明
- [ ] 上游基线快照落盘为可核验证据（tag=v3.0.5 / HEAD sha=b9a4af62b5f4fd2747884c0a61febbc341792ac2 / pushed_at=2026-08-17T15:25:43Z / Releases 空 / 其他通道排除），后续对标可直接引用，无需再次联网探针
- [ ] 生成 skill frontmatter 的 `version` 与 `stdd_version` 不再硬编码 3.0.5，与安装脚本可读到的 REPO_VERSION / vendored 内核版本自洽；重跑 tools/install_workbuddy_skills.py + tools/verify_workbuddy_skills.py 输出 PASS
- [ ] 经验库对标结论落盘：明确 leonai42/stdd-experiences 非我方回传目标，并给出「清单中我方 node 前缀条目数」的只读核对实测值
- [ ] 四自检脚本全绿：verify_rename 8/8、verify_eol 7/7、verify_skill_standards 7/7、verify_workbuddy_skills PASS
- [ ] 全量 pytest upstream/tests 0 failed
