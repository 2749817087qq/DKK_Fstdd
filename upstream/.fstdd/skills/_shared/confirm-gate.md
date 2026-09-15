## 确认门

> STDD 强制确认机制：每个 Phase 产出完成后，必须等待用户确认才能进入下一阶段。

**确认前检查清单：**
- [ ] 当前 Phase 的所有产出文件已生成
- [ ] 产出内容与用户需求一致
- [ ] 无明显遗漏或逻辑错误
- [ ] 相关测试案例已覆盖 Spec Scenario

**确认提示：**
请在继续之前审查以上产出。回复"确认"以进入下一阶段，或提出修改意见。

**V3.0.5 硬防线（AI 行为规范）：**
- ⛔ **AI 不得静默自跑 `stdd gate approve`**。无用户确认的 approve 是被禁止的（cmd_gate 强制 `--confirmed-by` 且 audit 落库，会被当场暴露）。
- ⛔ **AI 不得伪造 evidence**。`--evidence` 必须是用户确认原文（如 `"用户：确认"`）。
- ✅ 正确顺序：**展示确认框 → 等用户口头明确确认 → 再执行**：
  ```
  stdd gate approve <change> --gate N --confirmed-by dialog --evidence "用户确认原文"
  ```
- file_token 通道仅用于用户人工创建 `GATE<N>_APPROVED` 文件（guard 阻断 AI 写入 token）；cli 通道用于终端直接确认。
- 每次 approve 落库审计链：`confirmed_by`(通道) + `confirmed_actor`(发起者) + `confirmed_evidence`(证据) + `confirmed_at`(时间)，审计可分辨「人工发起」vs「AI 自作主张」。
