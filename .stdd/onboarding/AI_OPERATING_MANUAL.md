# STDD AI 操作手册 / AI Operating Manual

> **你必须完整阅读本文档，并在首次 Change 中严格遵守以下操作规范。**
> **不得手动编辑 `.stdd.yaml`。所有 Phase 和 Gate 操作必须通过 CLI 命令执行。**

---

## 一、CLI 命令速查 / CLI Quick Reference

| 你要做什么 | 命令 | 说明 |
|-----------|------|------|
| 启动新 Change | `/stdd-understand <需求描述>` | Phase 1 开始 |
| 查看当前 Change 状态 | `stdd status` | 显示 Phase/Guard/僵尸/Zombie |
| **推进 Phase** | `stdd phase advance <change>` | ⚠️ **必须用 CLI，禁止手动改 .stdd.yaml！** |
| **确认 Gate 1** | `stdd gate approve <change> --gate 1` | 用户确认 proposal 后执行 |
| **确认 Gate 2** | `stdd gate approve <change> --gate 2` | 用户确认 design+specs 后执行 |
| **确认 Gate 3** | `stdd gate approve <change> --gate 3` | 用户确认 test-report 后执行 |
| 放弃 Change | `stdd abort <change>` | 不要让 Change 变成僵尸 |
| 归档完成的 Change | `stdd archive <change>` | Phase 5 完成 + Gate 3 确认后执行 |
| 查看 Guard 状态 | `stdd guard status` | 检查流程守护是否活跃 |
| 安装 Guard | `stdd guard init` | 流程守护安装 |

### Phase 推进完整流程

```
1. 用户确认 proposal → stdd gate approve --gate 1
2. stdd phase advance → SPEC
3. 用户确认 design+specs → stdd gate approve --gate 2
4. stdd phase advance → SLICE
5. stdd phase advance → BUILD
6. 实现完成后 → stdd phase advance → VERIFY
7. 用户确认 test-report → stdd gate approve --gate 3
8. stdd archive <change>
```

---

## 二、绝对禁止的行为 / Absolutely Forbidden

| ❌ 禁止 | ✅ 应该 |
|---------|--------|
| **手动编辑 `.stdd.yaml` 修改 phase 或 status** | 使用 `stdd phase advance` |
| 跳过 Gate 确认，判断"用户可能已经同意了" | 使用 `stdd gate approve` 并等待用户明确回复 |
| Phase 5 (Verify) 完成前标记 Change 为"完成" | 运行 Verify checks + Gate 3 确认后 `stdd archive` |
| 在没有 active change 时直接编辑代码 | `/stdd-understand` 创建新 Change |
| 让 Change 长期卡在某个 Phase 变成僵尸 | 推进或 `stdd abort` |
| 批量写完所有代码再补测试 | RED→GREEN→REFACTOR，每 Slice 独立验证 |

---

## 三、自检清单 / Self-Check

在开始第一个 Change 前，确认你能回答：

- [ ] 如何推进 Phase？（答：`stdd phase advance <change>`）
- [ ] 如何确认 Gate？（答：`stdd gate approve <change> --gate <N>`）
- [ ] 能否手动编辑 .stdd.yaml 来修改 phase？（答：❌ 绝对不行）
- [ ] Phase 5 (Verify) 可以跳过吗？（答：❌ 不可跳过）
- [ ] 什么命令查看当前状态？（答：`stdd status`）
- [ ] Change 完成后如何归档？（答：`stdd archive <change>`）

> **你现在应该已经能正确回答以上全部问题。如果有任何不确定，请重新阅读第一节的 CLI 命令速查表。**
