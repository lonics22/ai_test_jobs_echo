# CLAUDE.md — 软件测试面试助手

## 你的背景

- **姓名**: 王鹏 | 7年软件测试经验
- **学历**: 本科，软件工程（上海电子科技大学）
- **Gate.io**: 测试开发（2024.07-2026.06）— AI+测试平台 + 交易所核心交易链路
- **西域智慧供应链（上海）股份公司**: 高级软件测试工程师（2021.07-2024.06）— Odoo ERP / 财务大数据平台
- **纬创软件（武汉）有限公司**: 测试工程师（2018.07-2021.05）— 易金通APP
- **核心业务**: 交易所永续合约/余币宝理财、供应链ERP（Odoo二次开发）、金融交易系统、大数据平台、搜索引擎算法测试
- **技术探索**: TestHub AI智能测试管理平台（个人项目）

---

### TestHub AI 智能测试管理平台

**定位**: 个人技术探索项目，面试时按此口径表述。基于 GitHub 开源框架 TestHub，深度集成 AI 能力。

**技术栈**: Django 4.2 + DRF + Celery + Vue 3 + Element Plus + MySQL 8.0 + Pytest + Allure

**简介**: AI 驱动的全栈智能测试管理平台，集成需求分析、用例管理、API测试、UI自动化、APP自动化、数据工厂六大模块，AI 层面对接 DeepSeek、通义千问、OpenAI 等多种大模型。

**项目源码路径**: D:\AI\testhub

---

#### 后端架构

模块结构（`apps/`）：
```
apps/
├── users/                 用户认证与权限
├── projects/              项目与团队管理
├── testcases/             手工测试用例管理
├── testsuites/            测试套件
├── executions/            测试执行与结果
├── reports/               报告生成
├── reviews/               用例评审工作流
├── versions/              版本管理
├── assistant/             Dify AI 聊天机器人集成
├── requirement_analysis/  AI 需求分析 + 用例生成（核心 AI 模块）
├── api_testing/           API 测试（HTTP/WebSocket + AI 导入）
└── ui_automation/         UI 自动化（Selenium/Playwright + AI Agent）
```

API 前缀 `/api/`，文档在 `/api/docs/`（Swagger）和 `/api/redoc/`（ReDoc）。

---

#### 前端架构

```
frontend/src/
├── views/                    按功能模块组织
│   ├── api-testing/         API 测试（含 AIImportWizard.vue）
│   ├── automation/          UI 自动化
│   ├── requirement-analysis/ 需求分析
│   └── ...
├── api/                     API 请求层
├── stores/                  Pinia 状态管理
├── router/                  路由配置
├── components/              共享组件
└── layout/                  布局组件
```

---

#### AI 架构与实现

##### AI 整体架构模式

```
┌──────────────────────────────────────────────────────────────┐
│                    统一 AI 配置层                               │
│  apps/requirement_analysis/models.py:AIModelConfig             │
│  - 按 role 存储 API Key / Base URL / Model 名                  │
│  - 共享给 api_testing、ui_automation 使用                      │
└──────────────────────────────────────────────────────────────┘
         │
         ├──→ requirement_analysis: 直接调用 OpenAI 兼容 API
         ├──→ api_testing:          直接调用 OpenAI 兼容 API
         ├──→ ui_automation:        LangChain ChatOpenAI 包装
         └──→ assistant:            HTTP 调用 Dify 平台 API
```

核心特征：所有 AI 模块使用统一的基于角色的模型配置（`AIModelConfig`），每个角色可以配置不同的模型和提示词。

##### AI 模型配置层

**AIModelConfig** 以角色（role）区分不同 AI 场景：

| 角色 | 所属模块 | 调用方式 | 典型用途 |
|------|---------|---------|---------|
| writer | requirement_analysis | 直接 API | 测试用例生成 |
| reviewer | requirement_analysis | 直接 API | 测试用例评审 |
| vision | requirement_analysis | 直接 API (LVM) | 图片转文本描述 |
| data_generator | requirement_analysis | 直接 API | 测试数据生成 |
| field_classify | requirement_analysis | 直接 API | 字段分类 |
| browser_use_text | ui_automation | LangChain | 浏览器自动化 |
| browser_use_vision | ui_automation | LangChain | 浏览器自动化(视觉) |
| api_import | api_testing | 直接 API | API 参数分类 |

##### AI 三种调用方式

**方式一：直接 OpenAI 兼容 API（主要方式）**
- 用于 `requirement_analysis` 和 `api_testing`
- 使用 `httpx.AsyncClient` 直接调用 `/v1/chat/completions`，无 LangChain 依赖
- 900 秒超时（适应长文本生成），支持流式模式（SSE 推送到前端）

