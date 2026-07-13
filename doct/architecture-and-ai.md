# TestHub 项目架构与 AI 实现总结

## 一、项目概览

TestHub 是一个 AI 驱动的测试管理平台，后端 Django 4.2 + DRF，前端 Vue 3 + Element Plus。覆盖功能：测试用例管理、API 测试、UI 自动化测试、AI 需求分析/用例生成/导入。

---

## 二、后端架构

### 2.1 模块结构（`apps/`）

```
apps/
├── users/             用户认证与权限
├── projects/          项目与团队管理
├── testcases/         手工测试用例管理
├── testsuites/        测试套件
├── executions/        测试执行与结果
├── reports/           报告生成
├── reviews/           用例评审工作流
├── versions/          版本管理
├── assistant/         Dify AI 聊天机器人集成
├── requirement_analysis/  AI 需求分析 + 用例生成（核心 AI 模块）
├── api_testing/        API 测试（HTTP/WebSocket + AI 导入）
└── ui_automation/      UI 自动化（Selenium/Playwright + AI Agent）
```

### 2.2 关键配置

- `backend/settings.py`: 数据库、REST framework、CORS、Celery
- `.env`: 环境变量（DB 凭证、API keys、邮件配置）

### 2.3 API 结构

所有端点前缀 `/api/`，文档在 `/api/docs/`（Swagger）和 `/api/redoc/`（ReDoc）。

---

## 三、前端架构

```
frontend/src/
├── views/             按功能模块组织
│   ├── api-testing/   API 测试（含 AIImportWizard.vue）
│   ├── automation/    UI 自动化
│   ├── requirement-analysis/ 需求分析
│   └── ...
├── api/               API 请求层
├── stores/            Pinia 状态管理
├── router/            路由配置
├── components/        共享组件
└── layout/            布局组件
```

---

## 四、AI 实现方式详解

### 4.1 整体架构模式

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

**核心特征**：所有 AI 模块使用统一的基于角色的模型配置（`AIModelConfig`），每个角色可以配置不同的模型和提示词。

### 4.2 AI 模型配置层

**文件**: `apps/requirement_analysis/models.py`

**AIModelConfig**（第 203 行）以角色（role）区分不同 AI 场景：

```python
class AIModelConfig(models.Model):
    role = models.CharField(choices=[
        ('writer', '测试用例编写'),
        ('reviewer', '测试用例评审'),
        ('vision', '视觉模型-LVM'),
        ('data_generator', '测试数据生成'),
        ('field_classify', '字段分类'),
        ('browser_use_text', '浏览器自动化-文本模式'),
        ('browser_use_vision', '浏览器自动化-视觉模式'),
        ('api_import', 'API 导入'),
    ])
    provider = models.CharField(choices=[
        'DeepSeek', 'Qwen(通义千问)', 'SiliconFlow(硅基流动)',
        'Zhipu(智谱)', 'Xiaomi', 'Xiaomi Coding Plan', 'Other'
    ])
    api_key, base_url, model_name, temperature, top_p
```

**PromptConfig**（第 257 行）：每个角色可配置系统提示词，支持版本管理。

### 4.3 AI 调用方式

#### 方式一：直接 OpenAI 兼容 API（主要方式）

用于 `requirement_analysis` 和 `api_testing`。使用 `httpx.AsyncClient` 直接调用 `/v1/chat/completions`（`models.py` 第 480 行，`call_openai_compatible_api`）:

```python
@staticmethod
async def call_openai_compatible_api(config, messages, **kwargs):
    async with httpx.AsyncClient(timeout=900) as client:
        response = await client.post(
            f"{config.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {config.api_key}"},
            json={"model": config.model_name, "messages": messages, ...}
        )
        return response.json()
```

特点：
- 无 LangChain、无第三方 SDK 依赖
- 900 秒超时（适应长文本生成）
- 支持流式模式（SSE 推送到前端）
- 不支持 Anthropic/Claude（仅 OpenAI 兼容协议）

#### 方式二：LangChain ChatOpenAI

用于 `ui_automation`（`ai_base.py` 第 937 行）:

```python
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model=model_name, api_key=api_key, base_url=base_url, temperature=temperature)
```

`browser-use` 库使用 LangChain 的 `ChatOpenAI` 类包装 LLM，Agent 根据浏览器状态（DOM 树、截图）决定下一步操作。

#### 方式三：Dify 平台 API

用于 `assistant`（`views.py` 第 54 行）:

```python
requests.post(f"{config.api_url}/chat-messages",
    headers={"Authorization": f"Bearer {config.api_key}"},
    json={"inputs": {}, "query": message, "response_mode": "blocking", "user": user_id}
)
```

AI 模型托管在 Dify 端，TestHub 仅做代理转发。

---

## 五、四大 AI 功能详解

### 5.1 需求分析与测试用例生成（requirement_analysis）

**数据流**:

```
文档上传 (PDF/Word/TXT)
    → 文本提取 (services.py: 按文件类型解析)
    → AIService.generate_test_cases() (models.py:753)
      → 加载 PromptConfig 系统提示词
      → 预处理器扫描 ![image](url) 标记 → LVM 转为文本描述
      → 调用 call_openai_compatible_api() → 生成用例
    → AIService.review_test_cases() (models.py:799)
      → 加载 reviewer 提示词
      → 对生成的用例进行评审
    → AIService.revise_test_cases_based_on_review() (models.py:976)
      → 按评审意见修改
    = 最终结果 (多阶段管线: generating → reviewing → revising → completed)
```

