# FSTDD 标准升级 / 同步规程

> 适用版本：FSTDD 3.0.x+
> 最后更新：2026-09-25
> 来源：`notices/00-STANDARD-UPGRADE-SYNC.md`（v1.0，据 FSTDD009 实战与 E-24 教训固化）

## 一、三层模型（核心）

| 层 | 内容 | 权威 | 同步方式 |
|---|---|---|---|
| **L1 代码/仓库** | git 历史、`upstream/`、测试 | 法定源（服务器裸库 master） | `git fetch server && git merge --ff-only server/master` |
| **L2 模板/配置** | `.fstdd/config.d/`、`templates/`、`standards/` | 上游为准，**本地改动优先保留** | **先 diff 再选路**（见 §三） |
| **L3 全量重建** | `stdd install` | — | **默认禁止**，仅 K 明令时执行 |

## 二、L1：永远先做（风险最低）

```bash
git rev-parse HEAD                       # 记录旧 HEAD
git remote add server <源>               # 无则加，有则跳
git fetch server master
git tag backup-before-sync-$(date +%Y%m%dT%H%M%S) HEAD   # 保命 tag
git merge --ff-only server/master
```
**分叉 ⇒ 停手回执**（附 `git log --oneline -3` / `status` / `merge-base`），**禁止** `reset --hard` / 强推。

## 三、L2：必须先 diff，再选路

```bash
git diff --stat <旧tag>..<新tag> -- .fstdd/config.d .fstdd/templates .fstdd/standards
```

| diff | 走哪条路 |
|---|---|
| **空** | **只改版本号**（`project.yaml` 的 `stdd_version`）—— 无结构变化，不是"假升级" |
| 非空、本地未改 | 采用上游 |
| 非空、本地改过 | **合并**：采用上游 + **保留本地** + 回执逐条列明 |

**本工作区必须保留**：轮询脚本补丁 / 回传端点配置 / 脱敏配置 / Guard 护栏 / 凭证引用。
⇒ **任何会覆盖以上内容的动作，一律停手回执。**

## 四、判据（同步后必交）

| # | 检查 | 期望 |
|---|---|---|
| V1 | `grep stdd_version .fstdd/config.d/project.yaml` | 目标版本 |
| V2 | `python -m pytest tests/test_except_audit.py -q` | 5 passed |
| V3 | 本地保留项逐条核对 | 全部仍在 |
| V4 | `git rev-parse HEAD` | 含目标 tag |

## 五、暂不升级也合法，但必须留痕

结论可为「暂不升级」，但**必须回执**：① 现状（HEAD/版本）② 为何不影响 ③ 何时做。
⇒ 避免被误读为「静默未做」。
