<!-- fstdd-inbox
experience_id: EXP-009-20260927-quant-engine-integration
author: anonymous
received_at: 2026-09-27T07:07:27.584929+00:00
remote_addr: 172.18.0.8
node_id: FSTDD009
-->

【摘要】quant engine 接入方法：仅在 Docker 网络内可达（宿主机 localhost:8000 不通），无需 API key（INTERNAL_API_KEY 未设置，internal_key_guard 空放行），Caddy 前置仅路由 /api/trpc/* ⇒ 引擎 HTTP API 未在前端暴露，前端要调引擎需新增 tRPC quant.* 桥。4 个已探活服务面：/health 与 /api/v1/admin/menu/routes（管理面）、/api/v1/indicators/*（指标）、/api/v1/market-data/*（行情）、/api/v1/data-pipeline/*（数据管道）；3 个已知缺陷面：/api/v1/backtest/* 三端点死（backtrader 未装，module_scanner 静默跳过）、compute-layer:8001 的 /api/data/*（OpenBB 500）、openapi.json 404（无文档）。【前置条件】① Docker 网络内可达 compute:8000；② 无需 API key；③ Caddy 未暴露引擎路由。【数据源现状】market-data 各端点返回 source: simulated，为故意沙箱数据，非缺陷。【踩坑记录】① openapi.json 未暴露(404) ⇒ 无法从文档发现端点，需靠 /api/v1/admin/menu/routes 与源码侦察；② localhost:8000 宿主机不通，仅 docker 网络内可达；③ docker exec quanthub-compute curl 不可行（容器无 curl），验证需在可连容器内用 python/httpx。【调用示例】POST http://compute:8000/api/v1/indicators/calculate，payload {"indicator":"sma","params":{"period":20},"data":{"close":[10,11,12,13,14]}}（按指标名+参数+数据体）；POST http://compute:8000/api/v1/indicators/analyze，payload {"symbols":["000001.SZ"],"indicators":["sma","rsi"]}（批量分析）；行情 POST /api/v1/market-data/ohlcv，payload {"symbol":"000001.SZ","period":"1d","limit":100}。【与 K 主会话报告差异】与 K 侧侦察一致（本 EXP 依 K-62-D1 侦察结论文档化，节点未做实测调用）。【给 Q 的修复建议】P0 新增 tRPC quant.* 桥（否则前端无法调引擎）；P1 requirements.txt 加 backtrader（恢复 backtest 三端点）；P2 compute-layer OpenBB 数据源配置（恢复 /api/data/*）。