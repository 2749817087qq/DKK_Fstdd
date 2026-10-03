# Test Plan — FSTDD v3.1.1 Release Validation Framework
# Change: 2026-10-03-release-validation-framework
# Phase 2 SPEC — Gate 2 Deliverable

## 1. TC 总览（按 class 依赖链排序）

| Class | TC-ID | 名称 | Spec Scenario | Color 判定 |
|-------|-------|------|--------------|------------|
| **L0 基础设施冒烟** | | | | |
| | L0-01 | git pull 到 fstdd-v3.1.1 tag | SC-L0-001 | 🟢 rc=0 + tag 存在 |
| | L0-02 | install_workbuddy_skills.py → 7/7 OK | SC-L0-002 | 🟢 rc=0 + stdout 成功 |
| | L0-03 | verify_workbuddy_skills.py → 全 PASS | SC-L0-003 | 🟢 rc=0 |
| | L0-04 | node 出现在 multihub online list | SC-L0-004 | 🟢 self_id in list |
| | L0-05 | multihub ping | SC-L0-005 | 🟢 rc=0 + 200 |
| **L1 静态内容校验** | | | | |
| | L1-01 | skills/fstdd-fin/SKILL.md 存在 + >1500 chars | SC-L1-001 | 🟢 assert PASS |
| | L1-02 | SKILL.md 含 7 红线 | SC-L1-002 | 🟢 7 assert PASS |
| | L1-03 | understand.md 含 Step 0.5 + 金融 | SC-L1-003 | 🟢 assert PASS |
| | L1-04 | upstream understand.md 同步 | SC-L1-004 | 🟢 assert PASS |
| | L1-05 | build.md C4 精确 22 行 | SC-L1-005 | 🟢 精确 = 22 |
| | L1-06 | upstream build.md C4 同步 22 行 | SC-L1-006 | 🟢 精确 = 22 |
| | L1-07 | B2.5 含 10 维金融测试关键词 | SC-L1-007 | 🟢 10 assert PASS |
| | L1-08 | 8 类金融失败模式关键词 | SC-L1-008 | 🟢 8 assert PASS |
| | L1-09 | KG FIN- 节点 ≥ 12 | SC-L1-009 | 🟢 count >= 12 |
| | L1-10 | KG graph_version >= 1.1 | SC-L1-010 | 🟢 float >= 1.1 |
| | L1-11 | version.yaml fstdd_version = 3.1.1 | SC-L1-011 | 🟢 assert PASS |
| | L1-12 | feedback_protocol.mandatory = true | SC-L1-012 | 🟢 assert PASS |
| | L1-13 | 3 平台 install 命令字段齐全 | SC-L1-013 | 🟢 3 assert PASS |
| **L2 Skill 加载可见性** | | | | |
| | L2-01 | /fstdd-understand → Step 0.5 可见 | (手动/UI) | 🟢 output contains "Step 0.5" |
| | L2-02 | /fstdd-build → C4 22 行可见 | (手动/UI) | 🟢 C4 section table 完整 |
| | L2-03 | /fstdd-build → B2.5 可见 | (手动/UI) | 🟢 B2.5 section 存在 |
| | L2-04 | /fstdd-fin → 加载无 error | (手动/UI) | 🟢 no error |
| **L3 金融钩子功能验证** | | | | |
| | L3-01 POS | 支付系统需求 → Step 0.5 + 7 红线触发 | (手动/LLM judge) | 🟢 agent 主动查 7 红线 |
| | L3-02 NEG | 博客需求 → 跳过 Step 0.5 | (手动/LLM judge) | 🟢 agent 直接 Step 1 |
| **L4 CLI Canonical 模板** | | | | |
| | L4-01 | fstdd canon generate → proposal.yaml 生成 | (CLI) | 🟢 file exists |
| | L4-02 | proposal.yaml 含 finance 字段 | (CLI + yaml parse) | 🟢 fields present |
| | L4-03 | fstdd validate → schema OK | (CLI) | 🟢 rc=0 |
| **L5 Mini E2E 四阶段** | | | | |
| | L5-01 | 完整四阶段 tiny change | (手动/FSTDD) | 🟢 archive 目录存在 |
| | L5-02 | Gate 1-3 全 approve | (Gate evidence) | 🟢 3 Gate 记录 |
| | L5-03 | 归档到 archive/ | (文件系统) | 🟢 path exists |
| **L6 Multihub 反馈** | | | | |
| | L6-01 | claim release task | (multihub auto) | 🟢 claim 200 |
| | L6-02 | complete + result JSON | (multihub auto) | 🟢 complete 200 |
| | L6-03 | result 含 node_id/platform/report | (JSON parse) | 🟢 字段齐全 |
| **L7 跨节点汇总** | | | | |
| | L7-01 | 全节点 result → 矩阵 | (发布者侧) | 🟢 95%+ 绿 → ship |
| | L7-02 | skill content hash 一致 | (发布者侧) | 🟢 hash match |
| | L7-03 | 最终 ship 判定 | (发布者侧) | 🟢 GREEN → ship 就绪 |

