---
name: mitmproxy-host-filter
description: "mitmproxy 抓包插件的两个高频坑。① 只解密指定域名、其余走裸 TCP 隧道（整机系统代理场景的性能优化）：`--ignore-hosts` 配否定前瞻 `^(?!.*域名)` 会把目标域名自己一起放走，必须改用正向白名单 `--allow-hosts`。② 多值响应头（Set-Cookie）必须用 `get_all()`，`.get()` 只返回第一条会静默丢数据。当用户抱怨「一开抓包电脑就变慢」、写了 ignore-hosts 后抓不到目标流量、或插件抓不到 cookie 时使用。"
agent_created: true
version: 1.1.0
license: unknown
---

# mitmproxy：只解密指定域名（正向白名单）

## 何时用

- 抓包脚本把**整机系统代理**指向 mitmproxy，导致所有 HTTPS 都被解密 → 电脑明显变慢
- 想「只解密目标域名，其余走裸 TCP 隧道」来省 CPU
- 写了 `--ignore-hosts` 之后**目标域名的流量反而抓不到了**

## 🔴 核心结论（先看这条）

**`--ignore-hosts` + 否定前瞻 `^(?!.*(?:target\.com))` 不可用 —— 它会把 target.com 自己一起放走。**

必须改用**正向白名单** `--allow-hosts 'target\.com|other\.com'`。

实测对照（同一份配置，请求 `mp.weixin.qq.com` + `www.baidu.com`）：

| 方案 | 目标域名被解密 | 无关域名被解密 |
|---|---|---|
| `--allow-hosts 'weixin\.qq\.com\|...'` | ✅ | ❌（裸隧道） |
| `--ignore-hosts '^(?!.*(?:weixin\.qq\.com\|...))'` | ❌ **抓不到** | ❌ |

## 根因

`mitmproxy/addons/next_layer.py` 的 `NextLayer._ignore_connection()` 会构造**多个**
hostname 形式，再对它们做 `any()`：

```python
hostnames: list[str] = []
if context.server.peername:                    # ← 解析后的 IP
    host, port, *_ = context.server.peername
    hostnames.append(f"{host}:{port}")
if context.server.address:                     # ← 域名
    host, port, *_ = context.server.address
    hostnames.append(f"{host}:{port}")
    # 还会追加 Host 头、ClientHello 的 SNI
...
if ctx.options.ignore_hosts:
    ignored = any(
        re.search(rex, host, re.IGNORECASE)
        for host in hostnames
        for rex in ctx.options.ignore_hosts
    )
```

否定前瞻拿 **IP 那一项**去匹配必然命中（IP 字符串里当然不含域名）→ `any()` 为真 →
整个连接被 ignore → 裸 TCP 隧道 → 插件收不到任何 hook。

而 `--allow-hosts` 是 `any()` 的**正向**判定：只要域名/SNI 那一项命中就放行，
不会被 IP 那一项拖累。

## ⚠ 别想着「再排除掉 IP 形式」去补救

IPv4 是点分 `1.2.3.4`、IPv6 是冒号分 `2408:80f1:21:c120::9e`、还可能带方括号 `[::1]`，
正则追不完。实测：只排除 IPv4 点分形式的补丁**照样失败**（那次的 IP 是 IPv6）。

## 正确写法

```python
TARGET_HOSTS = (r"weixin\.qq\.com", r"weixin\.com", r"wechat\.com")
ALLOW_HOSTS_RE = "|".join(TARGET_HOSTS)      # 正向，不要否定前瞻

mitm_args = [str(MITMDUMP), "-p", str(port), "-s", str(PLUGIN),
             "--set", "flow_detail=0",
             "--set", "stream_large_bodies=1m",   # 大响应体不缓进内存
             "--allow-hosts", ALLOW_HOSTS_RE]
```

同时保留一个 `--intercept-all` 逃生门：抓不到时先全量解密确认是不是名单漏了域名。

## 验证方法

拿一个必然命中的请求 + 一个必然不命中的请求，各发一次，看插件有没有打印：

