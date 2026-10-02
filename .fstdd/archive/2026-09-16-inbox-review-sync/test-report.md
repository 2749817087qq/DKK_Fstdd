# inbox-review-sync 测试报告

> 变更：`2026-09-16-inbox-review-sync`
> 执行日期：2026-09-17
> 执行环境：Windows，Python 3.11.9（`C:\Python311\python.exe`）
> 测试位置：`D:/tools/FSTDD/stdd-repo/upstream`

## 一、执行结果总览

| 测试文件 | 结果 |
|---|---:|
| `tests/test_inbox_pull.py` | **23 passed** |
| `tests/test_inbox_endpoint.py` | **44 passed** |
| 本 change 相关测试合计 | **67 passed / 0 failed** |

执行命令：

```bash
cd D:/tools/FSTDD/stdd-repo/upstream
C:/Python311/python.exe -m pytest tests/test_inbox_pull.py tests/test_inbox_endpoint.py -q
```

退出码：0。

## 二、追溯覆盖

| 范围 | 结果 |
|---|---|
| TC-IRS-001 ~ TC-IRS-016 | **16/16 有测试标注** |
| 测试标注位置 | `upstream/tests/test_inbox_pull.py` |
| 覆盖差集 | 0（test-plan 中的 TC 均在测试文件出现） |
| 端点批量/限流回归 | `test_inbox_endpoint.py`，44 项通过 |

## 三、验证内容

- 审核池读取、元数据解析、异常输入处理：已由 `test_inbox_pull.py` 覆盖。
- 脱敏与发布逻辑：已由 `test_inbox_pull.py` 覆盖，复用现有 `share_experience.py` 脱敏契约。
- 单条/批量协议、按条数限流、429 `Retry-After`、拒绝不计数、重试：已由 `test_inbox_endpoint.py` 覆盖。
- 客户端批量回传参数与端点协议：已由两个测试文件共同覆盖。

## 四、与全量回归的区别

此前已在同一 D 盘法定源上执行过全量套件，结果为 **562 passed / 0 failed**。本报告的 67 passed 是本 change 的针对性子集，不将其冒充全量结果。

## 五、当前收尾阻塞

代码和测试证据已具备，但 `.fstdd.yaml` 当前仍缺 `phases.build.slices_completed` 的受控写入记录。FSTDD 的 `phase advance` 会拒绝缺少 per-slice `tc_coverage/new_tests/verified_at` 的 BUILD→DELIVER 推进。因此本 change 暂不宣称已完成 Gate 3 或可归档；必须先通过受控 FSTDD CLI/流程补足证据，禁止手改 `.fstdd.yaml`。
