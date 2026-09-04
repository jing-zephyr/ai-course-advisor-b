// 与 server.js 同款 .env 装载：配置过密钥时联网断言一并执行，未配置则自动跳过
const fs = require('fs');
const path = require('path');
const envPath = path.join(__dirname, '..', '.env');
if (fs.existsSync(envPath)) {
  for (const line of fs.readFileSync(envPath, 'utf-8').split('\n')) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.+)\s*$/);
    if (m && !process.env[m[1]]) process.env[m[1]] = m[2];
  }
}
process.env.ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'smoke-test-admin-pw';
const kb = require('../data/knowledge.json');
const { retrieve, route } = require('../lib/retrieval');
const { handleChat, handleHistory, handleLogin, handleAdmin, MSG } = require('../lib/handler');
const { verify } = require('../lib/auth');
const { buildSystemPrompt, entryHint } = require('../lib/prompt');

let pass = 0, fail = 0;
function check(name, cond) {
  if (cond) { pass++; console.log('PASS  ' + name); }
  else { fail++; console.log('FAIL  ' + name); }
}

check('知识库三区结构完整', Array.isArray(kb.blocks) && kb.blocks.length >= 30);
const zones = {};
kb.blocks.forEach((b) => (zones[b.zone] = (zones[b.zone] || 0) + 1));
check('三区均有内容（camp/teacher/platform）', zones.camp >= 8 && zones.teacher >= 8 && zones.platform >= 8);
const ids = new Set(kb.blocks.map((b) => b.id));
check('知识块ID唯一', ids.size === kb.blocks.length);
check('每块均带来源标签', kb.blocks.every((b) => b.doc && b.chapter && b.title && b.content && Array.isArray(b.keywords)));

check('夏令营问题路由到camp', route('夏令营适合什么学生？') === 'camp');
check('教师培训问题路由到teacher', route('教师培训L2阶段学什么？') === 'teacher');
check('会员价格问题路由到platform', route('OPC平台会员多少钱？') === 'platform');
check('跨区对比问题路由到all', route('你们有哪些课程？') === 'all');

const r1 = retrieve('夏令营费用多少？有早鸟优惠吗？');
check('费用问题命中A6（费用说明）', r1.chunks.some((c) => c.id === 'A6'));
const r2 = retrieve('教师培训L1学什么？');
check('L1问题命中B3', r2.chunks.some((c) => c.id === 'B3'));
const r3 = retrieve('平台有哪些会员档位？');
check('会员档位命中C8', r3.chunks.some((c) => c.id === 'C8'));
const r4 = retrieve('怎么报名夏令营？');
check('报名问题命中A10', r4.chunks.some((c) => c.id === 'A10'));
check('检索返回trace（zone/hits/score齐全）', r4.trace && r4.trace.zone === 'camp' && r4.trace.hits.length > 0 && typeof r4.trace.hits[0].score === 'number');

// —— 鉴权与观测接口 ——
const l1 = handleLogin({ role: 'user' });
check('用户入口免密签发令牌', l1.status === 200 && /^aca\.user\.\d+\.[0-9a-f]{32}$/.test(l1.body.data.token));
check('用户令牌可校验', verify(l1.body.data.token) && verify(l1.body.data.token).role === 'user');
const lt = handleLogin({ role: 'teacher' });
check('教师入口免密签发teacher令牌', lt.status === 200 && /^aca\.teacher\./.test(lt.body.data.token) && verify(lt.body.data.token).role === 'teacher');
const lb = handleLogin({ role: 'biz' });
check('企业入口免密签发biz令牌', lb.status === 200 && /^aca\.biz\./.test(lb.body.data.token) && verify(lb.body.data.token).role === 'biz');
const lx = handleLogin({ role: 'nobody' });
check('未知角色登录返回400', lx.status === 400 && lx.body.code === 400);
const l2 = handleLogin({ role: 'admin', password: 'wrong-pw' });
check('技术入口错误口令返回401', l2.status === 401 && l2.body.code === 401);
const l3 = handleLogin({ role: 'admin', password: process.env.ADMIN_PASSWORD });
check('技术入口正确口令签发admin令牌', l3.status === 200 && /^aca\.admin\./.test(l3.body.data.token));
check('篡改令牌被拒绝', verify(l1.body.data.token.replace(/.$/, c => c === '0' ? '1' : '0')) === null);
const a1 = handleAdmin('stats', null);
check('未带令牌访问管理接口返回401', a1.status === 401 && a1.body.code === 401);
const a2 = handleAdmin('stats', { role: 'user' });
check('user角色访问管理接口返回401', a2.status === 401);
check('teacher角色访问管理接口返回401', handleAdmin('stats', { role: 'teacher' }).status === 401);
check('biz角色访问管理接口返回401', handleAdmin('sessions', { role: 'biz' }).status === 401);

