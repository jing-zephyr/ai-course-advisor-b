# AI课程顾问 Web应用

> OPC接单吧实战能力大赛 · 软件与智能体赛道 · B级测试单交付物
>
> 公网演示：https://ai-course-advisor-b445432.netlify.app （Netlify 生产环境，可直接对话实测）

## 一、项目简介

「AI课程顾问」是一套可独立访问、也可嵌入官网的全栈对话式 Web 应用，面向 AI 教育公司的课程咨询场景。访客（学生家长、教师、企业合作方）可以像发微信一样咨询三类业务：**2026暑期AI素养夏令营**（素材A）、**初高中教师AI素养培训**（素材B）、**OPC超级个体赋能平台**（素材C）。AI 严格基于三份课程资料作答，标注来源、不编造；库外问题明确拒答并引导官方渠道。

系统设**双入口登录**：访客走「用户入口」免密进入；评审/工程师走「技术人员入口」，凭口令登录后开启**技术观测面板**，实时查看检索追踪（路由分区/检索词/命中知识块得分）、会话日志与知识库状态，让 RAG 黑盒过程透明可验。

## 二、技术栈

- **前端**：原生 HTML/CSS/JS 单页（`public/index.html`），零依赖、零构建，PC/移动端响应式；登录门禁 + 管理员观测抽屉
- **后端**：Node.js（≥18，零第三方依赖），本地 `server.js`（原生 http 模块）；Serverless 适配层 `api/`（Vercel）与 `netlify/functions/api.js`（Netlify，统一单函数入口）
- **LLM**：DeepSeek（`deepseek-chat`），OpenAI 兼容协议，可一键切换智谱 GLM / 通义 / Moonshot
- **知识库**：自研轻量 RAG——`data/knowledge.json`（36 个结构化知识块，含来源标签与关键词）+ 中文二元组切词 + 区路由 + IDF-lite 加权检索
- **鉴权**：演示级双角色令牌（HMAC-SHA256 签名 + 12 小时时效 + 恒时比较防时序攻击），密钥仅存服务端环境变量
- **存储**：会话与请求日志采用「进程内内存层为主、文件落盘为辅」；本地写入 `data/*.json`，Serverless 自动降级至 tmpdir

## 三、安装与运行（本地一键，≤15分钟）

```bash
# 1. 进入目录
cd 03_系统/app
# 2. 配置密钥：复制 .env.example 为 .env，填入 LLM_API_KEY
cp .env.example .env   # Windows: copy .env.example .env
# 3. 启动（无需 npm install，无任何依赖）
node server.js
# 4. 浏览器打开 http://localhost:3000
```

冒烟自检（29 项断言，含鉴权与观测接口）：`node test/smoke.js`

## 四、环境变量说明

| 变量 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `LLM_API_KEY` | 是 | 无 | 大模型 API 密钥（DeepSeek 或任何 OpenAI 兼容服务） |
| `LLM_BASE_URL` | 否 | `https://api.deepseek.com/v1` | OpenAI 兼容端点地址 |
| `LLM_MODEL` | 否 | `deepseek-chat` | 模型名 |
| `ADMIN_PASSWORD` | 否 | 无 | 技术人员入口口令；不配置则该入口返回 503 未启用 |
| `AUTH_SECRET` | 否 | 派生自密钥 | 令牌 HMAC 签名密钥，生产环境建议显式配置 |
| `PORT` | 否 | `3000` | 本地服务端口 |

## 五、核心功能说明

