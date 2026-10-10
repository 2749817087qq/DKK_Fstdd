<!-- fstdd-inbox
experience_id: EXP-FSTDD004-echarts-tooltip-dispatchaction-over-mouse
author: anonymous
received_at: 2026-10-09T16:44:40.946834+00:00
remote_addr: 172.18.0.8
node_id: FSTDD004
-->

---
exported_at: 2026-10-10
sanitized: true
lifecycle_state: deposited
---
---
experience_id: FSTDD004-echarts-tooltip-dispatchaction-over-mouse
category: test_harness_pitfall
severity: medium
date: '2026-10-03'
node: FSTDD004
title: ① page.mouse.move 到容器中心后 tooltip 为空但鼠标坐标明显在图外（页面未滚动）
occurrences: 1
pattern: E2E 验收图表 tooltip 时用 page.mouse.move(x, y) 模拟悬停，两次都抓空：一是图表容器常在首屏之外，未 scrollIntoView
  时 boundingBox 换算出的坐标根本不在可视区，鼠标事件落在页面别处；二是自定义系列（custom + renderItem）的命中区由 renderItem
  自行返回 rect，与视觉柱体不一定重合，按柱顶中心算坐标可能落在命中区外。表现为 tooltip 断言偶发红、截图只有页面顶部、误判为「tooltip 功能没实现」。
root_cause: 把 tooltip 验证建立在「鼠标事件坐标」这一间接层上，而该层同时受布局滚动位置与自定义系列命中区两个不稳定因素影响；而 dispatchAction({type:'showTip'})
  是ECharts 官方的确定性触发路径，不依赖命中区几何。
detection_trigger: ① page.mouse.move 到容器中心后 tooltip 为空但鼠标坐标明显在图外（页面未滚动）；② tooltip
  断言用 mouse 悬停偶发抓空，重试就好；③ 自定义系列（custom/renderItem）的柱子鼠标命中区与视觉柱体不对齐；④ 滚动到图表后偶发抓到相邻
  series 的 tooltip。
fix_template: "// ✅ 先把图表滚进视口，再取真实像素坐标\nawait page.evaluate(() => document.getElementById('fundChart')\n\
  \  .scrollIntoView({ block: 'center' }));\nawait page.waitForTimeout(300);\n\n//\
  \ ✅ 用官方 action 触发 tooltip，绕开 renderItem 命中区\nconst [px, py] = await page.evaluate(([x,\
  \ y]) => {\n  const ch = echarts.getInstanceByDom(document.getElementById('fundChart'));\n\
  \  const si = ch.getOption().series.findIndex(s => s.name === '预计分红');\n  return\
  \ ch.convertToPixel({ seriesIndex: si }, [x, y]);\n}, [tsOfDay, dpuValue]);\nawait\
  \ page.evaluate(([si, di]) => echarts.getInstanceByDom(document.getElementById('fundChart'))\n\
  \  .dispatchAction({ type: 'showTip', seriesIndex: si, dataIndex: di }), [si, di]);\n\
  \n// ❌ 容器未在视口内时鼠标坐标全错\n// await page.mouse.move(box.x + box.width / 2, box.y + 20);\n\
  \n// ✅ 断言读 DOM 原文并打印，避免只判 substring 漏掉空串\nconst tip = await page.$eval('#chartTip',\
  \ el => el.innerText.trim());\nconsole.log('[tooltip]', JSON.stringify(tip));\n\
  ok('tooltip 含合并期数', /合并\\s*\\d+\\s*个报告期/.test(tip));"
tags:
- echarts
- playwright
- tooltip
- dispatchAction
- scrollIntoView
- custom-series
- e2e
language: javascript


## 现场

tooltip 验收最初用 `page.mouse.move(box.x + w/2, box.y + 20)` 悬停，两次都抓到空串，截图只有日历区。

两个原因叠加：① 图表容器 `#fundChart` 在首屏之外，未 `scrollIntoView` 时`boundingBox` 换算出的坐标根本不在可视区，鼠标事件落在页面别处；② 预计分红柱是 custom 系列（`renderItem` 自绘），命中区由 renderItem 返回的 rect 决定，按柱顶中心算坐标可能落在命中区外。

## 处置

先 `scrollIntoView({block:"center"})`，再 `dispatchAction({type:"showTip", seriesIndex, dataIndex})`；tooltip 断言读 DOM 原文并 `console.log` 打印，不只判 substring。

## 教训

1. 能用官方 action触发的东西就别用鼠标坐标模拟。间接层越多（滚动位置、命中区几何、事件冒泡），验收脚本越脆弱。

## 改善方法

- 根因：把 tooltip 验证建立在「鼠标事件坐标」这一间接层上，而该层同时受布局滚动位置与自定义系列命中区两个不稳定因素影响；而 dispatchAction({type:'showTip'}) 是ECharts 官方的确定性触发路径，不依赖命中区几何。
- 检测信号：① page.mouse.move 到容器中心后 tooltip 为空但鼠标坐标明显在图外（页面未滚动）；② tooltip 断言用 mouse 悬停偶发抓空，重试就好；③ 自定义系列（custom/renderItem）的柱子鼠标命中区与视觉柱体不对齐；④ 滚动到图表后偶发抓到相邻 series 的 tooltip。
- 修复模板：见 frontmatter `fix_template`。

> 迁移自工作区经验库 EXP-2026-0083 / change 2026-10-02-fcbar-event-aggregate
> （inbox 端点 HTTP 401 未送达 —— 端点存活但 FSTDD-AIBU-01 token 未重铸，已在
> `.fstdd/share-audit.yaml` 留痕待重投，改落本节点）
