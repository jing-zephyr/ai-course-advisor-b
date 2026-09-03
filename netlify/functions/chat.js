const { handleChat } = require('../../lib/handler');

exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: JSON.stringify({ code: 405, message: 'Method Not Allowed' }) };
  }
  let body = {};
  try {
    body = JSON.parse(event.body || '{}');
  } catch {}
  const { status, body: payload } = await handleChat(body);
  return {
    statusCode: status,
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
    body: JSON.stringify(payload),
  };
};
