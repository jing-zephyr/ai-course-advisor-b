const { retrieve, route } = require('./retrieval');
const { buildSystemPrompt, detectRole } = require('./prompt');
const store = require('./store');
const auth = require('./auth');
const kb = require('../data/knowledge.json');

const MAX_LEN = 500;
// 统一返回格式：成功 {code:0, message:'ok', data:{...}}；失败 {code:HTTP状态码, message:'...'}
const MSG = {
  empty: '请输入您的问题',
  long: '输入内容过长，请精简后重试',
  busy: '服务繁忙',
  noSession: '会话不存在',
};

function ok(data) {
  return { status: 200, body: { code: 0, message: 'ok', data } };
}
function fail(status, message) {
  return { status, body: { code: status, message } };
}

function cleanHistory(h) {
  if (!Array.isArray(h)) return [];
  return h
    .filter((m) => m && (m.role === 'user' || m.role === 'assistant') && typeof m.content === 'string')
    .slice(-8)
    .map((m) => ({ role: m.role, content: m.content.slice(0, 500) }));
}

async function callLLM(messages) {
  const base = process.env.LLM_BASE_URL || 'https://api.deepseek.com/v1';
  const model = process.env.LLM_MODEL || 'deepseek-chat';
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 25000);
  try {
    const res = await fetch(base + '/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer ' + process.env.LLM_API_KEY,
      },
      body: JSON.stringify({ model, messages, temperature: 0.3, max_tokens: 1500 }),
      signal: ctrl.signal,
    });
    if (!res.ok) throw new Error('llm_http_' + res.status);
    const data = await res.json();
    return data.choices[0].message.content;
  } finally {
    clearTimeout(timer);
  }
}

async function handleChat(input, authInfo) {
  const msg = ((input && input.message) || '').trim();
  if (!msg) return fail(400, MSG.empty);
  if (msg.length > MAX_LEN) return fail(400, MSG.long);
  if (!process.env.LLM_API_KEY) return fail(503, MSG.busy);

  const history = cleanHistory(input.history);
  const sessionId = typeof input.sessionId === 'string' ? input.sessionId.slice(0, 64) : '';
  const lastUser = [...history].reverse().find((m) => m.role === 'user');
  // 本条消息意图明确时只按本条路由；意图不明（短句追问）才融合上一条用户消息，
  // 避免历史里的主题词污染新一轮提问的检索范围
  const contextQuery = route(msg) !== 'all' ? msg : msg.length < 12 && lastUser ? lastUser.content + ' ' + msg : msg;

  const t0 = Date.now();
  const { chunks, trace } = retrieve(contextQuery, 5);
  // 动态 System Prompt 注入：结合本条消息与历史识别用户身份（学段/角色）
  const roleHint = detectRole(msg + ' ' + history.filter((m) => m.role === 'user').map((m) => m.content).join(' '));
  const messages = [
    { role: 'system', content: buildSystemPrompt(chunks, roleHint) },
    ...history,
    { role: 'user', content: msg },
  ];

  try {
    let reply = await callLLM(messages);
    reply = reply
      .split('\n')
      .filter((l) => !/^\s*-{3,}\s*$/.test(l))
      .join('\n')
      .replace(/\n{3,}/g, '\n\n')
      .trim();
    const seen = new Set();
    const sources = chunks
      .map((c) => ({ doc: c.doc, chapter: c.chapter, title: c.title }))
      .filter((s) => {
        const k = s.doc + s.chapter;
        if (seen.has(k)) return false;
        seen.add(k);
        return true;
      });
    if (sessionId) {
      store.appendMessages(sessionId, [
        { role: 'user', content: msg },
        { role: 'assistant', content: reply },
      ]);
    }
    store.appendLog({ sessionId, zone: trace.zone, ms: Date.now() - t0, ok: true, msg });
    const data = { reply, sources, sessionId: sessionId || null };
    // 检索过程回放：仅技术人员角色返回 trace（观测面板），普通用户响应不变
    if (authInfo && authInfo.role === 'admin') {
      data.trace = { ...trace, roleHint, totalMs: Date.now() - t0, model: process.env.LLM_MODEL || 'deepseek-chat' };
    }
    return ok(data);
  } catch (e) {
    store.appendLog({ sessionId, zone: trace.zone, ms: Date.now() - t0, ok: false, msg });
    return fail(500, MSG.busy);
  }
}

function handleLogin(input) {
  const role = input && input.role;
  const r = auth.login(role, input && input.password);
  if (!r.ok) return fail(r.status, r.message);
  return ok({ token: r.token, role: r.role, expiresIn: 12 * 3600 });
}

// 管理端只读接口：全部要求 admin 令牌，不验权一律 401
function handleAdmin(action, authInfo) {
  if (!authInfo || authInfo.role !== 'admin') return fail(401, '未授权：请从技术人员入口登录');
  if (action === 'stats') {
    const zones = {};
    const docs = new Set();
    for (const b of kb.blocks) {
      zones[b.zone] = (zones[b.zone] || 0) + 1;
      docs.add(b.doc);
    }
    const sessions = store.listSessions();
    const logs = store.listLogs(200);
    const okCount = logs.filter((l) => l.ok).length;
    return ok({
      kb: { blocks: kb.blocks.length, zones, docs: docs.size },
      sessions: { total: sessions.length, messages: sessions.reduce((a, s) => a + s.count, 0) },
      logs: { kept: logs.length, okRate: logs.length ? Math.round((okCount / logs.length) * 100) : null },
      model: process.env.LLM_MODEL || 'deepseek-chat',
      time: Date.now(),
    });
  }
  if (action === 'sessions') return ok({ sessions: store.listSessions().slice(0, 50) });
  if (action === 'logs') return ok({ logs: store.listLogs(50) });
  if (action === 'knowledge') {
    return ok({
      blocks: kb.blocks.map((b) => ({ id: b.id, zone: b.zone, doc: b.doc, chapter: b.chapter, title: b.title, keywords: b.keywords })),
    });
  }
  return fail(400, '未知的管理操作');
}

function handleHistory(sessionId) {
  if (!sessionId) return fail(400, '缺少 sessionId 参数');
  const sess = store.getSession(sessionId);
  if (!sess) return fail(404, MSG.noSession);
  return ok(sess);
}

module.exports = { handleChat, handleHistory, handleLogin, handleAdmin, MSG, MAX_LEN };
