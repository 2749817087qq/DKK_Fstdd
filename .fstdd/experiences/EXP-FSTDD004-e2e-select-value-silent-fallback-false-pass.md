<!-- fstdd-inbox
experience_id: EXP-FSTDD004-e2e-select-value-silent-fallback-false-pass
author: anonymous
received_at: 2026-10-09T16:44:40.942381+00:00
remote_addr: 172.18.0.8
node_id: FSTDD004
-->

---
exported_at: 2026-10-10
sanitized: true
lifecycle_state: deposited
---
---
experience_id: FSTDD004-e2e-select-value-silent-fallback-false-pass
category: test_harness_pitfall
severity: high
date: '2026-10-03'
node: FSTDD004
title: ① 多标的 E2E 输出里两个不同代码的指标数值完全一致（柱数/事件数/最大柱高一字不差）
occurrences: 1
pattern: E2E 里写死一串标的代码去测「多标的差异」，用 sel.value = code 切换。若某个 code 不在下拉<select> 里，赋值静默失败、页面不报错，而切换函数里常带
  `if (!f) sel.selectedIndex = 1` 之类的兜底分支 ⇒ 实际反复测的是同一只标的，但所有断言全绿。本次实测：脚本写死 ['180202','508077','508095']
  测三只，输出里 180202 与 508077 的柱数/事件数/最大柱高完全相同，review时若只看「全绿」就会直接放过。属于最危险的一类假通过——不产生任何红灯。
root_cause: 把「设置 select.value 成功」当成无声的既成事实，且切换辅助函数里存在「找不到就回落到默认项」的防御分支；两层叠加使标的替换彻底失效，而断言只校验渲染结果不校验「被测对象是谁」，于是同一份数据被反复验证
  N 遍并全绿。
detection_trigger: ① 多标的 E2E 输出里两个不同代码的指标数值完全一致（柱数/事件数/最大柱高一字不差）；② 用例名/日志写着「测 3 只基金」但探针实测
  option 数量远小于 3；③ 切换基金后未校验 select.value 就继续断言；④ select.closest('form') 有兜底分支（如 selectedIndex
  = 1）时尤甚。
fix_template: "// ✅ pick找不到就抛错，绝不静默兜底\nfunction pick(code) {\n  const sel = document.getElementById('fundSel');\n\
  \  const opt = Array.from(sel.options).find(o => o.value === code);\n  if (!opt)\
  \ throw new Error('基金 ' + code + ' 不在 fundSel 下拉里（下拉共 ' + sel.options.length + '\
  \ 项）');\n  sel.value = code;\n  sel.dispatchEvent(new Event('change', { bubble<PATH>
  \ true }));\n  if (sel.value !== code) throw new Error('切换未生效：期望 ' + code + ' 实际\
  \ ' + sel.value);\n}\n\n// ✅ 基金代码从下拉实取，绝不写死\nconst FUNDS = await page.evaluate(()\
  \ =>\n  Array.from(document.getElementById('fundSel').options).map(o => o.value).slice(0,\
  \ 3));\n\n// ❌ 静默回落：X 不在下拉里 → 不报错 → selectedIndex=1 兜底 → 实际测了同一只\n// el.value =\
  \ ['180202','508077','508095'].filter(c => (f = find(c)))[0] || (el.selectedIndex\
  \ = 1);\n\n// ✅ 补一条「覆盖度」断言，让假通过必红\nok('E7 实际覆盖 >= 3 只基金（防静默回落）', new Set(covered).size\
  \ >= 3);"
tags:
- e2e
- playwright
- false-pass
- select-value
- silent-fallback
- coverage-assertion
- test_harness_pitfall
language: javascript


## 现场

E2E 里写死 `["180202","508077","508095"]` 测三只基金的多标的差异，切换辅助函数写成：

```js
el.value = ['180202','508077','508095'].filter(c => (f = find(c)))[0]
         || (el.selectedIndex = 1);      // ← 静默兜底
```

`508077`/`508095` 根本不在 `fundSel` 下拉里（`find` 返回 undefined ⇒ 被 filter 剔除），于是**每次都回落到 `selectedIndex = 1`**，实际反复测的是同一只 180202。

输出里 180202 与「508077」的柱数 / 事件数 / 最大柱高**一字不差**（13 柱 / 12 事件 / 0.5943），但 66 条断言全绿。这是最危险的一类假通过：不产生任何红灯，review 时只看「全绿」就直接放过。

## 处置

`pick(code)` 找不到就 `throw`，切换后再校验 `sel.value === code`；基金代码从下拉实取；补一条「E7 实际覆盖 ≥ 3 只基金」的覆盖度断言。修正后三只真不同：180202(13柱/5合并) / 180203(4柱/3合并) / 180306(2柱/0合并)。

## 教训

1. E2E 判据必须同时回答两个问题：**「测的东西对不对」**和**「被测对象是不是我以为的那个」**。任何静默兜底分支（`|| default`、`selectedIndex = 0`、`if not found: skip`）都是假通过制造机，必须改成 throw，并补一条覆盖度断言兜住。

## 改善方法

- 根因：把「设置 select.value 成功」当成无声的既成事实，且切换辅助函数里存在「找不到就回落到默认项」的防御分支；两层叠加使标的替换彻底失效，而断言只校验渲染结果不校验「被测对象是谁」，于是同一份数据被反复验证 N 遍并全绿。
- 检测信号：① 多标的 E2E 输出里两个不同代码的指标数值完全一致（柱数/事件数/最大柱高一字不差）；② 用例名/日志写着「测 3 只基金」但探针实测 option 数量远小于 3；③ 切换基金后未校验 select.value 就继续断言；④ select.closest('form') 有兜底分支（如 selectedIndex = 1）时尤甚。
- 修复模板：见 frontmatter `fix_template`。

> 迁移自工作区经验库 EXP-2026-0082 / change 2026-10-02-fcbar-event-aggregate
> （inbox 端点 HTTP 401 未送达 —— 端点存活但 FSTDD-AIBU-01 token 未重铸，已在
> `.fstdd/share-audit.yaml` 留痕待重投，改落本节点）
