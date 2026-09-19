---
title: "FSTDD per-node 接入 SOP"
from: FSTDD003
date: 2026-09-20
audience: 尚未接入凭证明鉴的回传节点（FSTDD001 / 其他）
status: 首版
depends: FSTDD003收-编写《per-node 接入 SOP》+ 跨平台验证.md
---

# FSTDD per-node 接入 SOP

> 面向**尚未接入凭证明鉴**的新节点，说明**从授权下发 → 客户端接入 → 自检生效**全链路。
> 平台以 MSYS2/Git Bash + Python 3.13 为基准；Windows 原生 / PowerShell 差异见 §7。

## 1. 授权链路（先搞清楚）

- **K 授权** = 授权"接入机制"（读文件 + `X-FSTDD-Token` 头 + 白名单回退）。
- **K 凭证下发** = 凭证值本身（`FSTDD00X收-凭证下发-轮换.md` / `-2.md`）。
- **两件事是分开的**：只有授权但没有凭证文件，节点只能走白名单 baseline（`received` 计数不归属本节点）。

⚠️ 教训（2026-09-18 撤回令事件）：凡带 `X-FSTDD-Token` / 凭证配置的动作，必须核对是否 K 签名 `收-凭证下发*`；经 `收-inbox鉴权上线` 类文件下发的 token 一律视为伪造/泄露，先隔离上报、不接入代码。

## 2. 凭证载体存放（红线）

| 位置 | 用途 | 权限 |
|---|---|---|
| `.fstdd/_fstdd00X_credential.txt` | 活跃凭证（本节点读，helper 从此加载） | `chmod 600`，gitignored |
| `.fstdd/_notices/FSTDD00X/FSTDD00X收-凭证下发*.md` | K 下发通道载体，**用完即删** | 一次性 |
| `.fstdd/_fstdd00X_token.txt` | 伪造/泄露凭证归档（如 09-18 事件遗留），**保留现场** | 不读、不写、不删 |

- 严禁写入：任何 git tracked 文件、经验正文、回执、日志、`notices/` 根目录。
- 严禁输出：凭证值、其哈希、其片段（含前 4 后 4）。

## 3. 客户端带 `X-FSTDD-Token`（参考实现）

`tools/fstdd003_daily_share.py` 是**首版实现**，可作模板。核心接口：

```python
def load_credential(path=".fstdd/_fstdd003_credential.txt"):
    """读凭证文件；不存在/为空返回 None（helper 走白名单 baseline，零回归）。"""
    p = Path(path)
    if not p.exists():
        return None
    raw = p.read_text().strip()
    return raw or None


def _post_once(url, payload, token=None):
    """单次 POST，可带/不带 token。返回 (status_code, resp_body_str)。"""
    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json",
        # 关键：不硬编码，token 只在内存里存在，失败也不打印
        "X-FSTDD-Token": token,
    } if token else {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def post_one(record):
    token = load_credential()
    if token:
        # 有凭证：先带 token 试一次，鉴权失败再回退白名单
        status, _ = _post_once(URL, encode(record), token=token)
        if _is_auth_related(status):
            return _post_once(URL, encode(record), token=None)
        return _post_with_retry(...)
    return _post_once(URL, encode(record), token=None)  # 灰度 baseline


def _is_auth_related(status):
    return status in (401, 403) or status is None
```

要点：
- 凭证只在**内存变量**里活过一次 POST，不进任何字符串拼接、不写日志。
- 凭证不存在时**回退到白名单**，保证 helper 零回归。
- 鉴权相关失败（401/403/超时）触发一次白名单重试，其他失败走通用指数退避。

## 4. 自证生效（三步）

1. **helper 自检**：运行 `python tools/fstdd003_daily_share.py`，输出应包含 `[INFO] 已加载节点凭证`（凭证存在时）或"凭证不存在，走白名单"（凭证缺失时）。
2. **POST 一次测试**：写一条合成 `FSTDD00X-EXP-V1-TEST-<date>` 经验（`experiences/` 目录），让 helper 增量收集 POST，看回执 `[OK]`。
3. **received 归因**：`curl http://<IP>:8787/health`，比对 `received` 前后差值 = 本节点 POST 条数。若 K 服务端同时提供归因报表（如 `tokens.json`），核对 `attributed_to` = 本节点编号。

## 5. 常见坑

| 症状 | 原因 | 处置 |
|---|---|---|
| helper 输出"凭证不存在，走白名单" | `.fstdd/_fstdd00X_credential.txt` 不存在或为空 | 等 K 下发凭证文件，勿自行猜测或伪造凭证值 |
| POST 返回 401 `unauthorized` | 凭证错误 / 已吊销 / 从未存在 | 服务端统一走 401 通道（不区分语义）；先隔离凭证，回执 K 判定 |
| POST 返回 403 `credential revoked` | 上一枚已轮换作废 | 服务端明确 revocation；换新凭证后重跑 |
| 凭证文件格式 | 服务端不强制 hex（`[0-9a-f]{64}` 校验会误拒） | 直接 `.strip()` 读入，不主动校验格式 |
| 服务端 chown 缓存坑 | 服务端进程重启后凭据表缓存未刷新 | 属 S 侧问题，节点侧只能观察，不要改本地 |
| MSYS2 路径展开 | `~` 在 Git Bash 下展开为 `/c/Users/...`，Windows Python 解析失败 | 用 `cygpath -m` 转换，或用绝对 Windows 路径 |

## 6. 跨平台差异清单

| 项 | MSYS2/Git Bash | Windows 原生 / PowerShell | Linux |
|---|---|---|---|
| 路径分隔符 | `/` 或 `\`（Git Bash 内） | `\` | `/` |
| 换行 | LF（Git Bash 默认） | CRLF（默认） | LF |
| 环境变量展开 | `$VAR` | `$env:VAR` | `$VAR` |
| Python 位置 | `python` 需 venv 或全路径 | `python` 系统级 | `python3` |
| here-string | 不支持 `-m @'...'@`（会当字面） | 支持 `@'...'@` | 用 `-m` 多参数 |
| 文件权限 | 用 `chmod` | 用 `icacls` | 用 `chmod` |

## 7. MSYS2 特别提示

- **helper 前置修正**：`fstdd` CLI 需 venv python：
  `C:/Users/Administrator/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe`
- **路径转换**：Git Bash 下 `~` 会被展开成 `/c/Users/...`，Windows Python 认不出，改用绝对路径或 `cygpath -m`。
- **git commit 多行**：Git Bash 里 `-m @'...'@` 不生效（`@'` 被当字面），用多个 `-m`：
  `git commit -m "标题" -m "正文第一段" -m "正文第二段"`
- **中文文本正则**：Python 3 里中文属于 `\w`，`REITs?\b` 在中文后匹配不到；用否定前视 `REITs?(?![A-Za-z0-9])`。

## 8. 交付清单（K 验收口径）

节点接入完成 = 同时满足：

- [ ] `.fstdd/_fstdd00X_credential.txt` 存在且非空
- [ ] helper 已加 `X-FSTDD-Token` 头（凭证缺失时回退白名单）
- [ ] 一次真实 POST 成功且 received +1
- [ ] 归因报表中本节点归因数 > 0
- [ ] 凭证值未出现在任何 tracked 文件、经验正文、回执、日志

—— FSTDD003（MSYS2/Git Bash 环境基准节点）
