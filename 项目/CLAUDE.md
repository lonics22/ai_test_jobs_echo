# 抖音链接收藏管理器

抖音视频链接收藏工具，支持链接保存、AI 自动分类摘要、多端同步。

## 工作流规则（必须遵守）

### 规则 1：开始任务前必须阅读文档

当你将某个任务标记为 `in_progress` 之前，先阅读以下三份文档：

1. `docs/prd.md` — 产品需求，了解功能边界和用户故事
2. `docs/architecture.md` — 架构设计，了解技术方案和分层
3. `docs/tasks.md` — 任务分解，了解当前进度和依赖关系

阅读后，确认你理解了当前任务的范围、涉及的模块和完成标准，再开始编码。

### 规则 2：完成任务后必须测试并更新

当你完成一个任务（准备标记为 `completed`）时：

1. **运行该任务对应的测试脚本**（如果存在）
2. **确认测试全部通过**
3. **更新 `docs/tasks.md`** 中该任务的状态
4. **提交 commit**

### 规则 3：不允许跨任务开发

- 一次只处理一个任务
- 不允许同时修改多个任务的代码
- 当前任务完成并提交后，再开始下一个

## 项目结构

```
├── main.py              # FastAPI 应用入口
├── app/
│   ├── database.py      # 数据库 CRUD
│   ├── api/
│   │   └── bookmarks.py # API 路由
│   └── services/
│       ├── bookmark_service.py  # 业务编排
│       ├── scraper.py           # OG 信息抓取
│       └── ai_service.py        # AI 分类摘要
├── static/
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── data/                # SQLite 数据库目录
└── docs/
    ├── prd.md           # 产品需求文档
    ├── architecture.md  # 架构设计文档
    └── tasks.md         # 任务分解与进度
```

## 技术栈

- 后端: Python FastAPI + SQLite
- 前端: 原生 HTML/CSS/JS（响应式）
- AI: OpenAI / Claude API
- 部署: 本地运行

## Git 约定

- 每个任务一个独立 commit
- commit message 格式: `task-N: 任务简述`
