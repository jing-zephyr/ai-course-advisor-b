# -*- coding: utf-8 -*-
# AI课程顾问 真机测试电池（24例）：功能≥8 / RAG专项≥6+ / 前端体验≥4 / 部署≥2
# 用法：python test/live_test.py [base_url]   默认 http://localhost:3000
import json, sys, io, time, urllib.request, urllib.error, os, datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:3000'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'live_test_output.txt')
log = io.open(OUT, 'w', encoding='utf-8')

def w(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    log.write(s + '\n')

results = []
def record(no, scene, inp, expect, actual, passed):
    results.append((no, scene, inp, expect, actual, passed))
    w(f"[{'PASS' if passed else 'FAIL'}] {no} {scene}")

def chat(msg, history=None, sid=None, raw_body=None):
    body = raw_body if raw_body is not None else json.dumps(
        {'message': msg, 'history': history or [], 'sessionId': sid or 't-live'}, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(BASE + '/api/chat', data=body,
                                 headers={'Content-Type': 'application/json; charset=utf-8'})
    try:
        with _open(req, 90) as r:
            return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))
    except Exception as e:
        return -1, {'error': str(e)}

def _open(req, timeout):
    # 本地网络偶发断连（RemoteDisconnected/URLError），传输层错误重试一次；HTTP 错误与断言语义不变
    for attempt in range(2):
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError:
            raise
        except Exception:
            if attempt == 1:
                raise
            time.sleep(2)

def get(path, token=None):
    req = urllib.request.Request(BASE + path)
    if token:
        req.add_header('Authorization', 'Bearer ' + token)
    try:
        with _open(req, 30) as r:
            return r.status, r.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8')
    except Exception as e:
        return -1, str(e)

def post_json(path, obj):
    req = urllib.request.Request(BASE + path, data=json.dumps(obj, ensure_ascii=False).encode('utf-8'),
                                 headers={'Content-Type': 'application/json; charset=utf-8'})
    try:
        with _open(req, 30) as r:
            return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))
    except Exception as e:
        return -1, {'error': str(e)}

# 从本地 .env 读管理员口令（仅测试用，不入库）
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN_PW = ''
env_file = os.path.join(APP_DIR, '.env')
if os.path.exists(env_file):
    for line in open(env_file, encoding='utf-8'):
        if line.startswith('ADMIN_PASSWORD='):
            ADMIN_PW = line.split('=', 1)[1].strip()

w('=' * 30, 'AI课程顾问 真机测试', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'BASE =', BASE)

# ---------- 功能测试 F1-F9 ----------
s, d = chat('夏令营有哪些班型？分别什么时间？', sid='t-f1')
r = d.get('data', {}).get('reply', '')
ok = s == 200 and d.get('code') == 0 and ('北京' in r and '上海' in r and '线上' in r)
record('F1', '功能：班型咨询正常应答', '夏令营有哪些班型？分别什么时间？', '列出北京/上海/线上三班型', r[:80], ok)

s, d = chat('', sid='t-f2')
record('F2', '功能：空输入异常处理', '(空字符串)', 'HTTP400 + {code:400,message:"请输入您的问题"}', json.dumps(d, ensure_ascii=False), s == 400 and d.get('code') == 400)

s, d = chat('x' * 501, sid='t-f3')
record('F3', '功能：超长输入(501字)异常处理', 'x*501', 'HTTP400 + 提示输入过长', json.dumps(d, ensure_ascii=False), s == 400 and d.get('code') == 400)

s, d = chat('<script>alert(1)</script>；emoji😀；\'OR 1=1--', sid='t-f4')
r = d.get('data', {}).get('reply', '')
ok = s == 200 and d.get('code') == 0 and '<script>' not in json.dumps(d, ensure_ascii=False)
record('F4', '功能：特殊字符/注入字符串', '<script>alert(1)</script>；emoji😀；\'OR 1=1--', '正常应答，不执行脚本、不报错', (r[:60] or json.dumps(d, ensure_ascii=False)[:60]), ok)

