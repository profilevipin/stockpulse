#!/usr/bin/env python3
"""Incremental WF1 deployment test to find the breaking node."""
import json, requests, time

API_URL = 'https://stockpulse.co.in/api/v1'
API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4OGRjYzc0NS04ZGUxLTQwYTctYTVjMy0wY2JjMzAyMWE4ODIiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiYmI1ODY4NmUtNjUzMC00YmI5LWI5MmYtNmFkZWZjNGI0OTY1IiwiaWF0IjoxNzcxMzg1MDM3LCJleHAiOjE3NzkxMjkwMDB9.xFmCUrPLz0E-OAS1HP4jhkIt49NUZMC89TKODylVSac'
headers = {'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'}
WF1_ID = 'kGn3KwIfHldiwuGW'

with open('n8n-workflows/wf1-message-handler.json') as f:
    wf = json.load(f)
all_nodes = {n['name']: n for n in wf['nodes']}

def deploy_test(test_name, nodes, connections):
    """Deploy and check if activation succeeds."""
    r = requests.post(f'{API_URL}/workflows/{WF1_ID}/deactivate', headers=headers)
    time.sleep(0.5)

    test_wf = {
        'name': 'WF1 - Message Handler',
        'nodes': nodes,
        'connections': connections,
        'settings': {'executionOrder': 'v1'}
    }

    r2 = requests.put(f'{API_URL}/workflows/{WF1_ID}', headers=headers, json=test_wf)
    if r2.status_code != 200:
        print(f'  {test_name}: PUT failed ({r2.status_code})')
        return False

    r3 = requests.post(f'{API_URL}/workflows/{WF1_ID}/activate', headers=headers)
    activated = r3.status_code == 200 and r3.json().get('active', False)

    print(f'  {test_name} ({len(nodes)} nodes): {"ACTIVATED" if activated else "FAILED - " + r3.json().get("message", "")[:100]}')
    return activated

# Test 1: Full workflow (we know activation works, but execution fails)
# So activation is not the test - we need to test execution
# Let's trigger each version and check if the execution succeeds

def deploy_and_trigger(test_name, nodes, connections):
    """Deploy, activate, trigger, check execution."""
    r = requests.post(f'{API_URL}/workflows/{WF1_ID}/deactivate', headers=headers)
    time.sleep(0.5)

    test_wf = {
        'name': 'WF1 - Message Handler',
        'nodes': nodes,
        'connections': connections,
        'settings': {'executionOrder': 'v1'}
    }

    r2 = requests.put(f'{API_URL}/workflows/{WF1_ID}', headers=headers, json=test_wf)
    if r2.status_code != 200:
        print(f'  {test_name}: PUT failed')
        return False

    r3 = requests.post(f'{API_URL}/workflows/{WF1_ID}/activate', headers=headers)
    if r3.status_code != 200:
        print(f'  {test_name}: Activation failed')
        return False

    time.sleep(1)

    # Send a test webhook
    test_update = {
        'update_id': 999999990 + int(time.time()) % 1000,
        'message': {
            'message_id': int(time.time()) % 10000,
            'from': {'id': 12345, 'is_bot': False, 'first_name': 'Test'},
            'chat': {'id': 12345, 'type': 'private'},
            'date': int(time.time()),
            'text': f'test_{test_name}'
        }
    }

    # Use the webhook path with secret - we can't send proper webhook requests
    # So we'll need the user to send a message. Instead, just check if the workflow
    # can process by looking at the last execution after a few seconds

    # Actually, just check last execution timestamp to see if new ones come in
    r4 = requests.get(f'{API_URL}/executions', headers=headers, params={
        'limit': 1, 'workflowId': WF1_ID
    })
    before = r4.json().get('data', [{}])[0].get('id', 0) if r4.json().get('data') else 0

    print(f'  {test_name} ({len(nodes)} nodes): activated OK, last exec={before}')
    return True

# Since we can't trigger the webhook ourselves (Telegram secret required),
# let's use a different approach. Let me check each Code node's jsCode for syntax issues
# that could crash the execution engine.

print("=== Checking Code nodes for potential issues ===\n")
for node in wf['nodes']:
    if node['type'] == 'n8n-nodes-base.code':
        code = node['parameters'].get('jsCode', '')
        name = node['name']

        # Check for potential issues
        issues = []
        if 'await fetch(' in code:
            issues.append('uses await fetch() - may not be available in sandbox')
        if '$env.' in code:
            issues.append('uses $env - may be undefined')
        if 'require(' in code:
            issues.append('uses require() - not available in sandbox')

        if issues:
            print(f'  ⚠️  "{name}":')
            for issue in issues:
                print(f'       {issue}')
        else:
            print(f'  ✅ "{name}": OK')