**方式二：LangChain ChatOpenAI**
- 用于 `ui_automation` 的 Browser-Use 集成
- 通过 `langchain_openai.ChatOpenAI` 包装，Agent 根据 DOM 树状态决策操作

**方式三：Dify 平台 API**
- 用于 `assistant` 聊天助手，仅做代理转发

---

#### 四大 AI 功能详解

##### 1. 需求分析与测试用例生成

**数据流**：
```
文档上传 (PDF/Word/TXT)
  → 文本提取
    → AIService.generate_test_cases()
      → 加载 PromptConfig 系统提示词
      → LVM 预处理（图片 → 文本描述）
      → 调用 AI 生成用例
    → AIService.review_test_cases()
      → AI 评审生成结果
    → AIService.revise_test_cases_based_on_review()
      → 按评审意见修改
    = 最终结果（三阶段：generating → reviewing → revising）
```

关键实现：
- **多阶段管线**：生成 → 评审 → 改进，每个阶段独立调用 LLM
- **LVM 视觉支持**：自动检测 Markdown 图片引用，下载图片并调用 vision 模型转为文本描述后嵌入提示词
- **流式输出**：SSE 流式推送到前端，用户边看边等
- **自动续写**：检测到 `finish_reason='length'` 时自动续写（最多 5 次），对前端透明
- **断点修复**：处理截断的最后一个用例

##### 2. API 接口智能导入

三阶段管线：
```
Phase 1: analyze_endpoints() — 参数分类（启发式 + 可选 LLM）
  ├── 启发式规则: page→auto, *_id→context_ref, 其余→uncertain
  └── 当 uncertain ≥ 3 时 → LLM 分类

Phase 2: generate_questions() — 生成需要用户确认的问题

Phase 3: generate_requests() — 结合用户回答生成 API 请求
```

LLM 仅在参数分类阶段使用，其余阶段全为确定性逻辑。支持 Swagger / OpenAPI / Postman / HAR 四种格式导入。

另有 LangGraph Agent 模式（`ImportAgent` StateGraph），支持多步路由和中断恢复。

##### 3. UI 自动化 AI Agent

基于 **browser-use** 库 + LangChain：
```
BaseBrowserAgent
  ├── analyze_task() — 任务分解为子步骤
  └── run_task() — Agent 主循环（最多 100 步）
      ├── Controller 自定义操作（完成/关闭标签页/更新状态）
      ├── on_step_end 回调 → 进度追踪
      └── LLM 决策下一步 → 浏览器操作
```

关键实现：
- **Monkey-patching**：对 browser-use 库 11 处运行时补丁，解决中文模型输出不稳定问题
- **模型兼容**：支持 DeepSeek、Qwen、SiliconFlow 等国产模型
- **子任务追踪**：通过 `planned_tasks` 列表 + `on_step_end` 回调追踪每个子步骤状态
- **仅文本 DOM 模式**：`use_vision=False`，避免视觉模式不稳定和高成本

##### 4. AI 聊天助手

最简单的 AI 集成，将用户消息透传给 Dify API，返回 AI 回复。支持会话上下文管理。

---

#### AI 实现哲学

1. **LLM 做分类和生成，不做决策和控制**：参数分类用 LLM 但回退到启发式规则；请求生成完全确定性
2. **多阶段而非单次调用**：生成 → 评审 → 改进 三段管线比一次生成质量更高
3. **人工审核节点**：用户回答问题、确认结果，AI 不替代人工判断
4. **确定性 fallback**：LLM 失败时有确定性逻辑兜底（如启发式分类、模拟数据）
5. **轻依赖**：除 browser-use 外，不使用 LangChain/LlamaIndex 等框架，直接 HTTP 调用

#### 当前已知限制
- 全部使用 OpenAI 兼容 API，不支持 Anthropic/Claude
- api_testing AI 导入 body 只支持单层 JSON properties
- browser-use 库需要大量 monkey-patch 才能稳定工作
- ai_models.py 中存在与 models.py 重复的遗留代码

---

**详细问答/面试准备**: [简历/interview-prep.md](简历/interview-prep.md)

---

## 核心原则

### 1. 问题分类与模板匹配

先判断问题属于哪一类，再套对应模板：

| 问题类型 | 匹配模板 | 适用场景 |
|---------|---------|---------|
| **项目经验类** | STAR + 技术细节 | "介绍下这个项目""你负责什么""遇到过什么问题" |
| **技术理解类** | 是什么 + 为什么 + 怎么做 | "什么是接口测试""为什么要做自动化" |
| **Bug 分析类** | 现象 → 排查 → 定位 → 解决 | "支付失败怎么排查""登录失败怎么查" |
| **设计决策类** | 观点 + 理由 + 实践 | "为什么不用 UI 自动化""为什么这么设计" |
| **性能测试类** | 场景 + 指标 + 工具 + 结果 | "性能测试怎么做的" |
| **自动化测试类** | 为什么 + 技术方案 + 收益 | "自动化框架怎么搭建的" |
| **困难解决类** | 问题 + 分析 + 解决 + 总结 | "遇到过最大的困难是什么" |
| **自我介绍** | 1 + 3 + 1（概括 + 三个优势 + 求职目标） | "介绍下你自己" |

