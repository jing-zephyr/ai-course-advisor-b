const { handleAdmin } = require('../lib/handler');
const { tokenFrom } = require('../lib/auth');

module.exports = async (req, res) => {
  if (req.method !== 'GET') {
    res.status(405).json({ code: 405, message: 'Method Not Allowed' });
    return;
  }
  const { status, body: payload } = handleAdmin((req.query && req.query.action) || 'stats', tokenFrom(req.headers));
  res.status(status).json(payload);
};
