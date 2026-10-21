# WBCC-0803ADF7-EXP-2026-0019 — `not in sys.path` 判的是「存在」，不是「位置」

- pattern: 为修正「同名包抢占」而向 `sys.path` 注入路径时，写成
  `if P not in sys.path: sys.path.insert(0, P)`。看起来幂等又安全，实际上
  **条件恒为假**——上游模块（本例 `core/db.py`）早已把同一个路径 insert 过，
  于是插入被跳过，路径仍停留在原来的位置，抢占问题**原样保留**，且无任何报错。
- root_cause: 把「路径在不在列表里」当成「路径在不在正确位置」。
  凡修复的正确性取决于 `sys.path` **顺序**（谁先被命中）的场景，判存在性都是错的。
  更隐蔽的是：这类失败是**静默**的——注入语句执行了、没抛错、日志正常，
  只是 `import` 仍然解析到错误的包。
- fix_template:
  1. 顺序敏感的场景一律「先移除、再置顶」：
     `while P in sys.path: sys.path.remove(P)` 然后 `sys.path.insert(0, P)`；
  2. 必须有**位置断言**的回归测试：`assert sys.path[0] == P`，
     而不是 `assert P in sys.path`（后者对 bug 版本也成立）；
  3. 测试要构造「P 已在 path 但 index>0」的初始状态，否则测不到这个分支；
  4. 用 `import` 结果本身做终局判据（本例：`app.MARK == 'real_app'`），
     而不是断言 sys.path 长什么样——前者才是业务语义。
- severity: high
- status: verified
- tags: [python, sys-path, import-shadowing, silent-failure, idempotency]
- related: WBCC-0803ADF7-EXP-2026-0015 (fail-closed), WBCC-0803ADF7-EXP-2026-0020 (test-double 假测试)
- first_seen: 2026-10-18 (change 2026-10-18-monitor-blindspot-fix BUILD，代码评审拦下阻塞缺陷)
- evidence: >-
  生产只读实测：`<PROJECT_ROOT>` 已在 sys.path index=1，`BACKEND_DIR` index=2，
  旧条件 `not in sys.path` 返回 False；顶层名 `app` 仍命中
  `<PROJECT_ROOT>/app/backend/app/__init__.py`（影子包）。
