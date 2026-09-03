# AI课程顾问 Web应用

> OPC接单吧实战能力大赛 · 软件与智能体赛道 · B级测试单交付物
>
> 公网演示：https://ai-course-advisor-b445432.netlify.app （Netlify 生产环境，可直接对话实测）

## 一、项目简介

「AI课程顾问」是一套可独立访问、也可嵌入官网的全栈对话式 Web 应用，面向 AI 教育公司的课程咨询场景。访客（学生家长、教师、企业合作方）可以像发微信一样咨询三类业务：**2026暑期AI素养夏令营**（素材A）、**初高中教师AI素养培训**（素材B）、**OPC超级个体赋能平台**（素材C）。AI 严格基于三份课程资料作答，标注来源、不编造；库外问题明确拒答并引导官方渠道。

## 二、技术栈

- **前端**：原生 HTML/CSS/JS 单页（`public/index.html`），零依赖、零构建，PC/移动端响应式
- **后端**：Node.js（≥18，零第三方依赖），本地 `server.js`（原生 http 模块）；Serverless 适配层 `api/`（Vercel）与 `netlify/functions/`（Netlify）
- **LLM**：DeepSeek（`deepseek-chat`），OpenAI 兼容协议，可一键切换智谱 GLM / 通义 / Moonshot
- **知识库**：自研轻量 RAG——`data/knowledge.json`（36 个结构化知识块，含来源标签与关键词）+ 中文二元组切词 + 区路由 + IDF-lite 加权检索
- **存储**：对话历史持久化为本地 JSON 文件（`data/sessions.json`），Serverless 环境自动降级至 tmpdir

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

冒烟自检（不消耗 LLM 额度之外的离线断言 + 1 次真实对话）：`node test/smoke.js`

## 四、环境变量说明

| 变量 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `LLM_API_KEY` | 是 | 无 | 大模型 API 密钥（DeepSeek 或任何 OpenAI 兼容服务） |
| `LLM_BASE_URL` | 否 | `https://api.deepseek.com/v1` | OpenAI 兼容端点地址 |
| `LLM_MODEL` | 否 | `deepseek-chat` | 模型名 |
| `PORT` | 否 | `3000` | 本地服务端口 |

## 五、核心功能说明

1. **响应式对话界面**：品牌 Logo 区、消息区（用户右/AI 左双色气泡）、输入框、发送按钮、打字中加载动画；移动端输入框 16px 字号防 iOS 自动缩放，`100dvh` 适配软键盘弹出。
2. **快捷操作**：5 个快捷问题入口（学生课程/教师培训/查看所有班型/费用说明/报名方式）+ 4 张欢迎话题卡，降低输入成本。
3. **知识库问答（Prompt 注入 + 轻量 RAG）**：用户提问先经「区路由」（camp/teacher/platform/all），再在对应分区内做二元组+关键词+IDF 加权检索，Top5 知识块连同「回答规则」注入 System Prompt。回答末尾自动标注来源（《文档名》·章节）。
4. **动态 System Prompt**：识别用户身份（家长/初中/高中/教师/企业），向 System Prompt 追加差异化应答策略（如对家长侧重安全与费用明细）。
5. **多轮对话**：前端携带最近 8 条历史；后端对短句追问自动融合上一条用户消息做检索，避免指代丢失。
6. **对话记录**：每条对话按 `sessionId` 持久化到 JSON 文件；`GET /api/history?sessionId=xxx` 查询当前会话全部消息。
7. **统一 API 规范**：`POST /api/chat` 与 `GET /api/history` 均为 JSON；错误统一返回 `{code, message}`（如 `{code:500, message:"服务繁忙"}`）。

## 六、AI辅助开发标注

本项目由开发者主导设计、AI（TRAE）辅助编码完成：

- **人工完成**：技术选型（零依赖 Node 原生栈、双平台部署策略）、知识库 36 块的切分粒度与关键词设计、提示词规则（知识边界/来源标注/拒编）的逐条定义、测试用例设计与结果判定、UI 视觉方向（教育蓝金配色、头像元素）。
- **AI 辅助完成**：`lib/` 与 `server.js` 代码初稿、前端页面样式与交互脚本、部署脚本、本文档初稿。
- **人工复核**：全部代码逐行审阅；检索排序经过「L1 课程问题误排」缺陷修复（引入 IDF-lite 降权区公共词）；24 组真机测试全部人工核验输出内容。
- 详细标注见《AI辅助开发标注.md》。

## 七、目录结构

```
app/
├── public/index.html      # 前端单页（对话界面）
├── server.js              # 本地一键启动（静态+API）
├── api/                   # Vercel Serverless 入口（chat/history）
├── netlify/functions/     # Netlify Functions 入口（chat/history）
├── lib/                   # 核心业务：retrieval 检索 / prompt 提示词 / handler 编排 / store 会话存储
├── data/knowledge.json    # 结构化知识库（36块，三区）
├── test/                  # smoke.js 离线自检 + live_test.py 24例真机电池 + 部署脚本
└── .env.example           # 环境变量模板
```
