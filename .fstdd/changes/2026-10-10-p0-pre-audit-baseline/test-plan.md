# test-plan.md — P0-pre 审计基线批次

**约定**: 每切片 RED（先写失败测试）→ GREEN（最小实现）→ REFACTOR；测试结果入 test-report.md

## 切片 1：packaging（对应 spec-packaging）
| # | 用例 | 类型 | 验证 |
|---|---|---|---|
| T1.1 | 干净 venv pip install -e .[test] 后 fstdd --help 退出码 0 | 手工+脚本 | SC-1 |
| T1.2 | pytest upstream/tests 全绿且与打包前结果一致 | 脚本 | SC-2 |
| T1.3 | import yaml/jinja2/requests/fstdd 成功 | 脚本 | SC-3 |
| T1.4 | wheel 内容不含 skills/tools/docs | 脚本（unzip -l） | 边界 |

## 切片 2：patches-registry（对应 spec-patches-registry）
| # | 用例 | 类型 | 验证 |
|---|---|---|---|
| T2.1 | 表头 8 列齐全、基线声明存在 | 脚本解析 | SC-1/2 |
| T2.2 | 待登记区含 experience.py:428 | 人工 | SC-3 |

## 切片 3：validate 检查项（对应 spec-validate-upstream-patches）
| # | 用例 | 类型 | 验证 |
|---|---|---|---|
| T3.1 | 登记表正常 → 通过 | pytest | SC-1 |
| T3.2 | 登记路径不存在 → 非零退出且指明路径 | pytest | SC-2 |
| T3.3 | 登记表缺失 → 非零退出 | pytest | SC-3 |
| T3.4 | 注入未登记 upstream/ 修改 → **不报错**（显式锁定 D-1 非行为，防范围蔓延） | pytest | 非行为 |

## 切片 4：审计脚本入库 + 真实基线（对应 spec-audit-baseline）
| # | 用例 | 类型 | 验证 |
|---|---|---|---|
| T4.1 | 合成夹具全边界回归（单块/双块/导出块缺真身/共享分隔线/正文截断） | pytest（夹具随脚本入库） | SC-1/2/3 |
| T4.2 | 夹具注入 eid 不一致条目 → 计入 eid_mismatch.files | pytest | SC-4 |
| T4.3 | 夹具索引缺某 eid → indexed_false_files 命中 | pytest | SC-5 |
| T4.4 | **真实仓库实跑**：产出 audit-2026-10-experience-baseline.json，退出码 0 | 实跑 | SC-1~7 |
| T4.5 | SC-4 对账：affected_files 与团队 46 文件清单逐一对账，差异记录原因 | 人工留痕 | proposal SC-4 |
| T4.6 | 实跑确认 EXP-1BA44745.md eid_match=false（若本地与镜像一致） | 实跑 | SC-4 |

## 质量门槛（Gate 3 准入）
- 四自检 + test_a6 全绿；verify_eol 无新增混合态（脚本/文档一律 LF 写入）
- 变异自检：对 audit 脚本注入 1 处块解析缺陷，夹具必须变红
- 全量真实基线 JSON 归档并在 test-report 中引用 git HEAD