**关键实现**：
- **多阶段管线**：生成 → 评审 → 改进，每个阶段独立调用 LLM
- **LVM 视觉支持**：`preprocess_images()`（第 1307 行）自动检测 Markdown 图片引用，下载图片并调用 vision 模型转为文本描述后嵌入提示词
- **流式输出**：`generate_test_cases_stream()`（第 832 行）支持 SSE 流式推送
- **自动续写**：流式模式检测 `finish_reason='length'` 时自动续写（最多 5 次）
- **断点修复**：`fix_incomplete_last_case()`（第 1148 行）处理截断的最后一个用例

### 5.2 API 接口导入（api_testing）

**三阶段管线**（`ai_import_service.py`）:

```
Phase 1: analyze_endpoints() — 参数分类（启发式 + 可选 LLM）
  ├── 启发式规则: page→auto, *_id→context_ref, 其余→uncertain
  └── 当 uncertain ≥ 3 时 → LLM 分类为 auto/manual/context_ref

Phase 2: generate_questions() — 用户问题生成（纯确定性逻辑）
  ├── URL domain 问题（固定）
  ├── Auth 问题（仅当检测到认证 header 参数时）
  ├── 参数值填写表格（仅当有 manual 参数时）
  └── 环境变量映射（固定）

Phase 3: generate_requests() — 请求生成（纯确定性逻辑）
  ├── auto params → 自动生成值（page=1, limit=10, ...）
  ├── manual params → 用户回答 → 回退 default → example
  └── context_ref params → 同上
```

**LLM 使用范围**：仅在参数分类阶段用于不确定参数。其余阶段全部是确定性规则。这是"用 LLM 辅助而非完全依赖"的设计思路。

**LangGraph Agent 模式**（`ai_agent/agent.py`）:

```
ImportAgent (StateGraph)
  ├── parse_document_node → classify_node → generate_node → save_node
  ├── LLM 驱动路由: 调用 LLM 决定下一步动作
  ├── ask_user_node: 向用户提问（需要用户输入时暂停）
  ├── error_node: 错误处理
  └── DjangoCheckpointSaver: 持久化状态到数据库，支持中断恢复
```

当前实际生产路径走的是 `views.py:AIImportViewSet` 的 REST API 流程（7 步），LangGraph Agent 是另一条实现路径。

### 5.3 UI 自动化 AI Agent（ui_automation）

**基于 browser-use 库 + LangChain**:

```python
BaseBrowserAgent (ai_base.py:937)
  ├── analyze_task() — 任务分解为子步骤
  ├── run_task() — Agent 主循环（最多 100 步）
  │   ├── Controller 自定义操作（完成、关闭标签页、更新状态）
  │   ├── on_step_end 回调 → 进度追踪 + 自动切换标签页
  │   └── Agent 状态 → LLM 决策下一步 → 浏览器操作
  └── run_full_process() — 分析 + 执行组合
```

**关键实现细节**：
- **Monkey-patching**：对 browser-use 库进行大量运行时补丁（JSON 响应修复、参数别名、超时保护）
- **模型兼容**：支持 DeepSeek、Qwen、SiliconFlow 等；Kimi 需特殊处理（temperature=1.0）
- **Chrome 集成**：自动发现本地 Chrome 或下载 webdriver

### 5.4 AI 聊天助手（assistant）

**Dify 平台代理**：最简单的 AI 集成，将用户消息透传给 Dify API，返回 Dify 的 AI 回复。支持会话上下文（通过 Dify conversation_id）。

---

## 六、AI 角色与模型配置总览

| 角色（role） | 所属模块 | 调用方式 | 典型用途 |
|-------------|---------|---------|---------|
| writer | requirement_analysis | 直接 API | 测试用例生成 |
| reviewer | requirement_analysis | 直接 API | 测试用例评审 |
| vision | requirement_analysis | 直接 API (LVM) | 图片转文本描述 |
| data_generator | requirement_analysis | 直接 API | 测试数据生成 |
| field_classify | requirement_analysis | 直接 API | 字段分类 |
| browser_use_text | ui_automation | LangChain | 浏览器自动化 |
| browser_use_vision | ui_automation | LangChain | 浏览器自动化(视觉) |
| api_import | api_testing | 直接 API | API 参数分类 |

---

## 七、架构模式特征

### 7.1 共同模式

1. **统一的 AI 配置层**：所有模块共享 `AIModelConfig`，通过 role 区分场景
2. **多阶段管线**：生成 → 评审 → 改进，每个阶段独立调用 LLM
3. **SSE 流式支持**：requirement_analysis 和 api_testing 支持 Server-Sent Events
4. **确定性 fallback**：LLM 失败时有确定性逻辑兜底（如启发式分类、模拟数据）
5. **Python + 直接 HTTP 调用**：除 browser-use 外，不使用 LangChain/LlamaIndex 等框架

### 7.2 AI 的使用哲学

- **LLM 做分类和生成，不做决策和控制**：参数分类用 LLM 但回退到启发式规则；请求生成完全确定性
- **多阶段而非单次调用**：生成 → 评审 → 改进 三段管线比一次生成质量更高
- **人工审核节点**：用户回答问题、确认结果，AI 不替代人工判断

### 7.3 当前已知限制

- 全部使用 OpenAI 兼容 API，不支持 Anthropic/Claude
- api_testing AI 导入 body 只支持单层 JSON properties
- browser-use 库需要大量 monkey-patch 才能稳定工作
- ai_models.py 中存在与 models.py 重复的遗留代码
