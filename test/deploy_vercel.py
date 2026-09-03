# -*- coding: utf-8 -*-
# Vercel 一键部署：创建项目 -> 注入环境变量 -> 文件清单部署 -> 轮询就绪
import hashlib, json, os, sys, time, urllib.request, urllib.error

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = open(r'C:\Users\T\Desktop\20260822OPC order\vercel-trae.txt', encoding='utf-8').read().strip()
PROJECT_NAME = 'ai-course-advisor-b' + str(int(time.time()))[-6:]

FILES = ['public/index.html', 'api/chat.js', 'api/history.js', 'lib/handler.js', 'lib/prompt.js',
         'lib/retrieval.js', 'lib/store.js', 'data/knowledge.json', 'package.json']

def env_vars():
    out = {}
    with open(os.path.join(APP, '.env'), encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                out[k.strip()] = v.strip()
    return out

def api(method, url, data=None, headers=None):
    h = {'Authorization': 'Bearer ' + TOKEN, 'User-Agent': 'trae'}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))

# 1. 创建项目
try:
    proj = api('POST', 'https://api.vercel.com/v10/projects',
               data=json.dumps({'name': PROJECT_NAME}).encode(), headers={'Content-Type': 'application/json'})
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print('create project resp:', body[:300])
    proj = api('GET', f'https://api.vercel.com/v9/projects/{PROJECT_NAME}')
PID = proj['id']
print('project:', PID, PROJECT_NAME)

# 2. 注入环境变量（生产环境）
for k, v in env_vars().items():
    try:
        api('POST', f'https://api.vercel.com/v10/projects/{PID}/env',
            data=json.dumps({'key': k, 'value': v, 'target': ['production'], 'type': 'encrypted'}).encode(),
            headers={'Content-Type': 'application/json'})
        print('env set:', k)
    except urllib.error.HTTPError as e:
        print('env failed:', k, e.read().decode()[:200])

# 3. 文件清单部署
manifest = []
for rel in FILES:
    raw = open(os.path.join(APP, rel.replace('/', os.sep)), 'rb').read()
    manifest.append({'file': rel, 'sha': hashlib.sha1(raw).hexdigest(), 'size': len(raw)})

def create():
    return api('POST', 'https://api.vercel.com/v13/deployments?forceNew=1', headers={'Content-Type': 'application/json'},
               data=json.dumps({'name': PROJECT_NAME, 'project': PID,
                                'target': 'production', 'files': manifest}).encode('utf-8'))

try:
    dep = create()
except urllib.error.HTTPError as e:
    body = json.loads(e.read().decode('utf-8'))
    missing = (body.get('error') or {}).get('missing') or body.get('missing') or []
    if not missing:
        print('CREATE ERROR:', json.dumps(body)[:600]); sys.exit(1)
    by_sha = {m['sha']: m['file'] for m in manifest}
    for sha in missing:
        rel = by_sha[sha]
        raw = open(os.path.join(APP, rel.replace('/', os.sep)), 'rb').read()
        api('POST', 'https://api.vercel.com/v2/files', data=raw,
            headers={'Content-Type': 'application/octet-stream', 'x-vercel-digest': sha})
        print('uploaded', rel)
    dep = create()

print('deployment:', dep.get('url'), dep.get('readyState'))
for _ in range(40):
    time.sleep(3)
    st = api('GET', f'https://api.vercel.com/v13/deployments/{dep["id"]}')
    state = st.get('readyState')
    print('state:', state)
    if state == 'READY':
        for a in (st.get('alias') or []):
            print('alias:', a)
        aliases = st.get('alias') or []
        if aliases:
            with open(os.path.join(APP, 'deploy_vercel_url.txt'), 'w', encoding='utf-8') as f:
                f.write('https://' + aliases[0])
        sys.exit(0)
    if state in ('ERROR', 'CANCELED'):
        print('DEPLOY ERROR:', json.dumps(st)[:600]); sys.exit(1)
print('timeout'); sys.exit(1)
