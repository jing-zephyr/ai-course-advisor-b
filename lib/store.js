const fs = require('fs');
const path = require('path');
const os = require('os');

// 会话持久化：本地运行写入 data/sessions.json；
// Serverless（Netlify/Vercel）文件系统只读时自动降级到 tmpdir，接口行为保持一致
function resolveFile() {
  const local = path.join(__dirname, '..', 'data', 'sessions.json');
  try {
    fs.accessSync(path.dirname(local), fs.constants.W_OK);
    return local;
  } catch {
    return path.join(os.tmpdir(), 'ai-course-advisor-sessions.json');
  }
}

const FILE = resolveFile();
const MAX_SESSIONS = 200;
const MAX_MSG_PER_SESSION = 100;

function loadAll() {
  try {
    return JSON.parse(fs.readFileSync(FILE, 'utf-8'));
  } catch {
    return {};
  }
}

function saveAll(data) {
  const ids = Object.keys(data);
  if (ids.length > MAX_SESSIONS) {
    const sorted = ids.sort((a, b) => (data[a].updatedAt || 0) - (data[b].updatedAt || 0));
    for (const id of sorted.slice(0, ids.length - MAX_SESSIONS)) delete data[id];
  }
  try {
    fs.writeFileSync(FILE, JSON.stringify(data));
  } catch {
    // 只读环境下静默降级：对话主流程不受存储失败影响
  }
}

function appendMessages(sessionId, messages) {
  if (!sessionId || typeof sessionId !== 'string') return;
  const sid = sessionId.slice(0, 64).replace(/[^\w-]/g, '');
  if (!sid) return;
  const all = loadAll();
  const sess = all[sid] || { sessionId: sid, createdAt: Date.now(), messages: [] };
  for (const m of messages) {
    sess.messages.push({ role: m.role, content: String(m.content).slice(0, 2000), time: Date.now() });
  }
  sess.messages = sess.messages.slice(-MAX_MSG_PER_SESSION);
  sess.updatedAt = Date.now();
  all[sid] = sess;
  saveAll(all);
}

function getSession(sessionId) {
  const sid = String(sessionId || '').slice(0, 64);
  const sess = loadAll()[sid];
  if (!sess) return null;
  return { sessionId: sid, createdAt: sess.createdAt, updatedAt: sess.updatedAt, messages: sess.messages };
}

module.exports = { appendMessages, getSession };