```python
proxies = {"http": "http://127.0.0.1:PORT", "https": "http://127.0.0.1:PORT"}
requests.get("https://target.com/",  proxies=proxies, verify=False)   # 期望：插件有日志
requests.get("https://www.baidu.com/", proxies=proxies, verify=False) # 期望：插件无日志
```

⚠ 测试前先确认目标端口没有**别的** mitmdump 实例在占（否则请求打给了旧配置的实例，
结论全错）。`Get-NetTCPConnection -State Listen | Where LocalPort -eq PORT`。

## 调试：打印 mitmproxy 真正看到的 hostnames

怀疑判定不对时，写个 addon 包一层 `_ignore_connection`，把参数打出来 —— 比读源码猜快得多：

```python
import re
from mitmproxy import ctx
from mitmproxy.addons import next_layer as nl

_orig = nl.NextLayer._ignore_connection

def patched(self, context, data_client, data_server):
    hostnames = []
    if context.server.peername:
        h, p, *_ = context.server.peername; hostnames.append(f"{h}:{p}")
    if context.server.address:
        h, p, *_ = context.server.address;  hostnames.append(f"{h}:{p}")
    print(f">>> hostnames = {hostnames!r}", flush=True)
    print(f">>> peername={context.server.peername!r} addr={context.server.address!r} "
          f"sni={context.client.sni!r}", flush=True)
    for host in hostnames:
        for rx in ctx.options.ignore_hosts:
            print(f">>>   ignore? {host!r} vs {rx!r} -> "
                  f"{'HIT' if re.search(rx, host, re.IGNORECASE) else 'no'}", flush=True)
    res = _orig(self, context, data_client, data_server)
    print(f">>> RESULT = {res!r}", flush=True)
    return res

nl.NextLayer._ignore_connection = patched
```

挂载：`mitmdump -p 65009 -s your_plugin.py -s _dbg.py --ignore-hosts "<pattern>"`

## ⚠ 多值响应头必须用 `get_all()`，`.get()` 只给一条

`flow.response.headers.get("Set-Cookie")` **只返回第一条**。微信一次响应就下发 6 条
（`fake_id` / `login_certificate` / `login_sid_ticket` / `ticket_certificate` /
`ticket_uin` / `ua_id`），用 `.get()` 会静默丢掉 5 条 —— 而且丢的往往正是你要的那条。

```python
for raw in flow.response.headers.get_all("Set-Cookie") or []:
    # 一条一个 cookie：只取分号前的 k=v
    first = raw.split(";", 1)[0].strip()
    if "=" in first:
        name, _, value = first.partition("=")
        ...
```

**别把多条拼成一个字符串再按逗号切** —— `Expires=Thu, 01-Jan-2026 …` 里就有逗号，
切出来全是碎的。逐条解析才是对的。

同理，cookie 值里出现 `EXPIRED` 和空值要跳过（服务端会用 `k=EXPIRED` 表示删除该 cookie）。

## 已知局限：明文 HTTP 不受白名单影响

判定发生在 `NextLayer`，那时 `context.server.address` 还没解析出来 → `hostnames` 为空 →
`_ignore_connection()` 直接 `return False`（不忽略）。所以 `http://` 请求仍会被处理。
HTTPS（CONNECT）才是大头，影响很小。

## 其他性能提示

- mitmproxy 是**单线程 asyncio**，多核用不上；瓶颈常是**连接堆积**（`CLOSE_WAIT` /
  `FIN_WAIT_2` 半关闭不释放）而非 CPU。排查看
  `Get-NetTCPConnection | Where LocalPort -eq PORT` 的状态分布。
- 改插件后必须**重启** mitmdump（插件在启动时加载一次）。
- 插件里高频 `print` + 每次请求写 JSON 文件也会明显拖慢；落盘要节流（如每 3 秒一次）。
- 只写 `-s plugin.py` 且用 `subprocess.PIPE` 时，插件 stdout 会被吞掉 —— 要开线程
  实时转发，否则运行时完全没有反馈。
