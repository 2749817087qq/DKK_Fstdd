# 设计决策 — 2026-09-18-detection-silence-fixes

**范围**：审计表 15 处「意外吞错」修复 + F-1/F-2 + guard.py:315 勘误
**总原则**：**失败有声**——所有修复只把静默跳过改为可见警告或安全默认值，**不改任何检测阈值**。

---

## D1 统一修复模式：警告走 stderr，默认值保持安全方向

每个修复点遵循同一形态：

```python
except SpecificError:
    print(f"  ⚠️ <检测名>: <失败原因>，本次检测跳过", file=sys.stderr)
    return <安全默认值>
```

- 警告一律 `stderr`（stdout 留给结构化输出，避免污染管道）。
- 安全默认值方向不变（守卫类 fail-closed、计数类返回 0/空并声明不可用）。

## D2 naive 时间戳归一策略：缺时区按 UTC 解释，零警告

写入方（CLI）本就写 UTC，legacy naive 值是历史数据。**归一不告警**（否则老
change 全员刷警告，噪声淹没真问题）；只有**格式完全不可解析**才警告。
归一形态：`dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)`，三处同构。

## D3 F-1 僵尸活跃豁免：取消豁免，活跃停滞 change 照常上报并加标注

`_show_zombie_changes` 删除 `d.name == current_name` 跳过；活跃 change
进入僵尸清单时名字后加 `（当前活跃）`。理由：停滞判据是 `last_modified`
距今 >7 天，与是否活跃无关——活跃 8 天未动同样是僵尸候选。

## D4 F-2 接线点：cmd_guard_status 输出滞后警告段

`_check_phase_integrity_guard` 已有完整逻辑且经变异测试验证存活，接入
`cmd_guard_status` 末尾打印段。不接入 `guard check`（钩子热路径，每次编辑
都跑，滞后警告属低频状态信息）。段名：`Phase Lag 警告`。

## D5 check_timestamps 覆盖可观测：scan_errors 进报告

三个扫描循环（源码逐文件 / change YAML / proposal.md 头）的文件级失败
不再 `continue` 静默跳过，改记 `{category: "scan_error", location}`。
`full_scan` 返回新增 `scan_errors` 列表与计数。「零违规」断言从此不能把
扫描失败混进去——**覆盖缺口可观测**。

## D6 审计勘误流程：实证改判 + 留痕，不改归档表

guard.py:315 经实现前实证（except 路径 `return False` = 不放行 =
**fail-closed**，安全方向），原 P1「fail-open」误判撤销，改判**合理容错**。
- 归档审计表**不回改**（哨兵只校验位置指纹不校验分类字段）。
- 勘误对照进本 change 的 test-report + 经验沉淀（K-EXP）。
- 后续新审计引用此勘误。

## D7 测试策略：每修复点 ≥1「有声」断言 + CLI 级端到端

- 单元级：capfd 断言 stderr 警告，或返回值/报告字段。
- 端到端：F-1（status CLI）、F-2（guard status CLI）CLI 级验证。
- 审计表刷新后哨兵 `--check` 通过作为 XCUT 门槛。