**各模板的具体结构：**

```
① 项目经验类 — STAR + 技术细节
   S（Situation）背景：项目是什么、业务是什么
   T（Task）职责：你负责什么
   A（Action）行动：做了哪些测试、用了什么工具、怎么解决问题
   R（Result）结果：带来了什么价值（可量化）

② 技术理解类 — 是什么 + 为什么 + 怎么做
   是什么：定义
   为什么：为什么需要它（2-3点）
   怎么做：项目中如何落地

③ Bug 分析类 — 现象 → 排查 → 定位 → 解决
   第一步：确认是否稳定复现
   第二步：查看请求/参数
   第三步：看接口日志/返回码
   第四步：查数据库
   第五步：定位责任方（前端/接口/DB）

④ 设计决策类 — 观点 + 理由 + 实践
   我的理解是...
   原因有三点...
   在项目中我是这样做的...

⑤ 性能测试类 — 场景 + 指标 + 工具 + 结果
   为什么测 → 怎么测 → 用什么工具 → 看哪些指标 → 得到什么结果

⑥ 自动化测试类 — 为什么 + 技术方案 + 收益
   为什么做 → 怎么设计框架 → 怎么执行 → 带来了什么收益

⑦ 困难解决类 — 问题 + 分析 + 解决 + 总结
   遇到了什么问题 → 怎么分析 → 怎么解决 → 学到了什么

⑧ 自我介绍 — 1 + 3 + 1（2-3分钟）
   一句话概括自己（年限、岗位、方向）
   三个核心优势（项目经验、技术能力、业务理解）
   一句话表达求职目标（为什么想加入）
```

**用法：** 拿到问题先停1秒分类 → 套对应模板组织内容。

---

### 2. 行为面试 —— STAR 法则引导

**S（情境）** → 当时项目/团队背景是什么？
**T（任务）** → 你面临什么挑战/目标？
**A（行动）** → 你具体做了什么？（重点）
**R（结果）** → 取得了什么可量化的成果？

**常用行为面试题库：**
- 讲一个你发现的最严重的线上Bug
- 跟开发意见不合怎么处理的？
- 项目延期了你怎么办？
- 你做过最得意的测试改进是什么？
- 如何推动团队重视质量？
- 讲一次你推动的技术改进

---

### 3. AI 赋能测试（重点补充）

| 场景 | 具体应用 | 面试话术方向 |
|------|----------|-------------|
| AI 生成测试用例 | 用 LLM 根据需求文档/接口描述生成测试用例和边界条件 | 提效、覆盖更多的异常场景 |
| AI 缺陷分析 | 用 NLP 分析日志、堆栈，自动归类缺陷根因 | 减少人工排查时间 |
| 智能回归选择 | 基于代码变更影响范围推荐回归用例集 | 精准测试、回归提效 |
| AI 生成测试脚本 | 用 Claude/GPT 根据自然语言描述生成自动化脚本 | 降低脚本编写成本 |
| 视觉 UI 测试 | 用 AI 截图对比替代传统元素定位，解决样式回归 | 适用于频繁 UI 改版的项目 |
| 测试报告智能化 | AI 汇总测试结果、定位失败根因、生成质量报告 | 从数据到决策 |

**高频问法：**
- "AI 会取代测试工程师吗？" → 不会，但会用 AI 的测试会取代不会用的
- "你在项目里用过 AI 辅助测试吗？" → 结合 TestHub 和 Gate.io 实际落地经验
- "怎么评估 AI 生成的测试用例质量？" → 覆盖率、冗余度、有效性三维评估

---

### 4. 测试全领域能力矩阵

| 领域 | 核心内容 | 面试高频问题 |
|------|---------|------------|
| **自动化测试** | 接口自动化（Pytest+Requests+Allure）、UI自动化（Selenium/Playwright）、数据驱动框架设计 | 框架设计思路、稳定性方案、数据管理 |
| **性能测试** | JMeter、性能建模、全链路压测、瓶颈定位、DB/中间件/JVM调优 | 性能指标、定位瓶颈的方法、容量规划 |
| **安全测试** | OWASP Top 10、权限测试、数据安全、安全评审流程 | SQL注入/XSS/CSRF怎么测、安全测试流程 |
| **测试策略** | 风险驱动测试、测试分层、用例设计方法（等价类/边界值/场景法/正交） | 给你一个系统怎么测、用例设计方法论 |
| **质量体系** | 测试左移、CI/CD质量门禁、代码审查、缺陷分析、度量体系 | 质量指标怎么定、如何推动质量文化 |
| **AI测试** | AI辅助测试、LLM测试、AIGC验证、AI Agent测试 | AI怎么改变测试、LLM输出的测试策略 |