s1, d1 = chat('夏令营费用是多少？', sid='t-f5')
s2, d2 = get('/api/history?sessionId=t-f5')
msgs = json.loads(d2).get('data', {}).get('messages', []) if s2 == 200 else []
ok = s1 == 200 and len(msgs) >= 2 and msgs[0]['role'] == 'user' and msgs[1]['role'] == 'assistant'
record('F5', '功能：对话记录保存', '夏令营费用是多少？(sessionId=t-f5)', '服务端保存 user+assistant 两条', f'已存{len(msgs)}条', ok)

s, d = get('/api/history?sessionId=t-f5')
record('F6', '功能：历史查询接口', 'GET /api/history?sessionId=t-f5', '{code:0,data:{messages:[...]}}', d[:80], s == 200 and json.loads(d).get('code') == 0)

s1, d1 = chat('夏令营费用是多少？', sid='t-f7')
h = [{'role': 'user', 'content': '夏令营费用是多少？'}, {'role': 'assistant', 'content': d1.get('data', {}).get('reply', '')}]
s2, d2 = chat('早鸟呢？', history=h, sid='t-f7')
r = d2.get('data', {}).get('reply', '')
ok = s2 == 200 and ('5980' in r or '早鸟' in r)
record('F7', '功能：多轮上下文（追问“早鸟呢”）', '费用→早鸟呢？', '继承夏令营语境，回答早鸟价5980/3280', r[:60], ok)

s, d = chat('我孩子今年初一，零基础，能跟上夏令营吗？', sid='t-f8')
r = d.get('data', {}).get('reply', '')
ok = s == 200 and ('零基础' in r or '无需编程' in r or '六年级' in r or '初中' in r)
record('F8', '功能：动态Prompt（家长身份+学段注入）', '我孩子初一，零基础能跟上吗？', '按家长视角+初中学段作答，引用适合对象', r[:60], ok)

s, d = get('/api/history')
record('F9', '功能：错误返回格式统一', 'GET /api/history（缺参数）', '{code:400,message:...}', d[:60], s == 400 and 'code' in json.loads(d) and 'message' in json.loads(d))

# ---------- 功能测试 F10-F14：双入口登录与观测接口鉴权 ----------
s, d = post_json('/api/login', {'role': 'user'})
user_tok = d.get('data', {}).get('token', '')
ok = s == 200 and d.get('code') == 0 and user_tok.startswith('aca.user.')
record('F10', '功能：用户入口免密登录签发令牌', 'POST /api/login {role:user}', '200 + aca.user. 前缀令牌', f'HTTP {s} token={user_tok[:22]}...', ok)

s, d = post_json('/api/login', {'role': 'admin', 'password': 'definitely-wrong-pw'})
record('F11', '功能：技术入口错误口令拒绝', 'POST /api/login 错误口令', 'HTTP401 + 口令错误提示', f"HTTP {s} {d.get('message','')}", s == 401 and d.get('code') == 401)

admin_tok = ''
if ADMIN_PW:
    s, d = post_json('/api/login', {'role': 'admin', 'password': ADMIN_PW})
    admin_tok = d.get('data', {}).get('token', '')
    ok = s == 200 and admin_tok.startswith('aca.admin.')
    record('F12', '功能：技术入口正确口令签发admin令牌', 'POST /api/login 正确口令', '200 + aca.admin. 前缀令牌', f'HTTP {s}', ok)
else:
    record('F12', '功能：技术入口正确口令签发admin令牌', '(本地 .env 未配置 ADMIN_PASSWORD)', '200 + admin令牌', '跳过', None)

s, d = get('/api/admin?action=stats')
record('F13', '功能：未授权访问管理接口被拒', 'GET /api/admin（无令牌）', 'HTTP401 + 未授权提示', f'HTTP {s}', s == 401 and json.loads(d).get('code') == 401)

