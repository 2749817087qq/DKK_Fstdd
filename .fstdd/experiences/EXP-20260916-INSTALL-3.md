<!-- fstdd-inbox
experience_id: EXP-20260916-INSTALL-3
author: anonymous
received_at: 2026-09-25T13:10:02.970403+00:00
remote_addr: 172.18.0.8
node_id: FSTDD001
-->

---
exported_at: 2026-09-25
sanitized: true
---
<!-- fstdd-inbox
experience_id: EXP-20260916-INSTALL-3
author: (anonymous)
received_at: 2026-09-18T02:08:00.740479+00:00
remote_addr: <IP>
-->

---
experience_id: EXP-20260916-INSTALL-3
category: tooling
severity: low
occurrences: 1
exported_at: 2026-09-18
sanitized: true
lifecycle_state: deposited
---
## 现象

`install.sh --py /path/to/python` 传参失败：脚本把 `--py` 本身当成解释器路径，或漏掉后面的参数值。

## 根因

Bash 的 `for arg in "$@"` 在循环开始前已把参数列表展开固定，循环体内的 `shift` **不会**影响迭代顺序，导致 `--py` 与其值错位。

## 处理

改用下标遍历：

```bash
_args=("$@")
_i=0
while [[ $_i -lt ${#_args[@]} ]]; do
  case "${_args[$_i]}" in
    --py) _i=$((_i + 1)); PY="${_args[$_i]:-}" ;;
    *) : ;;
  esac
  _i=$((_i + 1))
done
```

## 性质

Shell 脚本参数解析的基础坑：**在 `for` 循环里 `shift` 无效**，需要精确消费参数值时一律用下标遍历或 `getopt`。