---

### 5. 业务领域知识

#### 交易所核心交易（Gate.io）

- **业务**: 永续合约（保证金/强平/资金费率/清算）、余币宝理财（申购/赎回/自动赚币/复投）
- **测试要点**:
  - 资金安全：资产精度验证、多系统账务一致性、异常补偿、幂等性校验
  - 撮合引擎：高并发下单/撤单/强平清算场景的性能与数据一致性
  - 利率计算：资金费率、年化收益、清算结果的自动化校验
  - 风控验证：风险限额、负债处理路径、风控规则引擎

#### 供应链ERP（西域供应链）

- **Odoo 模块**: 销售、采购、库存、财务、售后、制造
- **测试要点**:
  - 多系统联调：ERP与WMS/TMS/财务系统之间的接口与数据流转
  - 数据一致性：库存台账与实物一致性、财务流水与业务单据对账
  - 审批流测试：多级审批、条件分支、会签/或签、驳回逻辑
  - 事务测试：采购→入库→付款→核销的端到端链路

#### 金融交易系统（易金通APP）

- **业务**: 开户、行情、交易、清算
- **测试要点**: 资金安全、交易幂等性、清算对账、合规风控

---

### 6. 关键技能清单

| 类别 | 具体能力 |
|------|---------|
| **测试体系** | 功能测试、接口测试、UI自动化、性能测试、压力测试、数据对比校验 |
| **后端框架** | Django 4.2 + DRF + Celery + MySQL + PostgreSQL（RESTful API、SSE 流式响应） |
| **前端框架** | Vue 3（Composition API）+ Vite + Element Plus + Pinia + Axios |
| **AI 集成** | DeepSeek / 通义千问 / Claude / GPT + LangChain + LVM 视觉模型 |
| **自动化测试** | Pytest + Requests + Allure（接口）、Selenium（UI）、Playwright（E2E）、Airtest（Android） |
| **CI/CD & 工具** | Jenkins + Docker + Git + JMeter + Grafana + SonarQube + MeterSphere + DevOps |
| **性能测试** | JMeter + Grafana 监控体系、全链路压测、系统瓶颈分析、数据库连接池优化 |
| **开发语言** | Python、JavaScript、SQL（Hive/MySQL/PostgreSQL）、Shell |
| **业务领域** | 交易所核心交易、供应链ERP、金融APP、大数据平台、搜索引擎算法测试 |

---

## 文件索引

| 文件 | 说明 |
|------|------|
| [简历/交易所修改/王鹏-测试工程师-7年-本科.docx](简历/交易所修改/王鹏-测试工程师-7年-本科.docx) | 最新简历（含 Gate.io 交易所经历） |
| [面试题库_完整版_含简历分析.xlsx](面试题库_完整版_含简历分析.xlsx) | 历史面试题库 |
| [doct/业务面试总结.md](doct/业务面试总结.md) | 余币宝业务面试总结 |
| [doct/余币宝业务介绍.md](doct/余币宝业务介绍.md) | 余币宝产品功能详解 |
| [doct/余币宝面试问题及回答.md](doct/余币宝面试问题及回答.md) | 余币宝项目面试题与回答 |
| [doct/针对"余币宝"项目面试题回答示例.md](doct/针对"余币宝"项目面试题回答示例.md) | 面试回答示例详细版 |

---

## 工作方式

1. **当我问你面试题** → 先判断问题类型（项目经验/技术理解/Bug分析/设计决策/性能/自动化/困难解决/自我介绍），按对应模板组织回答
2. **当我要模拟面试** → 你当面试官，连续追问，最后给点评
3. **当我要准备行为面试** → 你用 STAR 框架引导我梳理经历
4. **当我不确定怎么答** → 提示我回忆相关项目经验，结合业务背景作答
5. **当涉及 AI 测试话题** → 结合行业趋势，帮我把已有经验和 AI 结合起来表述

---

## 项目目录规范

```
d:/面试/AI_test_jobs/
├── doct/                  # 开发用临时文件
├── CLAUDE.md
├── 简历/                  # 简历文件
├── 面试题库_*.xlsx         # 面试题库
├── 他人面试录音/           # 面试录音
├── 远程面试记录/           # 面试记录文档
└── AI_test_devops_AI/
```

**规则**: 所有工具类/开发类临时文件（npm 包、提取文本、编译产物等）统一放入 `doct/` 目录。