// —— 入口角色基调注入（会话级提示词差异化） ——
check('user入口基调含学生/家长视角', entryHint('user').includes('用户入口') && entryHint('user').includes('家长'));
check('teacher入口基调含教师视角', entryHint('teacher').includes('教师入口'));
check('biz入口基调含企业视角', entryHint('biz').includes('企业'));
check('admin无入口基调（不污染技术观测）', entryHint('admin') === null);
const sp1 = buildSystemPrompt([], null, entryHint('teacher'));
check('系统提示词含会话级入口注入段', sp1.includes('入口身份基调') && sp1.includes('教师入口'));
const sp2 = buildSystemPrompt([], null, null);
check('无入口时系统提示词不含入口注入段', !sp2.includes('入口身份基调'));
const a3 = handleAdmin('stats', { role: 'admin' });
check('admin令牌访问stats返回知识库/会话统计', a3.status === 200 && a3.body.data.kb.blocks >= 30);
const a4 = handleAdmin('knowledge', { role: 'admin' });
check('admin可拉取知识库清单', a4.status === 200 && a4.body.data.blocks.length === kb.blocks.length);

(async () => {
  const g1 = await handleChat({ message: '' });
  check('空输入返回统一错误格式', g1.status === 400 && g1.body.code === 400 && g1.body.message === MSG.empty);
  const g2 = await handleChat({ message: 'x'.repeat(501) });
  check('超长输入返回统一错误格式', g2.status === 400 && g2.body.code === 400 && g2.body.message === MSG.long);
  const g3 = await handleChat({ message: '夏令营班型有哪些', sessionId: 'smoke-test' });
  if (process.env.LLM_API_KEY) {
    check('有Key时正常应答且带source与会话ID', g3.status === 200 && g3.body.code === 0 && g3.body.data.reply && g3.body.data.sessionId === 'smoke-test');
    const g4 = await handleChat({ message: '夏令营费用多少', sessionId: 'smoke-test' }, { role: 'admin' });
    check('admin角色对话返回检索trace', g4.status === 200 && g4.body.data.trace && g4.body.data.trace.hits.length > 0);
    const g5 = await handleChat({ message: '夏令营费用多少', sessionId: 'smoke-test' });
    check('普通用户对话不返回trace', g5.status === 200 && !g5.body.data.trace);
  } else {
    check('无Key时优雅降级', g3.status === 503 && g3.body.code === 503 && g3.body.message === MSG.busy);
  }
  const h1 = handleHistory('smoke-test');
  if (process.env.LLM_API_KEY && g3.status === 200) {
    check('历史接口可查询已存会话', h1.status === 200 && h1.body.data.messages.length >= 2);
  }
  const h2 = handleHistory('not-exist-session');
  check('不存在会话返回404统一格式', h2.status === 404 && h2.body.code === 404);
  console.log('\n结果：' + pass + ' 通过 / ' + fail + ' 失败');
  process.exit(fail ? 1 : 0);
})();
