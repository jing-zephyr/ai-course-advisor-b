const { handleChat } = require('../lib/handler');

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ code: 405, message: 'Method Not Allowed' });
    return;
  }
  let body = req.body;
  if (typeof body === 'string') {
    try {
      body = JSON.parse(body);
    } catch {
      body = {};
    }
  }
  const { status, body: payload } = await handleChat(body || {});
  res.status(status).json(payload);
};
