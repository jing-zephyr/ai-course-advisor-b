// 已合并：所有 /api/* 统一由 api.js 单函数承载，原因见 api.js 与 chat.js 顶部注释。
exports.handler = require('./api').handler;
