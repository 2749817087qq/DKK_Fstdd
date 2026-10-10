<!-- fstdd-inbox
experience_id: EXP-FSTDD004-probe-object-assign-key-collision
author: anonymous
received_at: 2026-10-09T16:44:40.949773+00:00
remote_addr: 172.18.0.8
node_id: FSTDD004
-->

---
exported_at: 2026-10-10
sanitized: true
lifecycle_state: deposited
---
---
experience_id: FSTDD004-probe-object-assign-key-collision
category: test_harness_pitfall
severity: medium
date: '2026-10-03'
node: FSTDD004
title: ① 探针输出里出现「合并柱 n=1」而页面 tooltip 明写「合并 2 个报告期」这类自相矛盾
occurrences: 1
pattern: E2E 探针把「业务侧数据」与「DOM 侧数据」合并成一个对象时用了 Object.assign({}, ok, tip)，而两个来源里有一个同名字段：tip.n
  表示 DOM 里匹配到的候选节点数（恒为 1），ok.n 表示该分红事件合并的报告期数（可能为 2）。后者被前者静默覆盖，探针输出「合并柱 mk=2024-04
  n=1 Σdpu=0.5943」，与页面 tooltip 实际显示的「合并 2 个报告期」直接矛盾。危险之处在于它不报错、还会让基于 n 的断言（如 n>=2判合并生效）恒为红或恒为真，掩盖真实缺陷。
root_cause: 用「宽泛的键名（n/count/len）」承载不同语义的数据源，且依赖浅合并做汇总；JS 对象浅合并不做类型或语义校验，同名即覆盖。修法是给键名加来源前缀（DOM
  侧用 nodes/domCount），并在合并后打印全部字段供人工核对。
detection_trigger: ① 探针输出里出现「合并柱 n=1」而页面 tooltip 明写「合并 2 个报告期」这类自相矛盾；② Object.assign
  / {...a, ...b} 合并后某个字段值意外变成另一个含义；③ 断言失败信息里两个变量名相近、值不同（如 tip.n vs ok.n）；④ 用同一个键名承载两种语义后，某个断言恒为真。
fix_template: '// ✅ 不同语义用不同键名，一眼可辨

  const ok = pickMergedBar(ev);        // ok.n   = 合并的报告期数（业务语义）

  const t  = readTooltipDom();// t.nodes = DOM 候选节点数（物理语义）

  ok(''合并柱期数 >= 2'',ok.n >= 2);

  ok(''tooltip 期数与事件一致（防语义撞车）'', t.n >= 2);


  // ❌ Object.assign 静默覆盖，n 被 DOM 节点数顶掉

  // const r = Object.assign({}, ok, tip);   // r.n === 1，即使 tooltip 显示 2 期


  // ✅ 合并后逐字段打印，肉眼可查冲突

  console.log(''[merge-probe]'', JSON.stringify({ okN: ok.n, domNodes: t.nodes, tipText:
  t.text }));


  // ✅ 变量重名也要查：同一作用域内两次 const multi =

  // SyntaxError: Identifier ''multi'' has already been declared（Node 直接报错，早发现）'
tags:
- e2e
- probe
- object-assign
- silent-overwrite
- key-collision
- test_harness_pitfall
language: javascript


## 现场

探针把业务侧与 DOM 侧数据合并：

```js
const r = Object.assign({}, ok, tip);
ok('合并柱期数', r.n >= 2);              // r.n 已被 tip.n 顶掉
```

`ok.n` 是该分红事件合并的报告期数（2），`tip.n` 是 DOM 里匹配到的候选节点数（1）—— 同名浅合并，后者静默覆盖前者。

输出报「合并柱 mk=2024-04 n=1 Σdpu=0.5943」，而页面 tooltip 明写「合并 2 个报告期」，自相矛盾。同一次排查里还撞上 `const multi` 重复声明的 SyntaxError（E1 已用过同名变量）。

## 处置

DOM 节点数改名 `nodes`（业务期数仍叫 `n`），并加断言 `tipRead 返回的期数与事件一致`；合并后逐字段打印供人工核对。

## 教训

1. 合并不同来源的数据对象时，键名必须自带来源语义（`n` vs `nodes`）。浅合并不校验语义，同名即静默覆盖。

## 改善方法

- 根因：用「宽泛的键名（n/count/len）」承载不同语义的数据源，且依赖浅合并做汇总；JS 对象浅合并不做类型或语义校验，同名即覆盖。修法是给键名加来源前缀（DOM 侧用 nodes/domCount），并在合并后打印全部字段供人工核对。
- 检测信号：① 探针输出里出现「合并柱 n=1」而页面 tooltip 明写「合并 2 个报告期」这类自相矛盾；② Object.assign / {...a, ...b} 合并后某个字段值意外变成另一个含义；③ 断言失败信息里两个变量名相近、值不同（如 tip.n vs ok.n）；④ 用同一个键名承载两种语义后，某个断言恒为真。
- 修复模板：见 frontmatter `fix_template`。

> 迁移自工作区经验库 EXP-2026-0084 / change 2026-10-02-fcbar-event-aggregate
> （inbox 端点 HTTP 401 未送达 —— 端点存活但 FSTDD-AIBU-01 token 未重铸，已在
> `.fstdd/share-audit.yaml` 留痕待重投，改落本节点）
