# -*- coding: utf-8 -*-
# 经 Git Data API 推送 B级测试单代码到 GitHub（需先刷新 github-trae.txt 令牌）
# 安全约束（公开仓库边界）：白名单制——只推源码+README+架构/测试/AI标注/演示说明+知识库；
# 绝不推 .env / sessions.json / 过程记录 / 草稿 / 任务素材；推送前对每个文件做密钥模式扫描。
import base64
import json
import os
import sys
import urllib.request
import urllib.error

TOKEN = open(r'C:\Users\T\Desktop\20260822OPC order\github-trae.txt', encoding='utf-8').read().strip()
APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(APP))  # 测试单根目录（04_交付文档/02_知识库所在层）
REPO = 'ai-course-advisor-b'
MSG = '四入口角色登录（用户/教师/企业免密+管理口令）+ 角色化主题与提示词三层注入 + 移动端紧凑适配（入口卡减半/表单吸附/防iOS缩放）；37例真机测试公网全量复测通过'

FILES = ['public/index.html', 'public/_redirects', 'api/chat.js', 'api/history.js',
         'api/login.js', 'api/admin.js',
         'lib/handler.js', 'lib/prompt.js', 'lib/retrieval.js', 'lib/store.js', 'lib/auth.js',
         'data/knowledge.json', 'netlify/functions/api.js', 'netlify/functions/chat.js',
         'netlify/functions/history.js', 'netlify/functions/login.js', 'netlify/functions/admin.js',
         'server.js', 'package.json', 'netlify.toml', '.env.example', '.gitignore', 'README.md',
         'test/smoke.js', 'test/live_test.py', 'test/live_test_output.txt',
         'test/deploy_netlify.py', 'test/deploy_vercel.py', 'test/export_kb_view.py',
         'test/build_submit_zip.py', 'test/check_sessions_privacy.py', 'test/push_github.py']
# 交付文档（本地绝对路径 → 仓库路径）：架构说明/测试记录/AI辅助标注/演示说明/知识库视图
DOCS = [
    (r'04_交付文档\系统架构说明.md', 'docs/系统架构说明.md'),
    (r'04_交付文档\测试记录表.md', 'docs/测试记录表.md'),
    (r'04_交付文档\AI辅助开发标注.md', 'docs/AI辅助开发标注.md'),
    (r'04_交付文档\演示说明.md', 'docs/演示说明.md'),
    (r'02_知识库\结构化知识库_36块.md', 'docs/结构化知识库_36块.md'),
]
NEVER = ['.env', 'data/sessions.json', 'data/logs.json']  # 明文密钥与运行时数据，禁止外传
SECRET_PATTERNS = [b'nfp_', b'ghp_', b'github_pat_', b'sk-']  # 常见令牌前缀，命中即中止


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

sources = [(os.path.join(APP, rel.replace('/', os.sep)), rel) for rel in FILES]
sources += [(os.path.join(ROOT, loc), repo) for loc, repo in DOCS]

entries = []
for local, rel in sources:
    assert rel not in NEVER, rel
    raw = open(local, 'rb').read()
    if rel != 'test/push_github.py':  # 本脚本含模式定义字符串而非真实密钥，跳过自检
        for pat in SECRET_PATTERNS:
            assert pat not in raw, f'疑似密钥命中 {pat!r}：{rel}，已中止推送'
    blob = api('POST', base + '/git/blobs',
               {'content': base64.b64encode(raw).decode('ascii'), 'encoding': 'base64'})
    entries.append({'path': rel, 'mode': '100644', 'type': 'blob', 'sha': blob['sha']})
    print('blob', rel, len(raw))

tree = api('POST', base + '/git/trees', {'base_tree': base_tree, 'tree': entries})
commit = api('POST', base + '/git/commits', {'message': MSG, 'tree': tree['sha'], 'parents': [head]})
api('PATCH', base + '/git/refs/heads/main', {'sha': commit['sha'], 'force': False})
print('pushed', commit['sha'][:8], f'https://github.com/{OWNER}/{REPO}')
