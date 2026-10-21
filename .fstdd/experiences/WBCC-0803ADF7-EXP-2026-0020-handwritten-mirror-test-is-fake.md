# WBCC-0803ADF7-EXP-2026-0020 — 测试里「手写复刻被测逻辑」= 假测试

- pattern: 被测代码难以直接加载（依赖重、环境不匹配）时，测试改用「在测试文件里
  手写一段等价代码」来验证行为。结果：**把被测代码整段删掉，测试依然全绿**。
  另一种同源变体：stub 过度简化，例如替身只记录 SQL 不执行 `%` 解析，
  于是「裸 `%` 导致 IndexError」这个缺陷在测试中永远不出现，修复前也通过。
- root_cause: 测试与被测对象之间没有**真实的引用关系**。
  测试断言的是「我理解的逻辑」，而不是「实际运行的代码」。
  这类测试提供了虚假的安全感——覆盖率很好看，判别力为零。
- fix_template:
  1. **黄金标准**：把被测实现切到「未修复的基线版本」，重跑测试，必须失败。
     实现方式：给测试脚手架加环境变量（如 `MONITOR_IMPL=...baseline.py`），
     让同一个测试集可以指向两个版本。不失败就说明测试没测到点子上。
  2. 难加载的模块用 **AST 提取真实源码 + exec**（`ast.get_source_segment`），
     而不是手写复刻。断言对象仍是生产代码原文。
  3. 替身要**复刻被依赖行为的关键语义**，不能只做记录。
     本例：stub 必须实现 psycopg2 的 `%` 解析规则（`%%` 不消耗参数、
     其余 `%x` 消耗一个、不足抛 IndexError），否则测不到转义缺陷。
  4. 断言要落在**业务语义**上（`app.MARK == 'real_app'`），
     而不是结构上（`assert 'injection' in source`）。
- severity: high
- status: verified
- tags: [testing, test-double, mutation-thinking, false-positive, baseline-switch]
- related: WBCC-0803ADF7-EXP-2026-0019 (syspath 位置), WBCC-0803ADF7-EXP-2026-0018 (静态检查误报)
- first_seen: 2026-10-18 (change 2026-10-18-monitor-blindspot-fix BUILD，测试评审拦下 2 个假测试)
- evidence: >-
  首轮 19 个测试中，切到 baseline 后有 8 个仍然通过；其中 TC-MCI-005 与
  缺陷 B 的子进程探针属假测试。重写后 baseline 下 11 failed / 8 passed，
  通过项经逐一确认为「逻辑本就未改」的回归保护。
