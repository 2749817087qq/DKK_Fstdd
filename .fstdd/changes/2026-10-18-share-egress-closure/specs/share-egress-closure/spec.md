# share-egress-closure — 行为规格

> capability: `share-egress-closure` ｜ change: `2026-10-18-share-egress-closure`
> 机器可读源：`canonical/specs/code/2026-10-18-share-egress-closure.yaml`

## REQ-001 出站收口对 `pre_staged` 同样生效

### SC-001 索引文件不出站

```
GIVEN 一个目录含 EXP-OK.md（sanitized:true、无敏感内容）、README.md、SUBMIT.md
WHEN  以 pre_staged=True 调用 publish_via_scp()
THEN  SHALL 只送出 EXP-OK.md；README.md / SUBMIT.md 不得出站
```

### SC-002 未脱敏文件被剔除并留痕

```
GIVEN 一个目录含 sanitized:false 且带明文 token 的 EXP-BAD.md
WHEN  以 pre_staged=True 调用 publish_via_scp()
THEN  SHALL 剔除该文件并写 target:stage / result:skipped 审计
AND   若全部被剔除，SHALL 返回失败、不发空批次
```

### SC-003 传输源恒为独立临时目录

```
GIVEN 任何 pre_staged=True 的调用
WHEN  观察实际传输源目录
THEN  SHALL 为 _prepare_outbound() 新建的 exp_verify_* 目录
AND   不得是调用方目录
```

## REQ-002 残余判据与脱敏规则同源

### SC-004 补齐 4 类形态

```
GIVEN 文本含 C:\Users\x\y.txt / D:/work/x.md / a@b.com / 10.20.30.40 / db.internal
WHEN  调用 _verify_outbound()
THEN  SHALL 全部拦截
```

### SC-005 公开域名必须放行

```
GIVEN 文本含 github.com / pypi.org / python.org
WHEN  调用 _verify_outbound()
THEN  SHALL 放行
```

> 理由：`sanitize()` 故意保留 `PUBLIC_DOMAINS`。加通用域名分支会把正常经验整条剔除。

## REQ-003 审计记录真实且不膨胀

### SC-006 三档降级只审计一遍

```
GIVEN 一个目录含 N 个会被剔除的文件
WHEN  三档通道全部失败后调用 publish()
THEN  SHALL 只产生 N 条 skipped 审计（不得 ×3）
AND   _prepare_outbound() SHALL 只被调用 1 次
```

### SC-007 记录实际出站文件数

```
GIVEN OUT_DIR 有 30 条历史 + 本轮 1 条新增，全部通过校验
WHEN  silent_share() 写成功审计
THEN  SHALL 记录 sent_count: 31
```

### SC-008 并发写不丢记录

```
GIVEN 两个进程并发各写 100 条审计记录
WHEN  写入完成
THEN  SHALL 保留 200 条
```

## REQ-004 测试出站守卫覆盖面

### SC-009 六种形态全拦

```
GIVEN list-argv run / shell=True 字符串 / check_output / call / check_call / ssh.exe
WHEN  目标含 fstdd-hub
THEN  SHALL 全部拦截
```

### SC-010 不误伤不可达域名

```
GIVEN ssh ubuntu@fstdd-nonexistent-host.invalid ...
WHEN  调用 is_production_egress()
THEN  SHALL 返回 False
```

### SC-011 两种单跑方式都装守卫

```
GIVEN pytest tools/tests/ 或 pytest upstream/tests/ 单跑
WHEN  会话内检查 subprocess.run
THEN  SHALL 已安装守卫
```

## REQ-005 唯一事实源脱敏

### SC-012 两套规则逐字节一致

```
GIVEN 17 类敏感形态样本
WHEN  分别调用 _exp_sync._sanitize_text() 与 share_experience.sanitize()
THEN  SHALL 逐字节一致
AND   _SANITIZE_RULES SHALL 为 None（弱化副本已删）
```

## REQ-006 静默开关读取健壮

### SC-013 非法 UTF-8 不抛异常

```
GIVEN 配置文件含非法 UTF-8 字节
WHEN  调用 _share_disabled()
THEN  SHALL 不抛异常并返回 False
```

### SC-014 子目录能找到项目根

```
GIVEN cwd 为项目子目录，配置在项目根 .fstdd/config.d/
WHEN  调用 _find_project_root()
THEN  SHALL 返回项目根
AND   ~/.fstdd/（只有 projects.yaml 的全局注册表）不得被误判为项目根
```
