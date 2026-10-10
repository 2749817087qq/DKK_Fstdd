<!-- fstdd-inbox
experience_id: EXP-FSTDD004-echarts-minified-internal-api-unusable
author: anonymous
received_at: 2026-10-09T16:44:40.945939+00:00
remote_addr: 172.18.0.8
node_id: FSTDD004
-->

---
exported_at: 2026-10-10
sanitized: true
lifecycle_state: deposited
---
---
experience_id: FSTDD004-echarts-minified-internal-api-unusable
category: tool_misuse
severity: medium
date: '2026-10-03'
node: FSTDD004
title: ① 页面里ECharts 明明加载成功、控制台无 SyntaxError，但 evaluate 报 is not a function 且方法名带单字母
occurrences: 1
pattern: E2E 验收生产页面时，evaluate 里调用 ECharts 内部 API（ch.getModel().getSeriesByName(name).getData()）直接报
  "getData is not a function"。根因是生产页面加载的是 echarts.min.js 压缩版：内部类名被 minify 成单字母 e，SeriesModel
  上的 getData 方法在压缩产物中并不存在（源码里存在 ≠ 产物里可访问）；同源第二个坑是 getSeriesByName(name) 在同名 series
  多实例时返回数组而非对象，于是即便方法名侥幸存在也会在 .getData 处抛 is not a function。后果是验收脚本整体崩、截图只截到首屏、真因被误判为「页面功能缺陷」。
root_cause: 把 ECharts 源码级内部 API 当成公开契约使用。压缩产物不保证内部方法名与结构，且不承诺跨版本兼容；getSeriesByName
  的返回形态还随series 是否同名而变。正确做法是只用文档化的 getOption() / convertToPixel() / dispatchAction()。
detection_trigger: ① 页面里ECharts 明明加载成功、控制台无 SyntaxError，但 evaluate 报 is not a function
  且方法名带单字母；② getSeriesByName(name) 返回数组却按对象用（.getData is not a function）；③ 自测环境能跑通的断言在生产页面上炸；④
  源码搜 getData( 在 echarts.min.js 里能找到、调用却undefined。
fix_template: '// ✅ 一律走官方公开 API，不碰内部 model

  const opt = ch.getOption();               // 取 series 数组（普通对象）

  const si = opt.series.findIndex(s => s.name === ''预计分红'');

  const [px, py] = ch.convertToPixel({ seriesIndex: si }, [dataX, dataY]);


  // ❌ 生产是压缩版，内部类名 minify 成 e，SeriesModel.getData 不存在

  const m = ch.getModel().getSeriesByName(''预计分红'');

  if (Array.isArray(m)) console.warn(''getSeriesByName 返回数组，须取 [0]'');


  // ✅ 若必须探测内部 API，先判存在再调

  const probe = (obj, name) => typeof obj?.[name] === ''function'';

  if (!probe(ch, ''convertToPixel'')) throw new Error(''echarts 实例未就绪'');

  // ❌ ch.getModel().getSeriesByName(''x'').getData()  //生产直接 TypeError'
tags:
- echarts
- e2e
- minified
- api-misuse
- convertToPixel
- getOption
- test_harness_pitfall
language: javascript


## 现场

权益日历预计分红柱改按分红事件聚合后，E2E 探针里写了

```js
const m = ch.getModel().getSeriesByName('预计分红');
const d = m.getData();          // ← TypeError: m.getData is not a function
```

生产页面 `/info/equity-calendar.html` 加载的是压缩版 echarts，内部类名被minify 成单字母 `e`，`SeriesModel.getData` 在产物中不存在。第二个坑同时出现：`getSeriesByName` 在同名 series 多实例时返回的是**数组**，所以即便方法名侥幸存在也会在 `.getData` 处抛同一个错。

后果不止是探针崩：截图只截到首屏，日志里最后一句是 TypeError，很容易被误判成「页面功能缺陷」而回头去改产品代码。

## 处置

改走官方 `getOption()` + `convertToPixel({seriesIndex}, [x,y])`；探测内部 API 前先判 `typeof obj[name] === "function"`，不判就调。

## 教训

1. 对第三方库只用文档化的公开 API。源码里存在 ≠ 压缩产物里可访问
2. 这条同样适用于任何经过打包/压缩的运行时依赖。

## 改善方法

- 根因：把 ECharts 源码级内部 API 当成公开契约使用。压缩产物不保证内部方法名与结构，且不承诺跨版本兼容；getSeriesByName 的返回形态还随series 是否同名而变。正确做法是只用文档化的 getOption() / convertToPixel() / dispatchAction()。
- 检测信号：① 页面里ECharts 明明加载成功、控制台无 SyntaxError，但 evaluate 报 is not a function 且方法名带单字母；② getSeriesByName(name) 返回数组却按对象用（.getData is not a function）；③ 自测环境能跑通的断言在生产页面上炸；④ 源码搜 getData( 在 echarts.min.js 里能找到、调用却undefined。
- 修复模板：见 frontmatter `fix_template`。

> 迁移自工作区经验库 EXP-2026-0081 / change 2026-10-02-fcbar-event-aggregate
> （inbox 端点 HTTP 401 未送达 —— 端点存活但 FSTDD-AIBU-01 token 未重铸，已在
> `.fstdd/share-audit.yaml` 留痕待重投，改落本节点）
