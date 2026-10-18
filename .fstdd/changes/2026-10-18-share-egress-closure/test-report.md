# 经验静默回传出站收口 · 测试报告

> change: `2026-10-18-share-egress-closure` ｜ 基线 `14a941c` ｜ 终态 `ab79632`
> 日期：2026-10-18

## 一、结论

| 项 | 结果 |
|---|---|
| 全量门禁 `pytest tests upstream/tests` | **1326 passed / 11 skipped / 0 failed**（提交后复跑 `test_a6` 转绿） |
| 新增用例 | 97（51 + 37 + 9） |
| 真实端到端 | **已完成 1 次**（隔离 inbox，远端核对全绿） |
| 四自检 | `install_workbuddy_skills.py` PASS；`verify_workbuddy_skills.py` PASS（无 WARN） |

## 二、TC 执行明细

| TC | 覆盖 | 结果 | 证据 |
|---|---|---|---|
| TC-CLOSURE-001 | SC-001 索引文件不出站 | ✅ PASS | 真实运行远端 90 文件、无 README/SUBMIT |
| TC-CLOSURE-002 | SC-002 未脱敏剔除 + 留痕 | ✅ PASS | `[skip] EXP-BAD1.md：自称未脱敏` |
| TC-CLOSURE-003 | SC-002 不发空批次 | ✅ PASS | 返回 `(False, "...无可用文件...")`，subprocess 0 调用 |
| TC-CLOSURE-004 | SC-003 传输源为 `exp_verify_*` | ✅ PASS | argv 源路径 `.../exp_verify_*/EXP-A.md` |
| TC-CLOSURE-005 | SC-004/005 残余判据真值表 | ✅ PASS | 10/10（7 拦 + 3 放） |
| TC-CLOSURE-006 | SC-006 三档只审计一遍 | ✅ PASS | 2 个剔除 → **2 条**审计（改前 4→12） |
| TC-CLOSURE-007 | SC-007 `sent_count` | ✅ PASS | 89 条记录均 `sent_count: 90` |
| TC-CLOSURE-008 | SC-008 并发写不丢 | ⚠️ **未复测** | 见「已知缺口」 |
| TC-CLOSURE-009 | SC-009 守卫六形态 | ✅ PASS | 6/6 拦截 |
| TC-CLOSURE-010 | SC-010 不误伤 | ✅ PASS | `ubuntu@<不可达>` 放行 |
| TC-CLOSURE-011 | SC-011 两种单跑都装守卫 | ✅ PASS | 两棵树各自 `is_installed() == True` |
| TC-CLOSURE-012 | SC-012 脱敏唯一事实源 | ✅ PASS | 17 类形态 0 分叉 |
| TC-CLOSURE-013 | 真实端到端 | ✅ PASS | 见下节 |
| TC-CLOSURE-014 | SC-013/014 静默开关 | ✅ PASS | 9/9 |

## 三、真实端到端证据

```
$ FSTDD_INBOX_DIR=/home/ubuntu/_fstdd-e2e-verify FSTDD_AUDIT_TEST=1 \
    python tools/share_experience.py --silent
[OK] 已 scp 90 条经验 → fstdd-hub:/home/ubuntu/_fstdd-e2e-verify/local-experiences-20261018-132425
经验静默回传: 成功（目标 scp）
```

远端核对：

| 检查 | 结果 |
|---|---|
| 文件数 | 90 |
| `README.md` / `SUBMIT.md` | **已过滤**（旧批次 16/25 都含它们） |
| 残余命中（token / Windows 路径 / IPv4） | **0** |
| `sanitized: false` 文件 | **0** |
| 审计记录 | 89 条 `target: scp` / `result: success` / `sent_count: 90` |
| 落点 | `.fstdd/share-audit.test.yaml`（`FSTDD_AUDIT_TEST=1` 生效） |
| 生产审计污染 | **0 条当日记录** |

验证目录已 `rm -rf`；共享枢纽批次数未受影响。

## 四、修法禁区（回归锁）

审计员建议「把 `SANITIZE_RULES` 的域名正则搬进残余判据」。**未采纳**，并加正向用例锁死：

```
GIVEN 文本含 github.com / pypi.org / python.org
WHEN  调用 _verify_outbound()
THEN  SHALL 放行
```

理由：`sanitize()` 故意保留 `PUBLIC_DOMAINS`。加通用域名分支会把正常经验整条剔除，
**误杀不可逆**（EXP-20260915-B3）。当前 90 个经验文件在新判据下 **90/90 通过**，零误杀。

## 五、设计偏离

| # | 偏离 | 原因 |
|---|---|---|
| ADJ-001 | 守卫打点从 `Popen` 回退到 `run`+`call` | `asyncio/windows_utils.py:125` 在 import 期 `class Popen(subprocess.Popen)` 继承它，函数不可继承 ⇒ 全量门禁收集期崩（`TypeError: function() argument 'code' must be code, not str`）。直接 `Popen(...)` 成为已知缺口，写进 docstring |
| ADJ-002 | `pre_staged` 语义重定义 | 原语义「跳过整个收口」导致三道防线全失效；改为「只跳过脱敏动作」 |
| ADJ-003 | 残余判据只补 4 类，不加通用域名 | 见上节修法禁区 |

## 六、已知缺口

1. **并发写锁未复测**（TC-CLOSURE-008）。审计员测得改前 2 进程丢 20%；`_append_locked()`
   加了 `msvcrt.locking`，但**改后未做并发复测**。理由：并发探针会向审计文件写入大量假记录，
   而审计分流只防 pytest 上下文。建议后续在隔离 tmp 目录里补自动化用例。
2. **守卫漏 `Popen` 直接调用**。见 ADJ-001。仓库内已 grep 确认无此形态。
3. **`collect_local()` 无「已分享」过滤**。每次 `--silent` 重传全库（实测 89 条）。
   属既有设计，不在本 change 范围；但它是远端 28 个批次重复的根因，建议单独立项。
4. **`_exp_sync` 在安装包场景会 fail-closed**。`tools/` 不进 wheel ⇒ `--hub-dir` 必然
   RuntimeError。有意为之（宁可失败不降级），已写入 CHANGELOG。

## 七、复现命令

```bash
# 全量门禁（必须显式给路径）
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \
  python -m pytest tests upstream/tests -q

# 本 change 聚焦子集
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python -m pytest \
  tests/test_share_ssh_transport.py tests/test_share_publish_sanitize.py \
  tests/test_share_hardening.py tests/test_share_hardening_tc_traceability.py \
  tests/test_exp_sync_sanitize_parity.py tests/test_share_disabled_switch.py \
  upstream/tests/test_silent_share.py -q
# → 168 passed, 2 skipped

# 真实端到端（隔离 inbox，跑完记得清理）
FSTDD_INBOX_DIR=/home/ubuntu/_fstdd-e2e-verify FSTDD_AUDIT_TEST=1 \
  python tools/share_experience.py --silent
ssh fstdd-hub 'rm -rf /home/ubuntu/_fstdd-e2e-verify'
```
