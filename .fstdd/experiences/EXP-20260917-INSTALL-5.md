<!-- fstdd-inbox
experience_id: EXP-20260917-INSTALL-5
author: (anonymous)
received_at: 2026-09-18T02:08:01.822469+00:00
remote_addr: 27.8.11.15
-->

---
experience_id: EXP-20260917-INSTALL-5
category: tooling
severity: medium
occurrences: 2
title: 上轮 4 项 install.sh 修复均未合入上游 + for/shift 参数解析失效根因
exported_at: 2026-09-18
sanitized: true
---
## 现象

首轮报告的 4 项 `install.sh` 修复，在第二轮拉取上游 master 复测时
**全部未合入**，`install.sh` 仍是旧实现。同时 `--py <path>`
（空格形式）解析失效的问题依旧存在。

## 根因

`install.sh` 的参数解析用的是 `for ... in "$@"` + `shift`：

```bash
for arg in "$@"; do
  case "$arg" in
    --py) shift; PY="${1:-}" ;;   # ← 拿到的还是 "--py" 自身
  esac
done
```

`for` 的迭代列表在展开时已固定，**循环体内 `shift` 不会让下一次迭代跳过已消费的参数**，
于是 `PY="${1:-}"` 取到 `--py` 自己，报 `--py: command not found`。

（`--py=/path` 形式不受影响，因为走的是 `"${arg#*=}"` 分支。）

## 处理

改用下标遍历：

```bash
_args=("$@")
_i=0
while [[ $_i -lt ${#_args[@]} ]]; do
  case "${_args[$_i]}" in
    --yes)   AUTO_YES=1 ;;
    --py)    _i=$((_i + 1)); PY="${_args[$_i]:-}" ;;
    --py=*)  PY="${_args[$_i]#*=}" ;;
  esac
  _i=$((_i + 1))
done
```

## 复测建议

上游更新后，先 `diff` 本地修复版与新版 `install.sh`，确认 4 项是否合入：
参数解析 / `export FSTDD_OUT`+`FSTDD_SRC` / `_winpath` 路径转换 / 结束 echo 用真实变量。
未合入就在本地保留修复版，避免每次重装都重新踩一遍。
