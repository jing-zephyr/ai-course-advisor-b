# -*- coding: utf-8 -*-
# Netlify 一键部署：创建/复用站点 -> 注入环境变量 -> digest 部署（静态页 + 2个函数）-> 轮询就绪
import hashlib, http.client, io, json, os, sys, time, urllib.request, urllib.error, zipfile

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = open(r'C:\Users\T\Desktop\20260822OPC order\netlify-trae.txt', encoding='utf-8').read().strip()
SITE_NAME = 'ai-course-advisor-b' + str(int(time.time()))[-6:]


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
    h = {'Authorization': 'Bearer ' + TOKEN}
    if headers:
        h.update(headers)
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, data=data, method=method, headers=h)
            with urllib.request.urlopen(req, timeout=90) as r:
                raw = r.read().decode('utf-8')
                return json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as e:
            if e.code < 500:
                raise
            last = e
            print(f'  retry {attempt + 1}/4: HTTP {e.code}')
            time.sleep(3 * (attempt + 1))
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError) as e:
            last = e
            print(f'  retry {attempt + 1}/4: {type(e).__name__}')
            time.sleep(3 * (attempt + 1))
    raise last


# 1. 创建站点（已建则复用，断点续跑）
SITE_FILE = os.path.join(APP, 'test', '.netlify_site_id')
if os.path.exists(SITE_FILE):
    SITE_ID = open(SITE_FILE, encoding='utf-8').read().strip()
    site = api('GET', f'https://api.netlify.com/api/v1/sites/{SITE_ID}')
    print('reuse site:', SITE_ID, site.get('ssl_url'))
else:
    try:
        site = api('POST', 'https://api.netlify.com/api/v1/sites',
                   data=json.dumps({'name': SITE_NAME}).encode(), headers={'Content-Type': 'application/json'})
    except urllib.error.HTTPError as e:
        print('create site failed:', e.read().decode()[:300]); sys.exit(1)
    SITE_ID = site['id']
    with open(SITE_FILE, 'w', encoding='utf-8') as f:
        f.write(SITE_ID)
    print('site:', SITE_ID, site.get('ssl_url'))

# 2. 注入环境变量（数组格式；免费账号不带 scopes；逐key upsert：存在则 PUT 更新，保证新增 key 不被整体 409 跳过）
acct = api('GET', 'https://api.netlify.com/api/v1/accounts')[0]['id']
for k, v in env_vars().items():
    payload = [{'key': k, 'values': [{'value': v, 'context': 'all'}]}]
    try:
        api('POST', f'https://api.netlify.com/api/v1/accounts/{acct}/env?site_id={SITE_ID}',
            data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
        print('env set:', k)
    except urllib.error.HTTPError as e:
        if e.code in (409, 422):
            # 该账号 PATCH/PUT 更新均被拒（422/400），改为 DELETE + POST 重建
            api('DELETE', f'https://api.netlify.com/api/v1/accounts/{acct}/env/{k}?site_id={SITE_ID}')
            api('POST', f'https://api.netlify.com/api/v1/accounts/{acct}/env?site_id={SITE_ID}',
                data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
            print('env rebuilt:', k)
        else:
            print('env failed:', k, e.read().decode()[:300]); sys.exit(1)

# 3. 单函数打包：/api/* 统一由 api.js 承载（多函数容器隔离会导致会话跨函数丢失）
LIB_FILES = ['netlify/functions/api.js',
             'lib/handler.js', 'lib/prompt.js', 'lib/retrieval.js', 'lib/store.js', 'lib/auth.js',
             'data/knowledge.json']


def build_bundle(name):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr(f'{name}.js', f"module.exports = require('./netlify/functions/{name}.js')\n")
        for rel in LIB_FILES:
            z.write(os.path.join(APP, rel.replace('/', os.sep)), rel)
    return buf.getvalue()


bundles = {name: build_bundle(name) for name in ['api']}
fn_shas = {name: hashlib.sha256(b).hexdigest() for name, b in bundles.items()}

# 4. 文件清单（sha1）；_redirects 一并上传，否则 /api/* 重定向不生效
DISK = {'index.html': os.path.join(APP, 'public', 'index.html'),
        '_redirects': os.path.join(APP, 'public', '_redirects')}
files = {}
for rel, disk in DISK.items():
    with open(disk, 'rb') as f:
        files[rel] = hashlib.sha1(f.read()).hexdigest()

dep = api('POST', f'https://api.netlify.com/api/v1/sites/{SITE_ID}/deploys',
          data=json.dumps({'files': files, 'functions': fn_shas, 'async': True}).encode(),
          headers={'Content-Type': 'application/json'})
dep_id = dep['id']
print('deploy id:', dep_id)

time.sleep(2)
dep = api('GET', f'https://api.netlify.com/api/v1/deploys/{dep_id}')
print('required:', dep.get('required'), 'required_functions:', dep.get('required_functions'))
sha_to_path = {v: k for k, v in files.items()}
for sha in dep.get('required', []):
    rel = sha_to_path[sha]
    with open(DISK[rel], 'rb') as f:
        api('PUT', f'https://api.netlify.com/api/v1/deploys/{dep_id}/files/{rel}',
            data=f.read(), headers={'Content-Type': 'application/octet-stream'})
    print('uploaded file:', rel)

if dep.get('required_functions'):
    for name in ['api']:
        api('PUT', f'https://api.netlify.com/api/v1/deploys/{dep_id}/functions/{name}?runtime=js',
            data=bundles[name], headers={'Content-Type': 'application/octet-stream'})
        print('uploaded function:', name)

for _ in range(60):
    time.sleep(3)
    st = api('GET', f'https://api.netlify.com/api/v1/deploys/{dep_id}')
    state = st.get('state')
    print('state:', state)
    if state in ('ready', 'prepared'):
        url = st.get('ssl_url') or st.get('url')
        print('DEPLOY OK:', url)
        with open(os.path.join(APP, 'deploy_netlify_url.txt'), 'w', encoding='utf-8') as f:
            f.write(url)
        sys.exit(0)
    if state == 'error':
        print('DEPLOY ERROR:', json.dumps(st)[:800]); sys.exit(1)
print('timeout'); sys.exit(1)
