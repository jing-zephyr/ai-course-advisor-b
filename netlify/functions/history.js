const { handleHistory } = require('../../lib/handler');

exports.handler = async (event) => {
  if (event.httpMethod !== 'GET') {
    return { statusCode: 405, body: JSON.stringify({ code: 405, message: 'Method Not Allowed' }) };
  }
  const qs = event.queryStringParameters || {};
  const { status, body: payload } = handleHistory(qs.sessionId);
  return {
    statusCode: status,
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
    body: JSON.stringify(payload),
  };
};