1. **双入口登录门禁**：首屏「用户入口 / 技术人员入口」分流。用户入口免密（昵称仅前端留存）；技术入口校验 `ADMIN_PASSWORD`（恒时比较），签发 HMAC-SHA256 时效令牌，后续请求经 `Authorization: Bearer` 鉴权，篡改/过期令牌一律拒绝。
2. **技术观测面板**（仅 admin 角色可见）：三页签——①检索追踪：请求日志环形缓冲（分区/耗时/成功率）+ 最近检索词与 Top5 命中块得分；②会话日志：会话列表摘要（首条消息预览/轮数/时间）；③知识库状态：36 块清单（分区/来源/关键词）。数据来自管理端只读接口 `GET /api/admin?action=stats|sessions|logs|knowledge`，无令牌一律 401。
3. **检索过程回放（trace）**：admin 角色的对话响应额外携带 `trace`（路由分区、实际检索词、命中块 ID 与得分、模型、总耗时），普通用户响应保持不变——同一接口、按角色分级返回。
4. **响应式对话界面**：品牌 Logo 区、消息区（用户右/AI 左双色气泡）、输入框、发送按钮、打字中加载动画；移动端输入框 16px 字号防 iOS 自动缩放，`100dvh` 适配软键盘弹出。
5. **快捷操作**：5 个快捷问题入口（学生课程/教师培训/查看所有班型/费用说明/报名方式）+ 4 张欢迎话题卡，降低输入成本。
6. **知识库问答（Prompt 注入 + 轻量 RAG）**：用户提问先经「区路由」（camp/teacher/platform/all），再在对应分区内做二元组+关键词+IDF 加权检索，Top5 知识块连同「回答规则」注入 System Prompt。回答末尾自动标注来源（《文档名》·章节）。
7. **动态 System Prompt**：识别用户身份（家长/初中/高中/教师/企业），向 System Prompt 追加差异化应答策略（如对家长侧重安全与费用明细）。
8. **多轮对话**：前端携带最近 8 条历史；后端对短句追问自动融合上一条用户消息做检索，避免指代丢失。
9. **对话记录**：每条对话按 `sessionId` 持久化；`GET /api/history?sessionId=xxx` 查询当前会话全部消息。
10. **统一 API 规范**：`POST /api/chat`、`POST /api/login`、`GET /api/history`、`GET /api/admin` 均为 JSON；错误统一返回 `{code, message}`（如 `{code:500, message:"服务繁忙"}`）。

## 六、架构要点：Serverless 单函数入口

Netlify 各 Function 运行在相互隔离的 Lambda 容器，进程内存与 `/tmp` 互不共享。初版将 chat/history/login/admin 拆为 4 个函数，公网实测出现「chat 写入的会话在 history 读不到」（测试用例 F5/F6 失败）。遂收敛为 **`netlify/functions/api.js` 单函数统一入口**，`_redirects` 将 `/api/*` 全部重写至该函数，同实例内共享 store 内存层与临时目录；原 4 个函数文件保留为兼容转发并注明演进原因。本地 `server.js` 为单进程，天然无此问题，两侧业务代码（`lib/`）完全一致。

## 七、AI辅助开发标注

本项目由开发者主导设计、AI（TRAE）辅助编码完成：

- **人工完成**：技术选型（零依赖 Node 原生栈、双平台部署策略）、双入口与技术观测面板的产品决策、知识库 36 块的切分粒度与关键词设计、提示词规则（知识边界/来源标注/拒编）的逐条定义、测试用例设计与结果判定、UI 视觉方向（教育蓝金配色、头像元素）。
- **AI 辅助完成**：`lib/` 与 `server.js` 代码初稿、鉴权与观测接口实现、前端页面样式与交互脚本、部署脚本、本文档初稿。
- **人工复核**：全部代码逐行审阅；检索排序经过「L1 课程问题误排」缺陷修复（引入 IDF-lite 降权区公共词）；Serverless 容器隔离缺陷经公网实测定位后改为单函数入口；31 组真机测试全部人工核验输出内容。
- 详细标注见《AI辅助开发标注.md》。

## 八、目录结构

```
app/
├── public/index.html      # 前端单页（登录门禁 + 对话界面 + 技术观测面板）
├── public/_redirects      # /api/* → 统一 api 函数
├── server.js              # 本地一键启动（静态+API）
├── api/                   # Vercel Serverless 入口（chat/history/login/admin）
├── netlify/functions/     # Netlify 入口：api.js 统一承载 /api/*（其余4个保留为兼容转发）
├── lib/                   # 核心业务：retrieval 检索 / prompt 提示词 / handler 编排 / store 会话存储 / auth 鉴权
├── data/knowledge.json    # 结构化知识库（36块，三区）
├── test/                  # smoke.js 29项自检 + live_test.py 31例真机电池 + 部署脚本
└── .env.example           # 环境变量模板
```
