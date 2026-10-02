# 项目改名为 Fstdd（F=Fin）并独立于上游

<!-- source_hash: 7725e65e32f7efcd -->
<!-- generated_at: 2026-09-15T22:42:05.580762 -->
<!-- canonical: canonical/proposals/2026-09-15-rename-to-fstdd.yaml -->

## Why

本项目当前名为 DKKstdd，其 skill 名、CLI 命令名、数据目录、Python 包名
全部沿用上游 STDD 的命名。本机曾并存另一套同名实现
（vsem-azamat/stdd，plugin build v0.11.0），两套都叫 stdd、
都用 .fstdd/ 目录、都提供 stdd CLI，混装会互相干扰。
手工改名尝试已证明风险：364 处替换后第一处验证即失败
（STDD_SRC → FSTDD_SRC → FFSTDD_SRC 双重替换，环境变量全部失效）。


## What Changes

- skill 名 stdd-* → fstdd-*（6 个：fstdd、fstdd-understand/spec/build/deliver/upgrade）
- CLI 入口 upstream/bin/stdd → upstream/bin/fstdd
- 环境变量 STDD_SRC/STDD_OUT/STDD_PY/STDD_CLI → FSTDD_*
- 哨兵 STDD_LOCAL_POLICY_NO_UPLOAD_V1 → FSTDD_LOCAL_POLICY_EXPERIENCE_UPLOAD_V1
- 数据目录 .fstdd/ → .fstdd/（含现有数据迁移）
- Python 包 upstream/stdd/ → upstream/fstdd/
- 项目名 DKKstdd → Fstdd（含 README/NOTICE 等文档）
- 移除上游同步机制（upgrade skill 改为自管理版本）

### New Capabilities

- **独立命名空间**：全部标识使用 fstdd/FSTDD 前缀，与同名 STDD 实现彻底区分

### Modified Capabilities

- **skill 集合**：6 个 skill 由 stdd-* 更名为 fstdd-*，触发词同步更新
- **CLI**：入口与 Python 包更名为 fstdd，内部 import 路径同步调整

## Success Criteria

- [ ] SC1: 环境变量名恰为 FSTDD_SRC / FSTDD_OUT / FSTDD_PY / FSTDD_CLI，且全仓库不存在 FFSTDD_ 形式
- [ ] SC2: upstream/bin/fstdd --help 可执行，usage 行显示 fstdd
- [ ] SC3: install 脚本生成 6 个 fstdd-* skill 目录，verify 输出 PASS
- [ ] SC4: 除 upstream/ 与 .git 外，无残留的独立 stdd 标识（grep 词边界验证）
- [ ] SC5: 数据目录迁移后，fstdd status 可列出两个已归档 change
- [ ] SC6: 三项校验（verify_eol / verify_skill_standards / verify_workbuddy_skills）全部通过
