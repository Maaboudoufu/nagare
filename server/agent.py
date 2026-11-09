"""Runs inside a user's workspace container: grades code and CLI lessons there, so they never touch the server.
The worker keeps one of these per workspace (docker exec -i) and talks JSON lines over stdin/stdout, which saves
starting a process per request."""
import json, os, sys, traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grader

for line in sys.stdin:
    try:
        req = json.loads(line)
        if req['op'] == 'run':
            res = grader.run(req['lesson'], req['code'], req['submit'])
        elif not os.path.isdir(req['dir']):  # op == 'cli'
            res = {'error': f"Folder not found in your workspace: {req['dir']}"}
        else:
            res = grader.run_cli(req['steps'], req['dir'], req['baseURL'])
    except Exception:
        res = {'error': traceback.format_exc(limit=3)}
    sys.stdout.write(json.dumps(res) + '\n')
    sys.stdout.flush()
