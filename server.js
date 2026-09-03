const http = require('http');
const fs = require('fs');
const path = require('path');

const envPath = path.join(__dirname, '.env');
if (fs.existsSync(envPath)) {
  for (const line of fs.readFileSync(envPath, 'utf-8').split('\n')) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.+)\s*$/);
    if (m && !process.env[m[1]]) process.env[m[1]] = m[2];
  }
}

const { handleChat, handleHistory } = require('./lib/handler');

const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json' };

function sendJson(res, status, payload) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(payload));
}

const server = http.createServer(async (req, res) => {
  const u = new URL(req.url, 'http://localhost');
  if (u.pathname === '/api/chat' && req.method === 'POST') {
    let raw = '';
    req.on('data', (c) => (raw += c));
    req.on('end', async () => {
      let body = {};
      try {
        body = JSON.parse(raw || '{}');
      } catch {}
      const { status, body: payload } = await handleChat(body);
      sendJson(res, status, payload);
    });
    return;
  }
  if (u.pathname === '/api/history' && req.method === 'GET') {
    const { status, body: payload } = handleHistory(u.searchParams.get('sessionId'));
    sendJson(res, status, payload);
    return;
  }
  const file = u.pathname === '/' ? 'index.html' : u.pathname.replace(/^\//, '');
  const pub = path.join(__dirname, 'public');
  const full = path.join(pub, path.normalize(file));
  if (!full.startsWith(pub) || !fs.existsSync(full) || fs.statSync(full).isDirectory()) {
    res.writeHead(404);
    res.end('Not Found');
    return;
  }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(full)] || 'application/octet-stream' });
  fs.createReadStream(full).pipe(res);
});

const port = process.env.PORT || 3000;
server.listen(port, () => console.log('AI课程顾问 → http://localhost:' + port));
