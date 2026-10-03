# 测试报告 — 2026-09-19-notices-authenticity-gate

> 生成日期：2026-10-04（收口追溯）
> mode: thorough | task_type: code
> 证据基础：实现提交 `3493217`；本次收口唯一改动为 `tools/test_verify_notices.py` 的
> TC-NEP-003 节点本地断言 skipif 化（不改变被验证契约）。

## 一、覆盖总览

| 项 | 数值 |
|---|---|
| Spec 需求 | REQ-001..006（6） |
| Spec 场景 | SC-001..018（18） |
| 测试用例（TC） | 21（TC-NAV-001..018 + TC-NEP-001..003） |
| 测试函数 | 21（与 TC 一一对应） |
| 测试文件 | `tools/test_verify_notices.py` |
| Scenario 覆盖率 | **18/18 = 100%** |

## 二、切片完成度

| 切片 | 覆盖 | TC | 状态 |
|---|---|---|---|
| S1 清单比对与降级 | REQ-001/002 | TC-NAV-001..005、016..018（8） | ✅ |
| S2 凭证嗅探与隔离 | REQ-003/004 | TC-NAV-006..011（6） | ✅ |
| S3 CLI 退出码与 JSON | REQ-005 | TC-NAV-012..015（4） | ✅ |
| S4 零回归与收口 | REQ-006 | TC-NEP-001..003（3） | ✅ |

## 三、测试执行结果（实测）

| 命令 | 结果 |
|---|---|
| `pytest tools/test_verify_notices.py -q` | **20 passed / 1 skipped / 0 failed** |
| `pytest upstream/tests -q`（全量回归，收口前基线） | **887 passed / 54 skipped / 0 failed** |
| 四自检脚本（rename 8/8、eol 7/7、skill_standards 7/7、workbuddy_skills PASS） | 全绿（随 3.3.2 发布门禁实测） |

**1 skipped 说明（显式记录，非静默）**：`test_TC_NEP_003_token_file_unchanged_and_not_referenced`
断言「场景节点本地保留的旧凭证证据文件 `.fstdd/_fstdd003_token.txt` 内容与 mtime 不变」。
该文件是 incident 现场证据（gitignored、不随仓库分发），仅存在于事发节点；非场景节点上该前置条件不成立。
本次将该断言改为：**仓库侧不变量（校验器绝不引用该路径）始终执行**，节点本地前置条件缺失时 `pytest.skip`。
被验证的行为契约未变，仅消除非场景节点上的假红。

## 四、失败模式检查（23 类要点摘录）

| 类别 | 结论 |
|---|---|
| 静默假设 | 清单缺失/空清单/畸形行/目录缺失四态均有显式降级用例（S1） |
| 看似正确实则错误 | 退出码 2 与 3 并存时 3 优先，已用组合用例固定（TC-NAV-014） |
| 幻觉 API | 仅用 stdlib + pytest，无外部依赖 |
| 删除但仍被引用 | 本变更无删除；`fstdd003_daily_share.py` 零改动（TC-NEP-001） |
| 无动机改动 | 本次唯一改动为 TC-NEP-003 的 skipif 化，动机=消除节点本地假红，已在 tasks.md 声明 |
| 凭证外泄 | 四个输出面（stdout/stderr/隔离记录/git 对象）字面搜索断言（TC-NAV-010） |
| 误隔离 | 上界固定为 0，5 份真实格式 fixtures 全 verified（TC-NAV-008） |
| 回归破坏 | `tools/` 域原本零测试，本变更自带 3 条零回归断言（TC-NEP-001/002/003） |
| 其余类别 | 无命中 |

## 五、设计偏离

Phase 3（BUILD）**无功能层面偏离**（`design-adjustments.md` 的 5 项 AD-1..AD-5 均发生于 Gate 2 之前的 Phase 2 内自我修正）。
本次收口新增 1 项**测试实现微调**（TC-NEP-003 skipif 化），已在 `tasks.md` 头部显式声明，不构成设计偏离。

## 六、结论

- Scenario 覆盖 18/18；TC 21/21 实现并与测试函数一一对应；本变更单跑 **0 failed**。
- 全量回归 **0 failed**；四自检全绿。
- **可就绪 Gate 3**，风险等级：低。
