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

// 会话列表摘要（管理端用，不含消息正文）
function listSessions() {
  const all = loadAll();
  return Object.values(all)
    .map((s) => ({
      sessionId: s.sessionId,
      createdAt: s.createdAt,
      updatedAt: s.updatedAt,
      count: (s.messages || []).length,
      preview: (((s.messages || [])[0] || {}).content || '').slice(0, 30),
    }))
    .sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
}

// 请求日志：独立文件环形缓冲，观测面板「检索追踪」用
const LOG_FILE = (() => {
  const local = path.join(__dirname, '..', 'data', 'logs.json');
  try {
    fs.accessSync(path.dirname(local), fs.constants.W_OK);
    return local;
  } catch {
    return path.join(os.tmpdir(), 'ai-course-advisor-logs.json');
  }
})();
const MAX_LOGS = 200;
let memLogs = null;

function readLogs() {
  if (memLogs) return memLogs;
  try {
    memLogs = JSON.parse(fs.readFileSync(LOG_FILE, 'utf-8'));
  } catch {
    memLogs = [];
  }
  return memLogs;
}

function appendLog(entry) {
  const logs = readLogs();
  logs.push({
    time: Date.now(),
    sessionId: String(entry.sessionId || '').slice(0, 64),
    zone: String(entry.zone || '').slice(0, 16),
    ms: entry.ms | 0,
    ok: !!entry.ok,
    msg: String(entry.msg || '').slice(0, 60),
  });
  memLogs = logs.slice(-MAX_LOGS);
  try {
    fs.writeFileSync(LOG_FILE, JSON.stringify(memLogs));
  } catch {
    // 只读环境静默降级
  }
}

function listLogs(limit) {
  return readLogs().slice(-(limit || 50)).reverse();
}

module.exports = { appendMessages, getSession, listSessions, appendLog, listLogs };
