"""Append finance domain threads + failure patterns to knowledge-graph.yaml."""
import yaml, datetime

path = r'd:\FSTDD003\.fstdd\knowledge\knowledge-graph.yaml'
with open(path, 'r', encoding='utf-8') as f:
    raw = f.read()

# Parse
data = yaml.safe_load(raw)
print(f'Before: nodes={len(data["nodes"])}, version={data["graph_version"]}')

# Check duplicates
existing_ids = {n['id'] for n in data['nodes']}

new_nodes = [
    # 4 domain_threads
    dict(category='domain_thread', cross_project_count=1, description='支付/转账/清算 — 金融系统核心资金流转路径',
         fix_template_refs=[], id='FIN-THR-001', metrics=dict(last_seen='2026-10-03T10:20:00+08:00', occurrence_count=1, severity_trend='stable'),
         projects=['fstdd'], root_cause='', severity='medium', tags=['finance','capital_flow','payments'], title='capital_flow', type='domain'),
    dict(category='domain_thread', cross_project_count=1, description='订单簿/撮合引擎 — 交易类金融系统核心',
         fix_template_refs=[], id='FIN-THR-002', metrics=dict(last_seen='2026-10-03T10:20:00+08:00', occurrence_count=1, severity_trend='stable'),
         projects=['fstdd'], root_cause='', severity='medium', tags=['finance','trading','matching','exchange'], title='trading_matching', type='domain'),
    dict(category='domain_thread', cross_project_count=1, description='风控/KYC/AML — 合规与安全交叉领域',
         fix_template_refs=[], id='FIN-THR-003', metrics=dict(last_seen='2026-10-03T10:20:00+08:00', occurrence_count=1, severity_trend='stable'),
         projects=['fstdd'], root_cause='', severity='high', tags=['finance','risk','compliance','kyc','aml'], title='risk_compliance', type='domain'),
    dict(category='domain_thread', cross_project_count=1, description='消息队列/分布式事务/可观测性 — 金融系统技术底座',
         fix_template_refs=[], id='FIN-THR-004', metrics=dict(last_seen='2026-10-03T10:20:00+08:00', occurrence_count=1, severity_trend='stable'),
         projects=['fstdd'], root_cause='', severity='medium', tags=['finance','tech_infra','distributed','observability'], title='tech_infra', type='domain'),
    # 8 failure_patterns
    dict(category='double_charge', cross_project_count=1, description='重复扣款 — 幂等 key 缺失/消息重试未去重',
         fix_template_refs=['fstdd-fin-SKILL-MD'], id='FIN-FAIL-001', metrics=dict(last_seen='2026-10-03T10:20:00+08:00', occurrence_count=1, severity_trend='stable'),
         projects=['fstdd'], root_cause='幂等性未实现或不完整', severity='high', tags=['finance','payment','idempotency'], title='double_charge', type='failure_pattern'),
    dict(category='reconciliation_gap', cross_project_count=1, description='账实不符 — 内部账本与外部对账源不一致无处理流程',
         fix_template_refs=['fstdd-fin-SKILL-MD'], id='FIN-FAIL-002', metrics=dict(last_seen='2026-10-03T10:20:00+08:00', occurrence_count=1, severity_trend='stable'),
         projects=['fstdd'], root_cause='reconciliation 机制缺失', severity='high', tags=['finance','reconciliation','books'], title='reconciliation_gap', type='failure_pattern'),
    dict(category='silent_degradation', cross_project_count=1, description='静默降级 — 支付/风控/对账组件降级时未显式标记和告警',
         fix_template_refs=['fstdd-fin-SKILL-MD'], id='FIN-FAIL-003', metrics=dict(last_seen='2026-10-03T10:20:00+08:00', occurrence_count=1, severity_trend='stable'),
         projects=['fstdd'], root_cause='降级处理只打日志不阻断', severity='high', tags=['finance','degradation','fallback'], title='silent_degradation', type='failure_pattern'),
    dict(category='precision_loss', cross_project_count=1, description='精度丢失 — 用 float 处理金额导致精度丢失',
         fix_template_refs=['fstdd-fin-SKILL-MD'], id='FIN-FAIL-004', metrics=dict(last_seen='2026-10-03T10:20:00+08:00', occurrence_count=1, severity_trend='stable'),
         projects=['fstdd'], root_cause='金额字段未用 Decimal / BigDecimal', severity='high', tags=['finance','decimal','precision','money'], title='precision_loss', type='failure_pattern'),
    dict(category='audit_gap', cross_project_count=1, description='审计缺口 — 关键操作无不可变日志',
         fix_template_refs=['fstdd-fin-SKILL-MD'], id='FIN-FAIL-005', metrics=dict(last_seen='2026-10-03T10:20:00+08:00', occurrence_count=1, severity_trend='stable'),
         projects=['fstdd'], root_cause='日志非结构化/可修改', severity='high', tags=['finance','audit','log','immutable'], title='audit_gap', type='failure_pattern'),
    dict(category='state_machine_gap', cross_project_count=1, description='状态机漏洞 — 非法状态转换/死锁/无补偿',
         fix_template_refs=['fstdd-fin-SKILL-MD'], id='FIN-FAIL-006', metrics=dict(last_seen='2026-10-03T10:20:00+08:00', occurrence_count=1, severity_trend='stable'),
         projects=['fstdd'], root_cause='交易状态机未覆盖所有路径', severity='high', tags=['finance','state_machine','saga','tcc'], title='state_machine_gap', type='failure_pattern'),
    dict(category='limit_bypass', cross_project_count=1, description='额度穿透 — 限额只在客户端检查/并发竞态',
         fix_template_refs=['fstdd-fin-SKILL-MD'], id='FIN-FAIL-007', metrics=dict(last_seen='2026-10-03T10:20:00+08:00', occurrence_count=1, severity_trend='stable'),
         projects=['fstdd'], root_cause='限额未在服务端原子检查', severity='high', tags=['finance','limit','concurrency','race'], title='limit_bypass', type='failure_pattern'),
    dict(category='compliance_gap', cross_project_count=1, description='合规遗漏 — KYC/AML/跨境数据传输覆盖不全',
         fix_template_refs=['fstdd-fin-SKILL-MD'], id='FIN-FAIL-008', metrics=dict(last_seen='2026-10-03T10:20:00+08:00', occurrence_count=1, severity_trend='stable'),
         projects=['fstdd'], root_cause='合规流程未嵌入主交易路径', severity='high', tags=['finance','compliance','kyc','aml','gdpr'], title='compliance_gap', type='failure_pattern'),
]

added = 0
for n in new_nodes:
    if n['id'] not in existing_ids:
        data['nodes'].append(n)
        added += 1
    else:
        print(f'SKIP duplicate: {n["id"]}')

print(f'Added: {added}, Total nodes: {len(data["nodes"])}')

# Update version + timestamp
data['graph_version'] = '1.1'
data['last_merged'] = datetime.datetime.now(datetime.timezone.utc).isoformat()

with open(path, 'w', encoding='utf-8') as f:
    yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=True)

# Verify
with open(path, 'r', encoding='utf-8') as f:
    v = yaml.safe_load(f)
fin_ids = [n['id'] for n in v['nodes'] if n['id'].startswith('FIN-')]
print(f'After: nodes={len(v["nodes"])}, version={v["graph_version"]}')
print(f'FIN nodes ({len(fin_ids)}): {fin_ids}')
print('YAML valid OK')
