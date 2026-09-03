# -*- coding: utf-8 -*-
# 经 Git Data API 推送 B级测试单代码到 GitHub（需先刷新 github-trae.txt 令牌）
# 安全约束：不推 .env / sessions.json / 任何含密钥文件
import base64
import json
import os
import sys
import urllib.request
import urllib.error

TOKEN = open(r'C:\Users\T\Desktop\20260822OPC order\github-trae.txt', encoding='utf-8').read().strip()
APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = 'ai-course-advisor-b'
MSG = '增强：双入口登录 + 技术观测面板；Serverless 函数合并为统一 api 入口（修复容器隔离导致的会话丢失），公网31例测试全过'

FILES = ['public/index.html', 'public/_redirects', 'api/chat.js', 'api/history.js',
         'api/login.js', 'api/admin.js',
         'lib/handler.js', 'lib/prompt.js', 'lib/retrieval.js', 'lib/store.js', 'lib/auth.js',
         'data/knowledge.json', 'netlify/functions/api.js', 'netlify/functions/chat.js',
         'netlify/functions/history.js', 'netlify/functions/login.js', 'netlify/functions/admin.js',
         'server.js', 'package.json', 'netlify.toml', '.env.example', '.gitignore', 'README.md',
         'test/smoke.js', 'test/live_test.py', 'test/live_test_output.txt',
         'test/deploy_netlify.py', 'test/deploy_vercel.py', 'test/export_kb_view.py', 'test/push_github.py']
NEVER = ['.env', 'data/sessions.json', 'data/logs.json']  # 明文密钥与运行时数据，禁止外传


import http.client
import time


def api(method, url, payload=None):
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(
                url, method=method,
                headers={'Authorization': 'Bearer ' + TOKEN, 'User-Agent': 'trae',
                         'Accept': 'application/vnd.github+json', 'Content-Type': 'application/json'},
                data=json.dumps(payload).encode('utf-8') if payload is not None else None)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode('utf-8'))
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError) as e:
            last = e
            print(f'  retry {attempt + 1}/5: {type(e).__name__}')
            time.sleep(3 * (attempt + 1))
    raise last


me = api('GET', 'https://api.github.com/user')
OWNER = me['login']
print('owner:', OWNER)

try:
    api('GET', f'https://api.github.com/repos/{OWNER}/{REPO}')
    print('repo exists')
except urllib.error.HTTPError:
    api('POST', 'https://api.github.com/user/repos',
        {'name': REPO, 'private': False, 'auto_init': True,
         'description': 'OPC接单吧·软件与智能体赛道B级测试单：AI课程顾问 Web 应用'})
    print('repo created')

base = f'https://api.github.com/repos/{OWNER}/{REPO}'
head = api('GET', base + '/git/ref/heads/main')['object']['sha']
base_tree = api('GET', base + '/git/commits/' + head)['tree']['sha']

entries = []
for rel in FILES:
    assert rel not in NEVER, rel
    local = os.path.join(APP, rel.replace('/', os.sep))
    raw = open(local, 'rb').read()
    blob = api('POST', base + '/git/blobs',
               {'content': base64.b64encode(raw).decode('ascii'), 'encoding': 'base64'})
    entries.append({'path': rel, 'mode': '100644', 'type': 'blob', 'sha': blob['sha']})
    print('blob', rel, len(raw))

tree = api('POST', base + '/git/trees', {'base_tree': base_tree, 'tree': entries})
commit = api('POST', base + '/git/commits', {'message': MSG, 'tree': tree['sha'], 'parents': [head]})
api('PATCH', base + '/git/refs/heads/main', {'sha': commit['sha'], 'force': False})
print('pushed', commit['sha'][:8], f'https://github.com/{OWNER}/{REPO}')