# Now let's do the incremental deploy test
print("\n=== Incremental Activation Test ===\n")

# Each test builds on the previous one
# We use the full connections from the original workflow, filtered

def filter_connections(full_connections, node_names):
    """Keep only connections between nodes in node_names set."""
    result = {}
    for src, conn in full_connections.items():
        if src not in node_names:
            continue
        new_main = []
        for output in conn.get('main', []):
            new_targets = [t for t in output if t['node'] in node_names]
            new_main.append(new_targets)
        result[src] = {'main': new_main}
    return result

tests = [
    # Test 1: Trigger + Extract + Debug
    ['Telegram Trigger', 'Extract Message Data'],
    # Test 2: + Auth
    ['Telegram Trigger', 'Extract Message Data', 'Check User Auth', 'Is Authorized?',
     'Reject Unauthorized', 'Prepare User Context'],
    # Test 3: + Claude pipeline
    ['Telegram Trigger', 'Extract Message Data', 'Check User Auth', 'Is Authorized?',
     'Reject Unauthorized', 'Prepare User Context', 'Is File Upload?',
     'Claude: Parse Intent', 'Parse Claude Response', 'Save to Context', 'Handle File Upload'],
    # Test 4: + Switch + Help + Unknown
    ['Telegram Trigger', 'Extract Message Data', 'Check User Auth', 'Is Authorized?',
     'Reject Unauthorized', 'Prepare User Context', 'Is File Upload?',
     'Claude: Parse Intent', 'Parse Claude Response', 'Save to Context', 'Handle File Upload',
     'Route by Intent', 'Handle HELP', 'Handle Unknown'],
    # Test 5: + Buy/Sell/Alert/Portfolio handlers
    ['Telegram Trigger', 'Extract Message Data', 'Check User Auth', 'Is Authorized?',
     'Reject Unauthorized', 'Prepare User Context', 'Is File Upload?',
     'Claude: Parse Intent', 'Parse Claude Response', 'Save to Context', 'Handle File Upload',
     'Route by Intent', 'Handle HELP', 'Handle Unknown',
     'Handle BUY', 'Confirm BUY', 'Handle SELL', 'Handle ALERT SET',
     'Handle PORTFOLIO', 'Format Portfolio', 'Send Portfolio'],
    # Test 6: + All remaining handlers
    ['Telegram Trigger', 'Extract Message Data', 'Check User Auth', 'Is Authorized?',
     'Reject Unauthorized', 'Prepare User Context', 'Is File Upload?',
     'Claude: Parse Intent', 'Parse Claude Response', 'Save to Context', 'Handle File Upload',
     'Route by Intent', 'Handle HELP', 'Handle Unknown',
     'Handle BUY', 'Confirm BUY', 'Handle SELL', 'Handle ALERT SET',
     'Handle PORTFOLIO', 'Format Portfolio', 'Send Portfolio',
     'Handle PREDICT', 'Handle BRIEFING',
     'Fetch Active Alerts', 'Format Alerts List', 'Send Alerts List',
     'Prepare Alert Cancel', 'Cancel Alert in DB', 'Confirm Alert Cancel',
     'Handle LOGIN', 'Handle SYNC'],
]

for i, node_names in enumerate(tests):
    nodes = [all_nodes[n] for n in node_names if n in all_nodes]
    name_set = set(node_names)
    connections = filter_connections(wf['connections'], name_set)
    deploy_test(f'Test{i+1}', nodes, connections)
    time.sleep(1)

# Restore the full workflow at the end
print("\nRestoring full workflow...")
clean = {
    'name': wf['name'],
    'nodes': wf['nodes'],
    'connections': wf['connections'],
    'settings': wf.get('settings', {})
}
requests.post(f'{API_URL}/workflows/{WF1_ID}/deactivate', headers=headers)
time.sleep(0.5)
r = requests.put(f'{API_URL}/workflows/{WF1_ID}', headers=headers, json=clean)
r2 = requests.post(f'{API_URL}/workflows/{WF1_ID}/activate', headers=headers)
print(f'Full workflow restored: PUT={r.status_code}, Activate={r2.status_code}')