---

## 2. 执行计划（按 class 依赖链）

```
for class in [L0, L1, L2, L3, L4, L5, L6]:
    if class == L0: 每节点必跑，rc!=0 → STOP
    if class == L1: 所有平台跑，任何 FAIL → STOP
    if class == L2: 需要 UI 的节点跑，无 UI → SKIP
    if class == L3: 需要 Agent 理解，无 LLM → SKIP
    if class == L4: 需要 fstdd CLI，无 Python → SKIP
    if class == L5: 指定 1-2 节点跑（designated），其他 SKIP
    if class == L6: 所有节点最后自动跑（runner 内置）

L7: 仅 FSTDD003 发布者侧，所有节点跑完后执行
```

---

## 3. runner 命令参考

```bash
# G1 WorkBuddy 节点
python tests/run_release_validation.py --platform workbuddy

# G2 Linux 节点（无 UI → 自动 skip L2/L3）
python3 tests/run_release_validation.py --platform workbuddy

# G3 trae self（带 L5 E2E）
python tests/run_release_validation.py --platform trae --e2e

# G4 Claude Code
python tests/run_release_validation.py --platform claude_code

# G5 Designated E2E
python tests/run_release_validation.py --platform workbuddy --e2e --skip l0,l1,l2,l3,l4,l6
```

---

## 4. 颜色编码定义（统一）

| Code | Name | Meaning | Exit Code |
|------|------|---------|-----------|
| 🟢 | PASS | 命令 exit 0 / assert 全过 | 0 |
| 🟡 | WARN | 有 SKIP 或非阻断 warning | 0（除非全 WARN） |
| 🔴 | FAIL | exit non-zero / assert 失败 | 1 |
| ⚪ | SKIP | 本平台不适用 | 不计入 |
| 🔵 | PENDING | multihub 任务未认领 | — |

---

## 5. 反馈协议（强制）

每个节点 runner 执行完毕后，**自动**执行 L6：
- claim multihub release task
- complete 并塞入 result JSON：
  ```json
  {
    "node_id": "FSTDD-K",
    "platform": "workbuddy",
    "timestamp": "2026-10-03T13:00:00+08:00",
    "overall": "PASS",
    "classes": {
      "L0": {"status": "PASS", "duration_ms": 842},
      "L1": {"status": "PASS", "duration_ms": 1203},
      "L2": {"status": "PASS", "duration_ms": 18402},
      "L3": {"status": "PASS", "duration_ms": 30122},
      "L4": {"status": "PASS", "duration_ms": 2001},
      "L5": {"status": "SKIP", "reason": "not designated"},
      "L6": {"status": "PASS", "duration_ms": 910}
    },
    "tcs": [
      {"id": "L0-01", "status": "PASS", "evidence": "git describe → fstdd-v3.1.1"},
      {"id": "L0-02", "status": "PASS", "evidence": "install: 7/7 OK"},
      {"id": "L1-05", "status": "PASS", "evidence": "C4 rows = 22"}
    ]
  }
  ```

---

## 6. 成功判定（L7 发布者侧）

- **Release Ship 就绪**: ≥ 95% 节点 L0 PASS，≥ 90% 节点 L1+L4 PASS，无全局红色
- **需先修复**: 任何 🔴 L0/L1 FAIL → 定位节点 → 修复 → 重跑 → 绿了再说
- **可接受 WARN**: 单节点 L2/L3 SKIP（无 UI）、L5 SKIP（非 designated）
