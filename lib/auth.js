const crypto = require('crypto');

// 演示级鉴权：双入口角色（user 用户入口 / admin 技术人员入口）
// 令牌为 HMAC-SHA256 签名的时间戳凭证，7 天过期（覆盖评审周期，评审人员一次登录即可）；密钥仅存服务端环境变量，不落仓库
const TTL_MS = 7 * 24 * 3600 * 1000;

function secret() {
  return process.env.AUTH_SECRET || 'aca|' + (process.env.ADMIN_PASSWORD || '') + '|' + (process.env.LLM_API_KEY || '');
}

function sign(payload) {
  return crypto.createHmac('sha256', secret()).update(payload).digest('hex').slice(0, 32);
}

function issue(role) {
  const exp = Date.now() + TTL_MS;
  const payload = role + '.' + exp;
  return 'aca.' + payload + '.' + sign(payload);
}

function verify(token) {
  if (typeof token !== 'string' || token.length > 200) return null;
  const m = token.match(/^aca\.(user|admin)\.(\d+)\.([0-9a-f]{32})$/);
  if (!m) return null;
  const payload = m[1] + '.' + m[2];
  const expect = sign(payload);
  // 恒时比较，防时序侧信道
  if (!crypto.timingSafeEqual(Buffer.from(m[3]), Buffer.from(expect))) return null;
  if (Date.now() > Number(m[2])) return null;
  return { role: m[1] };
}

function tokenFrom(headers) {
  const h = (headers && (headers.authorization || headers.Authorization)) || '';
  const m = h.match(/^Bearer\s+(.+)$/);
  return m ? verify(m[1].trim()) : null;
}

// 登录：用户入口免密（演示场景，昵称仅前端留存）；技术入口校验 ADMIN_PASSWORD
function login(role, password) {
  if (role === 'user') return { ok: true, token: issue('user'), role: 'user' };
  if (role === 'admin') {
    if (!process.env.ADMIN_PASSWORD) return { ok: false, status: 503, message: '技术人员入口未启用（未配置 ADMIN_PASSWORD）' };
    if (typeof password !== 'string' || password.length > 64) return { ok: false, status: 400, message: '口令格式不正确' };
    const a = Buffer.from(password);
    const b = Buffer.from(process.env.ADMIN_PASSWORD);
    if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return { ok: false, status: 401, message: '口令错误，请重试' };
    return { ok: true, token: issue('admin'), role: 'admin' };
  }
  return { ok: false, status: 400, message: '未知的登录角色' };
}

module.exports = { login, verify, tokenFrom };
