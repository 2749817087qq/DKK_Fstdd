# Fstdd 改名任务清单

## 1. 独立命名空间（P0）

- [ ] 1.1 编写断言脚本 `tools/verify_rename.py`（承载 6 个 TC）
- [ ] 1.2 【RED】运行断言脚本，确认全部失败（尚未改名）
- [ ] 1.3 【S1】实现单次扫描替换引擎（正则 alternation + re.sub）
- [ ] 1.4 【S1】执行标识层替换（skill 名/环境变量/哨兵/项目名/文档）
- [ ] 1.5 【S1】重命名 skills/stdd-fin → skills/fstdd-fin
- [ ] 1.6 【S1】验证 TC-RENAME-001、TC-RENAME-002 通过
- [ ] 1.7 【S2】重命名 upstream/bin/stdd → upstream/bin/fstdd
- [ ] 1.8 【S2】重命名 Python 包 upstream/stdd/ → upstream/fstdd/ 并同步 import
- [ ] 1.9 【S2】验证 TC-RENAME-003（CLI 冒烟）、TC-RENAME-004（隔离安装）通过
- [ ] 1.10 【S3】迁移数据目录 .fstdd/ → .fstdd/
- [ ] 1.11 【S3】验证 TC-RENAME-005（历史资产可访问）通过
- [ ] 1.12 【S3】验证 TC-RENAME-006（三项校验全绿）通过

## 2. 测试与验证（P0）

- [ ] 2.1 每个切片完成后执行 Step B4 切片验证（TC 覆盖 + 产出物核对 + 测试通过）
- [ ] 2.2 记录每切片的 tc_coverage / new_tests / verified_at 到 .fstdd.yaml
- [ ] 2.3 全量回归：三项校验脚本全部通过
- [ ] 2.4 失败模式检查（12 项，全量执行不得占位）
- [ ] 2.5 生成 test-report.md

## 3. 交付准备（P1）

- [ ] 3.1 提交改名成果
- [ ] 3.2 更新 README / NOTICE 反映新名称
- [ ] 3.3 确认经验回传链路在新仓库名下仍可达（P2，可延后）

<!--
优先级说明：
- P0：阻塞性任务，完成前无法进入下一阶段
- P1：重要任务，应在当前阶段完成
- P2：可延后到后续版本的任务

切片说明：
- S1 标识层：TC-RENAME-001/002
- S2 CLI 与包：TC-RENAME-003/004
- S3 数据目录：TC-RENAME-005/006
-->
