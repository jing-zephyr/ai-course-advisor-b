// 统一 API 入口：/api/chat /api/login /api/history /api/admin 全部路由到本函数。
// 为什么合并：Netlify 各 Function 运行在相互隔离的 Lambda 容器，进程内存与 /tmp 互不共享，
// 拆成 4 个函数时 chat 写入的会话在 history 里读不到（公网实测用例 F5/F6 失败）。
// 合并为单函数后，同实例内共享 store 的内存层，观测面板统计数据口径一致。
const { handleChat, handleHistory, handleLogin, handleAdmin } = require('../../lib/handler');
const { tokenFrom } = require('../../lib/auth');

const JSON_H = { 'Content-Type': 'application/json; charset=utf-8' };

function parseBody(event) {
  try {
    return JSON.parse(event.body || '{}');
  } catch {
    return {};
  }
}

exports.handler = async (event) => {
  // 经 _redirects 重写后 event.path 前缀不确定，统一取叶子段路由
  const seg = (event.path || '').split('/').filter(Boolean).pop();
  const method = event.httpMethod;
  const qs = event.queryStringParameters || {};
  let r;
  if (seg === 'chat' && method === 'POST') {
    r = await handleChat(parseBody(event), tokenFrom(event.headers || {}));
  } else if (seg === 'login' && method === 'POST') {
    r = handleLogin(parseBody(event));
  } else if (seg === 'history' && method === 'GET') {
    r = handleHistory(qs.sessionId);
  } else if (seg === 'admin' && method === 'GET') {
    r = handleAdmin(qs.action || 'stats', tokenFrom(event.headers || {}));
  } else if (['chat', 'login', 'history', 'admin'].includes(seg)) {
    r = { status: 405, body: { code: 405, message: 'Method Not Allowed' } };
  } else {
    r = { status: 404, body: { code: 404, message: 'Not Found' } };
  }
  return { statusCode: r.status, headers: JSON_H, body: JSON.stringify(r.body) };
};
