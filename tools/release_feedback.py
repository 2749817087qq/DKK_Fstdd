"""Track agent feedback for release announce tasks.

Usage: python tools/release_feedback.py [task_id] [--summary-only]
Default: tracks the latest release announce task (kind=change, summary=RELEASE)
"""
import sys, json, argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hub_client import HubClient

def load_hub():
    env = {}
    env_path = Path(__file__).parent / '.heartbeat.env'
    with open(env_path, encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return HubClient(
        token=env.get('HUB_TOKEN', ''),
        url=env.get('HUB_URL', 'http://127.0.0.1:8788'),
        node_id=env.get('NODE_ID', 'FSTDD003')
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('task_id', nargs='?', default=None)
    ap.add_argument('--summary-only', action='store_true')
    args = ap.parse_args()

    hub = load_hub()

    if args.task_id:
        tid = args.task_id
    else:
        # find latest release announce task
        tasks = hub.list_tasks()
        if isinstance(tasks, dict):
            tasks = tasks.get('tasks') or tasks.get('items') or []
        release_tasks = [t for t in tasks if 'RELEASE' in t.get('summary', '') and t.get('kind') == 'change']
        if not release_tasks:
            print('No release announce task found.')
            return
        tid = release_tasks[0].get('task_id')

    print(f'\n=== Release Feedback Tracker ===')
    print(f'task_id: {tid}')
    print(f'tracked by: FSTDD003\n')

    # Get task details
    tasks = hub.list_tasks()
    if isinstance(tasks, dict):
        tasks = tasks.get('tasks') or tasks.get('items') or []
    task = next((t for t in tasks if t.get('task_id') == tid), None)
    if not task:
        print(f'Task {tid} not found.')
        return

    print(f'summary: {task.get("summary", "?")}')
    print(f'status: {task.get("status", "?")}')
    scope = task.get('scope', {}) or {}
    print(f'version: {scope.get("version", "?")}')
    print(f'tag: {scope.get("tag", "?")}\n')

    # Now poll all online nodes — have they claimed/completed this?
    try:
        nodes = hub.list_online_nodes()
        if isinstance(nodes, dict):
            nodes = nodes.get('nodes') or nodes.get('items') or []
    except Exception as e:
        print(f'Cannot list nodes: {e}')
        nodes = []

    # Re-list tasks to see which have been completed/claimed
    all_tasks = hub.list_tasks()
    if isinstance(all_tasks, dict):
        all_tasks = all_tasks.get('tasks') or all_tasks.get('items') or []
    this_task_completions = [t for t in all_tasks if t.get('task_id') == tid]

    print(f'Online nodes: {len(nodes)}')
    print(f'Claimed/completed on this task: {len(this_task_completions)}\n')

    claimed_by = []
    completed_by = []
    for t in this_task_completions:
        s = t.get('status', '')
        owner = t.get('claimed_by') or t.get('owner') or t.get('node_id') or '?'
        result = t.get('result', '')
        claimed_by.append(owner)
        if s == 'done':
            completed_by.append({'node': owner, 'result': result})

    if not claimed_by:
        print('🚨 NO AGENTS HAVE CLAIMED THIS RELEASE TASK YET')
        print('  -> agents may not be reading multihub, or the announce just went out')
    else:
        print(f'📋 Claimed by {len(set(claimed_by))} nodes:')
        for n in sorted(set(claimed_by)):
            marker = '✅' if any(c['node'] == n for c in completed_by) else '⏳'
            print(f'  {marker} {n}')

    if completed_by:
        print(f'\n📊 Install feedback ({len(completed_by)} nodes reported):')
        for c in completed_by:
            res = c['result']
            try:
                fb = json.loads(res) if isinstance(res, str) else res
                platform = fb.get('platform', '?')
                irc = fb.get('install_rc', '?')
                vrc = fb.get('verify_rc', '?')
                notes = fb.get('notes', '')
                print(f'  [{c["node"]}] platform={platform} install={"✅" if irc==0 else "❌"}(rc={irc}) verify={"✅" if vrc==0 else "❌"}(rc={vrc}) {notes}')
            except:
                print(f'  [{c["node"]}] result={str(res)[:100]}')

    # Summary
    if args.summary_only:
        return

    print(f'\n--- Open action ---')
    print(f'Run again: python tools/release_feedback.py {tid}')
    print(f'or track by node: run this on each agent node after install')

if __name__ == '__main__':
    main()
