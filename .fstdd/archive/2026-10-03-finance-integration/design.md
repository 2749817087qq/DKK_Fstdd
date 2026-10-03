# FSTDD × 金融：修复 fstdd-fin 资产 + 核心四阶段融合 — 技术设计

## Context

FSTDD 宣称集成金融领域增强层（fstdd-fin / FinFSTDD），但审计发现融合度 0.6/5：
- 资产游离：fstdd-fin SKILL.md 仅在 `_scratch/stdd-dev/` 和 `_scratch/upstream-cli-sync/` 有孤立副本
- 安装链路断裂：`install_workbuddy_skills.py` 零 fin 条目
- 流程零融合：核心四阶段 skill（understand/spec/build/deliver）零金融红线/测试/失败模式条目
- 配置零注册：`quality.yaml` 失败模式库 14 类零金融条目，`platforms.yaml` 未注册 fstdd-fin

任务类型：configuration + documentation（纯 skill + 配置层变更，零 upstream/ 内核改动）

## Decisions

### 1. 融合层定位：轻量钩子 vs 独立 skill 体系

**方案**：在通用 skill 里加"条件段落"（条件触发），不创建第二个独立流程体系

**为什么**：
- fstdd-fin SKILL.md 已经做了金融增强的独立 skill，但它只适合"全金融项目"
- 现实中大量项目是"有部分金融特征"（如带支付的 SaaS、含账户系统的工具），需要的是**通用流程里有金融钩子**，而不是切到完全不同的 skill
- 加条件段落（"如果需求包含金融关键词则执行以下检查"）是最小侵入的方式

**备选方案及排除原因**：
- 备选 A：让 fstdd-fin 完全替代四阶段 skill 执行金融项目 → 过于厚重，非全金融项目无法用
- 备选 B：在 CLI 层加 financial flag → 纯 skill 层项目（非 Python）用不了 CLI

### 2. 金融判定规则：关键词白名单

**方案**：understand.md 前置段落，关键词白名单判定：支付/银行/交易/撮合/风控/KYC/AML/DeFi/结算/对账/资金/金额/Decimal/幂等/账户/余额/汇率/杠杆/保证金/清算/行情/托管/票据/债券/股票/期货/期权/私募/公募/资管/净值/回撤/夏普/贝塔/阿尔法/波动率/流动性风险/信用风险/市场风险

**为什么**：
- 关键词触发 = 纯文本匹配，无需任何结构化输入
- 白名单足够具体（35+ 金融领域关键词），误触发概率低
- 触发后只是"多做检查"，不阻断非金融项目任何步骤

**备选方案及排除原因**：
- 备选 A：让用户手动标注 → 增加交互摩擦，违反 FSTDD "自动发现风险"设计
- 备选 B：LLM 自动判断 → 不可靠且增加成本

### 3. fstdd-fin SKILL.md 内容：不改动

**方案**：直接从 `_scratch/stdd-dev/stdd-repo/skills/fstdd-fin/SKILL.md` 拷贝到 `skills/fstdd-fin/SKILL.md`，一字不改

**为什么**：
- 审计确认 266 行质量合格（7 红线 / 4 阶段增强 / 10 维测试 / 8 失败模式 / 4 主线）
- SKILL.md 已经很好地处理了边界（wb-finance-skill 投研 vs fstdd-fin 研发）
- 改动只会引入新风险

### 4. quality.yaml 金融失败模式：追加而非替换

**方案**：在现有 14 类失败模式后面追加 8 类金融特有模式

**为什么**：
- 14 类通用失败模式对金融项目同样有效（如 precision loss = 通用精度丢失在金融场景有特别严重后果）
- 金融特有模式是**补充检查**，不是替换
- 追加保持向后兼容

**备选方案及排除原因**：
- 备选 A：新建 `finance_quality.yaml` 分开维护 → 双配置文件增加认知负担
- 备选 B：把金融模式内嵌到现有 14 类里 → 模糊了"通用" vs "金融特有"的边界

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │   FSTDD Project (non-finance)       │
                    │   通用流程，不触发金融钩子            │
                    └─────────────────────────────────────┘
                                      │
                                      ▼
understand.md ── 关键词匹配 ── YES ──► 7 红线强制检查（缺失=Gate 1 不通过）
                                      │
                      NO ◄────────────┘
                      │
                      ▼
              标准 UNDERSTAND（不变）
                      │
                      ▼
build.md ── 同关键词匹配 ── YES ──► 10 维金融测试强制覆盖
                      │
                      ▼
              标准 BUILD（不变）
                      │
                      ▼
              quality.yaml 失败模式库
                      │
                 ┌────┴────┐
                 │         │
            14 通用    8 金融特有
```

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 关键词白名单太宽，非金融项目误触发 | 白名单限定 35+ 金融领域专业词，不用"金额"这种太泛的词；触发后只是追加检查，不阻断 |
| fstdd-fin SKILL.md 放了目录但 install 脚本没接 → 还是孤立 | C2 明确修改 install_workbuddy_skills.py 加 source + install 路径 |
| 金融钩子插入位置不对 → 破坏 understand/build.md 原结构 | 用"条件段落"格式（`## 金融系统前置检查（条件触发）`），独立于原有章节 |
| quality.yaml 追加失败模式破坏现有 schema | 只追加，不改现有 14 类；validate 后确认格式正确 |
