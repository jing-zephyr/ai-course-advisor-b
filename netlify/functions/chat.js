// 已合并：所有 /api/* 统一由 api.js 单函数承载。
// 多函数部署时各 Lambda 容器的内存与 /tmp 相互隔离，会话记录会跨函数丢失，故收敛为单入口。
// 本文件保留作兼容转发（直接部署整个 functions 目录时行为一致），正式部署仅打包 api.js。
exports.handler = require('./api').handler;