if admin_tok:
    s, d = get('/api/admin?action=stats', token=admin_tok)
    j = json.loads(d)
    ok = s == 200 and j.get('data', {}).get('kb', {}).get('blocks', 0) >= 30
    record('F14', '功能：admin令牌访问观测统计', 'GET /api/admin?action=stats（带令牌）', '200 + 知识块/会话/成功率统计', f"HTTP {s} blocks={j.get('data',{}).get('kb',{}).get('blocks')}", ok)

    body = json.dumps({'message': '夏令营费用多少？', 'history': [], 'sessionId': 't-f14'}, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(BASE + '/api/chat', data=body,
                                 headers={'Content-Type': 'application/json; charset=utf-8', 'Authorization': 'Bearer ' + admin_tok})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            d = json.loads(r.read().decode('utf-8'))
        tr = d.get('data', {}).get('trace')
        ok = tr and tr.get('zone') == 'camp' and len(tr.get('hits', [])) > 0 and 'score' in tr['hits'][0]
        record('F15', '功能：admin对话返回检索过程trace', '带admin令牌提问夏令营费用', 'trace含zone=camp、命中块得分、检索词', f"zone={tr.get('zone') if tr else None} hits={len(tr.get('hits',[])) if tr else 0}", bool(ok))
    except Exception as e:
        record('F15', '功能：admin对话返回检索过程trace', '带admin令牌提问', 'trace齐全', str(e)[:50], False)
else:
    record('F14', '功能：admin令牌访问观测统计', '(无admin令牌)', '200', '跳过', None)
    record('F15', '功能：admin对话返回检索过程trace', '(无admin令牌)', 'trace齐全', '跳过', None)

# ---------- RAG 专项 R1-R7 ----------
s, d = chat('夏令营线下班多少钱？早鸟价呢？', sid='t-r1')
r = d.get('data', {}).get('reply', '')
ok = s == 200 and '6980' in r and '5980' in r
record('R1', 'RAG：直接事实-夏令营费用', '线下班多少钱？早鸟价？', '6980元/早鸟5980元，数字与素材一致', r[:60], ok)

s, d = chat('教师培训L1阶段学什么？多少课时？', sid='t-r2')
r = d.get('data', {}).get('reply', '')
ok = s == 200 and '8课时' in r and ('2天' in r)
record('R2', 'RAG：直接事实-L1课时', 'L1学什么？多少课时？', '8课时/2天，四模块', r[:60], ok)

s, d = chat('孩子开学高三，参加夏令营会不会太简单？', sid='t-r3')
r = d.get('data', {}).get('reply', '')
ok = s == 200 and ('高三' in r or '分层' in r or '混龄' in r)
record('R3', 'RAG：间接推断-适龄性', '高三参加会不会太简单？', '依据混龄分组+分层任务作答', r[:60], ok)

s, d = chat('OPC平台会员有哪几档？', sid='t-r4')
r = d.get('data', {}).get('reply', '')
ok = s == 200 and ('免费' in r and '基础' in r and '专业' in r and '大师' in r)
record('R4', 'RAG：直接事实-会员档位', '会员有哪几档？', '免费体验/基础/专业/大师 四档', r[:60], ok)

s, d = chat('夏令营和教师培训有什么区别？分别适合谁？', sid='t-r5')
r = d.get('data', {}).get('reply', '')
src = json.dumps(d.get('data', {}).get('sources', []), ensure_ascii=False)
ok = s == 200 and '素材A' in src and '素材B' in src and ('学生' in r and '教师' in r)
record('R5', 'RAG：跨区对比+双来源溯源', '夏令营和教师培训区别？', '综合素材A+B回答，两个来源均标注', (r[:50] + ' | src:' + src[:50]), ok)

s, d = chat('夏令营在马甸桥有教学点吗？', sid='t-r6')
r = d.get('data', {}).get('reply', '')
ok = s == 200 and ('超出' in r or '没有' in r or '未' in r) and '马甸桥' not in r.replace('马甸桥有教学点', '')
# 宽松判定：不得肯定回答马甸桥有班
ok = s == 200 and ('马甸桥有' not in r) and ('超出' in r or '没有' in r or '未提及' in r or '不在' in r)
record('R6', 'RAG：库外拒绝编造（虚构教学点）', '马甸桥有教学点吗？', '明确告知资料中无此信息', r[:70], ok)

s, d = chat('夏令营退费规则是什么？', sid='t-r7')
srcs = d.get('data', {}).get('sources', [])
docs = set(x.get('doc', '') for x in srcs)
ok = s == 200 and len(srcs) > 0 and all(('素材A' in x or '素材B' in x or '素材C' in x) for x in docs)
record('R7', 'RAG：引用溯源准确性', '退费规则是什么？', '返回sources且均属于三份素材', json.dumps(srcs, ensure_ascii=False)[:80], ok)

# ---------- 前端体验 FE1-FE5（静态断言 + 人工实测项） ----------
s, html = get('/')
ok = s == 200 and 'AI课程顾问' in html and '<header>' in html and 'logo' in html
record('FE1', '前端：PC页面加载与品牌区', 'GET /', '200 + 品牌Logo区', f'HTTP {s}, {len(html)}字节', ok)

need_chips = ['学生课程', '教师培训', '查看所有班型', '费用说明', '报名方式']
ok = all(c in html for c in need_chips)
record('FE2', '前端：快捷问题入口（5个）', '检查chips', '包含学生课程/教师培训/查看所有班型/费用说明/报名方式', '全部存在' if ok else '缺失', ok)

ok = '<textarea' in html and '发送' in html and 'typing' in html and 'setLoading' in html
record('FE3', '前端：输入框+发送按钮+加载状态', '检查输入区与loading', 'textarea/发送/打字动画均存在', '存在' if ok else '缺失', ok)

ok = 'viewport-fit=cover' in html and '@media (max-width: 640px)' in html and 'font-size: 16px' in html
record('FE4', '前端：移动端适配标记', '检查viewport/媒体查询/16px输入框', 'viewport-fit、640px媒体查询、输入框16px防iOS缩放', '存在' if ok else '缺失', ok)

ok = '100dvh' in html and 'SpeechRecognition' in html
record('FE5', '前端：软键盘适配(dvh)+语音输入降级', '检查100dvh与SR降级', '存在', '存在' if ok else '缺失', ok)

ok = '用户入口' in html and '技术人员入口' in html and 'gate' in html and 'adminDrawer' in html and '检索追踪' in html and '知识库状态' in html
record('FE6', '前端：登录门禁双入口+技术观测面板', '检查gate双入口与admin面板DOM', '用户/技术人员双入口、三页签面板均存在', '全部存在' if ok else '缺失', ok)

# ---------- 部署测试 D1-D3 ----------
s, html = get('/')
ok = s == 200 and len(html) > 5000
record('D1', '部署：本地一键运行（node server.js）', '启动后访问 / 与 /api/chat', '页面200且对话接口可用', f'HTTP {s}', ok)

envpath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env.example')
ok = os.path.exists(envpath)
txt = open(envpath, encoding='utf-8').read() if ok else ''
ok = ok and 'LLM_API_KEY' in txt and 'your_api_key_here' in txt
record('D2', '部署：.env.example 配置说明', '检查文件', '含LLM_API_KEY占位与注释', '符合' if ok else '不符合', ok)

is_local = BASE.startswith('http://localhost') or BASE.startswith('http://127.0.0.1')
if not is_local:
    s, d = chat('夏令营费用是多少？', sid='t-d3')
    ok = s == 200 and d.get('code') == 0
    record('D3', '部署：公网链接对话可用', '公网/api/chat', '200 + code:0', f'HTTP {s}', ok)
else:
    record('D3', '部署：公网链接可访问性', '见部署测试记录', '公网URL返回200', '本地模式跳过，部署后补测', None)

# ---------- 汇总 ----------
w('\n' + '=' * 30, '汇总')
passed = sum(1 for r in results if r[5] is True)
failed = sum(1 for r in results if r[5] is False)
skipped = sum(1 for r in results if r[5] is None)
w(f'通过 {passed} / 失败 {failed} / 跳过 {skipped} / 总计 {len(results)}')
w('\n明细（测试记录表素材）：')
for no, scene, inp, expect, actual, p in results:
    mark = '通过' if p is True else ('未通过' if p is False else '跳过')
    w(f'{no}\t{scene}\t输入={inp[:40]}\t预期={expect[:40]}\t实际={str(actual)[:60]}\t{mark}')
log.close()
print('\n完整输出已写入:', OUT)
