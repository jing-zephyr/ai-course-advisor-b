const { handleHistory } = require('../lib/handler');

module.exports = async (req, res) => {
  if (req.method !== 'GET') {
    res.status(405).json({ code: 405, message: 'Method Not Allowed' });
    return;
  }
  const { status, body: payload } = handleHistory(req.query && req.query.sessionId);
  res.status(status).json(payload);
};
