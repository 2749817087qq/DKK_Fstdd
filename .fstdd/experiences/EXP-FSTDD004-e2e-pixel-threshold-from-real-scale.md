<!-- fstdd-inbox
experience_id: EXP-FSTDD004-e2e-pixel-threshold-from-real-scale
author: anonymous
received_at: 2026-10-09T16:44:40.936471+00:00
remote_addr: 172.18.0.8
node_id: FSTDD004
-->

---
exported_at: 2026-10-10
sanitized: true
lifecycle_state: deposited
---
---
experience_id: FSTDD004-e2e-pixel-threshold-from-real-scale
category: acceptance_judgment_defect
severity: medium
date: '2026-10-03'
node: FSTDD004
title: ① 断言「中心距 >= 6px」实测 5.25px 判红，但产品其实没问题
occurrences: 1
pattern: E2E 像素级断言里把阈值写成「相邻柱中心距 >= 6px」，实测 5.25px 判红。根因是阈值来自印象而非被测对象的真实几何：ECharts
  外推柱的水平偏移是 fcOffPx = (barW + fcW) / 2 + 1，在窄柱宽下天然只有 5px 上下，产品行为完全正确，判据本身是错的。危险之处有两层：一是把正确实现判红会诱导去改产品代码以迎合错误断言；二是这类假红会消耗排查时间，并让人对整组像素断言失去信任。
root_cause: 判据阈值未从被测数据的实际量级推导，而是用「看起来合理」的整数；且断言锁定的是具体像素值而非本质不变量。正确做法是先探测真实间距/量级（用
  convertToPixel 从 series 反推），再用「物理下限 + 本质不变量」构造判据。
detection_trigger: ① 断言「中心距 >= 6px」实测 5.25px 判红，但产品其实没问题；② 阈值来自「印象/常见值」而非从被测数据反推；③
  改动渲染逻辑后大批像素阈值断言集体变红；④ 无法说清阈值对应的真实量级来源。
fix_template: "// ✅ 先从series 反推真实量级，再定阈值\nconst m = await page.evaluate(() => {\n\
  \  const ch = echarts.getInstanceByDom(document.getElementById('fundChart'));\n\
  \  const s = ch.getOption().series.find(x => x.name === '场内价格');\n  const pts =\
  \ s.data.map(d => ch.convertToPixel({ seriesIndex: 0 }, d));\n  const gaps = pts.slice(1).map((p,\
  \ i) => p[0] - pts[i][0]);\n  return { minGap: Math.min(...gaps), plotTop: 34.0,\
  \ plotBottom: 366.0 };\n});\nconsole.log('[scale]', JSON.stringify(m));   // minGap=16.07（月宽），据此判断\
  \ 6px 是否合理\n\n// ✅ 判本质不变量，不判拍出来的数\nok('相邻柱不重叠', m.minGap >= 2);                \
  \ // 2px 是「真的压上了」的物理下限\nok('外推柱右偏于最后一根',fcOffPx >= 3);          // 3px 覆盖 (barW+fcW)/2+1\
  \ 的最小构造\nok('无柱触顶', topMost > m.plotTop + 1);          // 留白存在即可，不锁死具体像素\n\n// ❌\
  \ 阈值凭印象：ok('最近中心距 >= 6px', gap >= 6)  // 实测 5.25 ⇒ 假红"
tags:
- e2e
- threshold
- pixel-assertion
- false-red
- convertToPixel
- acceptance-judgment
language: javascript


## 现场

E5 断言写成 `ok("最近中心距 >= 6px", gap >= 6)`，实测 5.25px 判红。

6px 是凭印象写的。真实几何是 `fcOffPx = (barW + fcW) / 2 + 1`，在窄柱宽下就是 5px 上下——**产品行为完全正确，判据本身是错的**。

改法：先用 `convertToPixel` 从 series 反推真实量级（实测黄柱最小间距 16.07px = 月宽），再把判据换成本质不变量：「不重叠（≥2px，物理下限）」「外推柱右偏（≥3px，覆盖最小构造）」「无柱触顶」。

## 处置

阈值全部改为本质不变量（不重叠 ≥2px / 右偏 ≥3px / 无柱触顶），不再锁死具体像素。

## 教训

1. 判据阈值只能来自被测数据的真实量级。「看起来合理」的整数一旦写进断言，就会在正确实现上判红，诱导人去改对的产品。

## 改善方法

- 根因：判据阈值未从被测数据的实际量级推导，而是用「看起来合理」的整数；且断言锁定的是具体像素值而非本质不变量。正确做法是先探测真实间距/量级（用 convertToPixel 从 series 反推），再用「物理下限 + 本质不变量」构造判据。
- 检测信号：① 断言「中心距 >= 6px」实测 5.25px 判红，但产品其实没问题；② 阈值来自「印象/常见值」而非从被测数据反推；③ 改动渲染逻辑后大批像素阈值断言集体变红；④ 无法说清阈值对应的真实量级来源。
- 修复模板：见 frontmatter `fix_template`。

> 迁移自工作区经验库 EXP-2026-0085 / change 2026-10-02-fcbar-event-aggregate
> （inbox 端点 HTTP 401 未送达 —— 端点存活但 FSTDD-AIBU-01 token 未重铸，已在
> `.fstdd/share-audit.yaml` 留痕待重投，改落本节点）
