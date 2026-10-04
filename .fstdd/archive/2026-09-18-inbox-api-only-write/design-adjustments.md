# design-adjustments.md — 设计偏离记录

> change: `2026-09-18-inbox-api-only-write`
> 约束依据：AGENTS.md 铁律 2 —— 绝不静默修改设计，偏离必须记录。

## DA-01 ｜ 实现口径：远端字节回灌 → 契约冻结 + 仓库自主实现 + 部署收敛

| 字段 | 内容 |
|------|------|
| 发现位置 | Phase 2（design.md 决策 4） |
| 变更 | 原设计「把远端已部署的 `inbox_server.py` 字节回灌仓库」改为「按部署版**行为契约**在仓库侧自主实现，再由部署动作收敛字节」 |
| 触发原因 | 本机与生产 `43.134.236.80` 不互通，无法回灌远端字节；且字节回灌会把仓库绑死在未审计的远端副本上 |
| 影响 | 接口/语义不变。若 K 回灌的部署版与本实现行为不一致，以 SC-006/007/008 的行为断言为准（行为等价优先于字节一致） |

## DA-02 ｜ `do_POST` 顺序：先消费请求体，再做鉴权

| 字段 | 内容 |
|------|------|
| 发现位置 | Phase 3 切片 1（RED 用例 `test_d2b_allow_ip_declared_forms[10.0.0.1-False]`） |
| 变更 | `do_POST` 鉴权从「读 body 之前」调整到「读 body 之后」（顺序：Content-Length 校验 → `rfile.read(length)` → 鉴权 → JSON 解析） |
| 触发原因 | 服务端在未消费请求体时提前响应 401 并关闭连接，客户端仍有未读 body → `ConnectionAbortedError: [WinError 10053]`（TCP RST）。属结构性缺陷，非测试抖动 |
| 影响 | 401/200 等对外行为与状态码完全不变；仅消除连接层抖动 |

## DA-03 ｜ 凭证比较由 `str` 改为 `bytes`（防非 ASCII 头 TypeError）

| 字段 | 内容 |
|------|------|
| 发现位置 | Phase 3 质量验证 C1 代码评审代理 |
| 变更 | `_authorized()` 中 `secrets.compare_digest(supplied, token)` 改为 `compare_digest(supplied.encode("utf-8","surrogateescape"), token.encode("utf-8"))` |
| 触发原因 | HTTP 头以 latin-1 解码，攻击者可寄非 ASCII 值（如 `X-FSTDD-Token: <0xE9>`）；`compare_digest` 对含非 ASCII 的 `str` 会抛 `TypeError`，导致未捕获异常与栈刷屏 |
| 验证 | 新增回归用例 `test_d1d_non_ascii_token_header_rejected_gracefully`（RED→GREEN） |
| 影响 | 接口/语义不变：正确 token 仍放行，错误/畸形凭证一律 401 且不落盘 |

## DA-04 ｜ 静态守护断言口径放宽（脚本引号写法）

| 字段 | 内容 |
|------|------|
| 发现位置 | Phase 3 切片 2（`test_e2`） |
| 变更 | env 存在性校验断言由精确匹配 `'[ -f "$ENV_FILE" ]'` 放宽为子串 `"[ -f " in text and "ENV_FILE" in text` |
| 触发原因 | 脚本实际写法为 `[ -f '$ENV_FILE' ]`（单引号让**远端** shell 展开路径），与双引号字面量不匹配 |
| 影响 | 仅测试匹配口径；不断言弱化到失去意义（仍要求存在性校验 + `exit 1` + 处置指导三要素） |

## 汇总

| 编号 | 类型 | 位置 | 严重度 | 是否需用户裁定 |
|------|------|------|--------|---------------|
| DA-01 | 实现口径 | design.md / 部署 | 低 | 否（Phase 2 已登记） |
| DA-02 | 实现顺序 | tools/inbox_server.py | 中（连接层缺陷） | 否 |
| DA-03 | 健壮性 | tools/inbox_server.py | 中（安全边界） | 否 |
| DA-04 | 测试口径 | upstream/tests/test_inbox_endpoint.py | 低 | 否 |

**未发生改变对外接口/行为语义的设计偏离**：DA-02/DA-03 均为连接层/健壮性修复，SC-006/007/008/009 的对外行为不变；DA-04 仅测试匹配口径。B 层（外部挂账）不涉及本文件。