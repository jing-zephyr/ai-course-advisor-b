const kb = require('../data/knowledge.json');
const { retrieve, route } = require('../lib/retrieval');
const { handleChat, handleHistory, MSG } = require('../lib/handler');

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

(async () => {
  const g1 = await handleChat({ message: '' });
  check('空输入返回统一错误格式', g1.status === 400 && g1.body.code === 400 && g1.body.message === MSG.empty);
  const g2 = await handleChat({ message: 'x'.repeat(501) });
  check('超长输入返回统一错误格式', g2.status === 400 && g2.body.code === 400 && g2.body.message === MSG.long);
  const g3 = await handleChat({ message: '夏令营班型有哪些', sessionId: 'smoke-test' });
  if (process.env.LLM_API_KEY) {
    check('有Key时正常应答且带source与会话ID', g3.status === 200 && g3.body.code === 0 && g3.body.data.reply && g3.body.data.sessionId === 'smoke-test');
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
