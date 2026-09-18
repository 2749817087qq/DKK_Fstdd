# 静默失效系统性排查：让每个「零命中」的检测都证明自己在干活

<!-- source_hash: cc17af1937a02bff -->
<!-- generated_at: 2026-09-18T00:45:35+00:00 -->
<!-- canonical: canonical/proposals/2026-09-18-silent-failure-audit.yaml -->

## Why

检测/校验/告警逻辑被 `except` 吞掉异常后会**静默全哑**——不报错、不告警、
输出看起来一切正常，但保护早已失效。这是比崩溃更糟的失败形态：
崩溃至少告诉你坏了，静默失效让你**以为**有保护。

这不是假想。2026-09-17 的 time-baseline change 全量回归抓出实证（EXP-20260917-B3）：

  - `upgrade.py:340` 与 `guard.py:196,517` 三处写成 `_dt.now(_dt.timezone.utc)`
    （`_dt` 是 datetime **类**、timezone 是**模块**属性）→ 必抛 AttributeError
  - 全部被外层 `except Exception` 吞掉 → **guard 的僵尸 change 检测与卡壳检测
    长期全哑，无人知晓**；直到真实路径被测试执行才暴露
  - 更隐蔽的是：静态检测器（check_timestamps L2）只查「now() 是否带时区参数」
    的**形态**，`_dt.timezone.utc` 形态上"正确"——检测器给了假安全感

而这类点位全仓有多少？2026-09-18T08:34Z 只读实测（观测时 HEAD = 6c5d390）：

  | 统计口径 | 数量 |
  |---|---|
  | `except [Exception]` 块首语句为 pass/continue/空返回 的总点位 | **29 处 / 16 个文件** |
  | 其中文件名含检测语义的（check/verify/guard/validate…） | **11 处 / 4 个文件** |
  | 密度最高 | guard.py 6 处、status.py 3 处、check_timestamps.py 3 处 |

29 处中大部分是**合理的**（探测类操作失败返回 None，如 ssh 不可达），
但「合理」目前只靠读代码的人眼判断——没有任何机制区分
「故意容错」与「意外吞错」。这正是 A1 经验的同族问题：
工具自身故障与产物缺陷不可区分。

危害是**复利式**的：每多一处哑检测，用户对「绿」的信任就被稀释一分；
当真正的缺陷出现时，它混在一片假绿里没人看。


## What Changes

- 29 处吞异常点位逐个审计，分类为「故意容错」/「意外吞错」/「需收窄异常类型」，意外吞错处修复并补测试
- 对 ≥3 处关键检测路径建立变异测试（注入已知缺陷验证检测真的会红）
- 新增 tools/audit_silent_except.py：枚举吞异常点位并强制要求逐条标注豁免理由（带理由清单入仓），无理由的新增点位在 CI 报出
- except 块内一律留痕（logger.debug 最低限度），禁止裸 pass 出现在检测/校验函数
- 方法论沉淀：经验条目 + stdd-build skill 的验收清单增项（新检测逻辑必须附变异测试）

## Success Criteria

- [ ] 29 处点位 100% 有审计结论（容错豁免 / 修复 / 收窄异常类型），逐条记录理由
- [ ] 关键检测路径（guard 僵尸/卡壳、check_timestamps L1/L2、validate 基线警告）各有 ≥1 个变异测试，注入已知缺陷必红
- [ ] audit_silent_except.py 入仓并纳入 CI：未标注理由的新增吞异常点被报出（含自证：对当前 29 处全过）
- [ ] 全量工程测试无回归（基线 692 passed / 694 collected）
- [ ] 经验条目入库（.fstdd/experiences/EXP-20260918-*.md），stdd-build 验收清单增项落地
