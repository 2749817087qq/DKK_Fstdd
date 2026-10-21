# WBCC-0803ADF7-EXP-2026-0022 — AST-exec 测试的 ns 快照语义：impl 新增模块级符号，测试必须同步登记

- pattern: 用 `exec` 把真实 impl 源码里的函数提取到受控命名空间测试
  （不 import 生产模块的隔离范式）。helper `load_function(key, name, ns)`
  内部 `ns.update(globals_ns)` 后 exec——**globals_ns 是快照**：
  函数对象只在加载那一刻看见 ns 里已有的名字。GREEN 补丁给 impl 新增
  模块级常量 `DEGRADED_METRICS_JSON` 与新函数 `_metrics_root_exists`
  （后者引用前者），测试的 `_load_funcs()` 不知道这两个新符号，
  结果：纯净 RED→「修完 impl 反而 4 红」，报
  `NameError: name 'DEGRADED_METRICS_JSON' is not defined`
  —— 错误指向"修复无效"，实际是**测试脚手架缺登记**。
- root_cause: 把"提取函数源码"当成自包含动作。真实函数体的全局依赖
  （常量、同级函数）必须显式进入 globals_ns，且**依赖项必须先于使用者
  入 ns**（使用者加载时做快照）。impl 每次新增模块级符号，测试加载器
  就是一处必须同步的登记点，漏登记不会在编译期暴露，只在运行时炸。
- fix_template:
  1. 加载器按依赖序组织：**常量 → 被依赖函数 → 被测函数**，分三段循环，
     每段 `try/except LookupError` 兼容 baseline（无该符号时跳过，
     这正是 baseline 判别力所需的形态）；
  2. helper 自己的 globals_ns 要从主 ns 取（本例 `_helper_ns` 里补
     `DEGRADED_METRICS_JSON`），不能只给 `{"os","logger}` 了事；
  3. 一条判别口诀：**GREEN 后新出现的 NameError/LookupError，
     先怀疑测试 ns 登记，再怀疑 impl**——二者故障模式完全同形，
     唯一区分办法是看名字是否 impl 本轮新增；
  4. 把"impl 新增符号清单"列入补丁脚本的必跑核对项（补完 impl
     立刻 grep 一遍 `^[A-Z_]+ =|^def ` 与测试登记表对账）。
- severity: medium（测试期自伤，延误定位；不会漏过缺陷，因为 impl 侧
  错误与脚手架错误都能被 baseline 复跑区分开）
- status: verified
- tags: [ast-exec, namespace-snapshot, test-harness, green-phase, dependency-order]
- related: WBCC-0803ADF7-EXP-2026-0020 (mirror 假测试), WBCC-0803ADF7-EXP-2026-0019 (语义判定陷阱)
- first_seen: 2026-10-19 (change 2026-10-19-pipeline-defects-trio 切片 C GREEN)
- evidence: >-
  补丁后首跑 4 failed + 27 passed，失败点全部为
  `_metrics_root_exists` 内 NameError: DEGRADED_METRICS_JSON；
  `_load_funcs` 补常量登记 + helper globals_ns 传递后 31 passed，
  OPD_IMPL=baseline 判别恢复 6 红（判别力未受损）。
