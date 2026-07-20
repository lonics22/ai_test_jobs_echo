# TestHub AI 测试平台 — 面试准备文档

---

## 一、项目概况

### 1.1 项目定位
一站式 AI 驱动的测试管理平台，覆盖**需求分析 → 用例生成 → 评审修订 → 自动化执行 → 报告输出**全流程。

### 1.2 技术栈
| 层级 | 技术 |
|------|------|
| 后端框架 | Django 4.2 + Django REST Framework |
| 前端框架 | Vue 3 + Element Plus + Vite |
| 数据库 | MySQL 8.0 + Redis（缓存/Celery Broker） |
| 异步任务 | Celery + WebSocket（Channels） |
| AI 调用 | httpx 异步 HTTP（OpenAI 兼容接口） |
| UI 自动化 AI | browser-use + LangChain + Playwright |
| APP 自动化 | Airtest + Allure |
| API 文档 | drf-spectacular（Swagger / ReDoc） |

### 1.3 核心模块

| 模块 | 功能 |
|------|------|
| users | JWT 双 Token 认证、短信/密码/SSO 登录、五级角色权限 |
| projects | 项目管理、成员管理、环境变量 |
| testcases | 测试用例 CRUD、Excel 批量导入、步骤化、标签版本关联 |
| executions | 测试计划、执行追踪（passed/failed/blocked/retest） |
| reviews | 评审流程（4 态流转）、模板、多人分配、检查清单 |
| **requirement_analysis** | 需求文档解析、AI 分析/生成/评审、LVM 视觉、流式输出 |
| **api_testing** | HTTP/WebSocket 测试、断言系统、定时任务、AI 导入 |
| **ui_automation** | Playwright + Selenium 双引擎、元素库、POM、AI Browser-Use |
| **app_automation** | Airtest 框架、设备管理、组件化场景编排 |
| **data_factory** | 51 个造数工具（测试数据/JSON/加解密/编码等 7 大类） |
| assistant | Dify 智能助手集成 |
| reports | 执行/汇总/趋势 3 种报告 |
| analytics | 埋点事件统计（条件启用） |

### 1.4 数据流
```
用户上传需求文档 (PDF/Word/TXT/MD)
  → DocumentProcessor 提取文本 + 内嵌图片
    → LVM 预处理（图片替换为文字描述）
      → AI 分析 → 结构化需求列表
        → AI Writer 生成测试用例（流式）
          → AI Reviewer 评审
            → AI 修订 → 最终用例
              → 保存到测试用例模块 / 导出
```

---

## 二、AI 实现方式详解

### 2.1 统一 AI 调用架构

所有 AI 调用通过 `AIModelService`（`apps/requirement_analysis/models.py`）统一接入，核心方法是：

```python
# 非流式调用
AIModelService.call_openai_compatible_api(config, messages)

# 流式调用（异步生成器）
AIModelService.call_openai_compatible_api_stream(config, messages, callback)
```

**特点：**
- 所有模型（DeepSeek / Qwen / SiliconFlow / OpenAI / Anthropic / 智谱等）统一走 OpenAI 兼容接口
- `build_openai_compatible_url()` 智能补全 `/v1/chat/completions` 路径
- 支持 `Authorization: Bearer` 和 `api-key` 两种认证方式
- 超时配置：连接 60s、读取 900s（15 分钟），支持大文档生成

### 2.2 流式输出 + 自动续写

`call_openai_compatible_api_stream` 实现了完整的流式生成机制：

```
用户请求 → 创建 TestCaseGenerationTask → 后台线程开始生成
  → 流式调用 API（SSE）
    → 每个 chunk 实时写入 stream_buffer
      → 前端 SSE 轮询 /stream_progress 接口拉取增量内容
```

**自动续写机制（解决长文档截断）：**
1. 检测到 `finish_reason = 'length'` 时触发续写
2. 将已生成内容作为 assistant 消息追加到对话历史
3. 添加 "请继续输出" 的 user 指令
4. 重新发起 API 调用，最多续写 5 次
5. 整个流程对前端透明，前端只看到持续流出的内容

**关键代码位置：** `models.py:623-751`

### 2.3 三阶段生成流程

`TestCaseGenerationTaskViewSet.generate`（`views.py:1526`）创建后台线程执行：

```
Phase 1 - 生成 (generating)：
  [可选] LVM 预处理 → AI Writer 流式生成用例 → 存入 generated_test_cases

Phase 2 - 评审 (reviewing)：
  AI Reviewer 评审用例 → 输出评审报告 → 存入 review_feedback

Phase 3 - 修订 (revising)：
  AI 根据评审意见修订 → 输出最终用例 → 存入 final_test_cases
```

三个阶段均可选配（通过 `GenerationConfig` 控制 `enable_auto_review`）。

### 2.4 LVM 视觉模型集成

`AIModelService.preprocess_images`（`models.py:1307`）：

```
需求文本中的 ![alt](url) 
  → 正则提取所有图片标记
    → 并发下载图片（本地 media 或远程 URL）
      → 转为 base64
        → 调用 multimodal API（image_url + text）
          → 返回描述文本替换图片标记
```

- 使用 `role='vision'` 的 `AIModelConfig`
- 提示词来自 `docs/tester_vision.md`：识别是流程图还是原型图，描述内容
- 并发处理所有图片（`asyncio.gather`），失败图片不影响整体流程
- 支持本地 `/media/` 路径和远程 URL

### 2.5 Prompt 提示词体系

| 角色 | 文件 | 用途 |
|------|------|------|
| writer | `docs/tester.md` | 用例编写专家，10 年经验 QA，生成 Markdown 表格格式用例 |
| reviewer | `docs/tester_pro.md` | 评审专家（Test Architect），输出评分 + 问题列表 + 改进建议 |
| vision | `docs/tester_vision.md` | 视觉模型，识别流程图/原型图并描述内容 |
| data_generator | `docs/tester_data_gen.md` | 测试数据生成模板 |
| field_classify | `docs/tester_field_classify.md` | API 参数分类（auto/manual/context_ref） |

**特点：**
- Prompt 存储在数据库中（`PromptConfig` 模型），前端可动态编辑
- 默认值从 `docs/` 目录加载，`PromptConfigViewSet` 的 `load_defaults` 动作读取
- 每种角色一次只允许一个活跃配置

### 2.6 模型配置体系

`AIModelConfig`（`models.py:18`）：

```python
model_type = 'deepseek' | 'qwen' | 'siliconflow' | 'zhipu' | 'xiaomi' | 'other'
role = 'writer' | 'reviewer' | 'browser_use_text' | 'vision' | 'data_generator'
```

- 每种角色独立配置，可以 writer 用 DeepSeek、reviewer 用 Qwen
- 同一角色只有一个活跃配置
- 支持 `max_tokens`、`temperature`、`top_p` 参数独立调节

---

## 三、AI Agent 用法（Browser-Use 集成）

### 3.1 架构层次

```
┌─────────────────────────────────────────┐
│  AICaseViewSet.run (views.py:2948)      │  ← HTTP 入口
│  创建 AIExecutionRecord                 │
│  启动后台线程                           │
├─────────────────────────────────────────┤
│  run_full_process_sync (ai_agent.py)    │  ← 同步桥接
│  asyncio.run(run_full_process(...))     │
├─────────────────────────────────────────┤
│  BaseBrowserAgent (ai_base.py:937)      │  ← 核心 Agent
│  analyze_task() → 拆分子任务            │
│  run_task() → 执行子任务                │
├─────────────────────────────────────────┤
│  browser-use Agent + Controller         │  ← 第三方框架
│  LangChain ChatOpenAI → LLM            │
│  Playwright → 浏览器控制               │
└─────────────────────────────────────────┘
```

### 3.2 任务拆解（Task Decomposition）

`BaseBrowserAgent.analyze_task()`（`ai_base.py:1323`）：

1. 尝试从任务描述中提取显式编号的步骤（`1. ... 2. ...`）
2. 如果步骤过多（>=10）或步骤过于复杂，调用 LLM 重整（`_model_break_down_task`）
3. 合并机械性碎步骤（如 "打开浏览器 → 输入 URL" 合并为 "访问 URL"）
4. 返回结构化的 `[{id, description, status}]` 列表

### 3.3 执行流程（Run Task）

`BaseBrowserAgent.run_task()`（`ai_base.py:1485`）：

```
1. 验证 LLM 连通性（_verify_execution_llm）
2. 清理僵尸 Chrome 进程（_cleanup_zombie_chrome）
3. 创建 Controller，注册自定义动作：
   - done() → 标记任务完成
   - close_tab() → 关闭标签页 + 自动切回来源页
   - mark_task_complete/failed/skipped(task_id)
   - update_task_status(task_id, status)
4. 构建增强版 Prompt（包含子任务列表和执行规则）
5. 创建 BrowserProfile → 启动 Chrome
6. 创建 browser-use Agent → 执行
7. on_step_end 回调追踪执行状态
```

### 3.4 子任务状态追踪机制

这是最关键的面试话题。通过 `planned_tasks` 列表追踪：

```python
[
  {"id": 1, "description": "访问登录页面", "status": "completed"},
  {"id": 2, "description": "输入用户名密码", "status": "completed"},
  {"id": 3, "description": "点击登录", "status": "in_progress"},
]
```

**状态更新的方式：**
1. **主动标记**：LLM 调用 `mark_task_complete(task_id=N)` 动作
2. **被动补齐**：`backfill_prior_pending_tasks()` 在检测到跳号时自动补齐前序任务
3. **异常处理**：登录失败超过 3 次自动 `mark_task_failed`，基础设施错误自动终止

**on_step_end 回调（`ai_base.py:1721`）**：
- 每步执行后解析 LLM 输出中的 action
- 检测 `mark_task_complete` 等状态更新动作
- 检查所有子任务是否都已终端状态 → 自动停止 Agent
- 检测认证失败信号 → 累计 3 次后标记失败并停止

### 3.5 大量 Monkey-Patching

这是容易在面试中被问到"你做了什么深度工作"的地方。`ai_base.py` 对 browser-use 做了 11 处 monkey-patch：

| Patch | 解决的问题 |
|-------|-----------|
| `Agent.get_model_output` | LLM 返回格式不稳定（thinking 标签、字符串 action、参数名不一致） |
| `TokenCost.register_llm` | LangChain 消息格式兼容性 |
| `BrowserSession.connect` | Windows CDP 连接重试机制 |
| `ToolRegistry.execute_action` | 映射 switch_tab 等 action 名，点击后加 1.5s 延迟 |
| `ScreenshotWatchdog` | 截图超时全局修复（3s 超时 + 1x1 占位） |
| `ClickElementAction.__init__` | 统一 click 参数格式为 `{index: N}` |
| 其他 | DOMWatchdog、verdict 属性缺失、端口号固定 |

**为什么需要这么多 patch？**
- browser-use 是一个较新的框架，对中文 LLM（DeepSeek/Qwen）的兼容性不够
- 不同 LLM 输出格式差异大（`<thinking>` 标签、字符串 `mark_task_complete(task_id=8)` 等）
- 中文 UI 框架（Element Plus）的渲染需要额外等待时间

### 3.6 关键设计决策

| 决策 | 原因 |
|------|------|
| `use_vision=False` | 视觉模式不稳定 + 成本高，仅用文本 DOM 模式 |
| 限制 `max_actions_per_step=10` | 平衡效率与准确性 |
| 后台线程而非 Celery 执行 AI | 简化架构，避免 Celery 队列延迟 |
| DB 轮询而非 WebSocket 推送进度 | 简化前端实现，降低复杂度 |

---

## 四、API 测试 AI 导入

### 4.1 三阶段管线

`AIImportViewSet`（`apps/api_testing/views.py`）实现：

```
Phase 1 - 文档解析：
  支持 Swagger 2.0 / OpenAPI 3.0 / Postman / HAR 格式
  doc_parser.detect_format() → parse_document()

Phase 2 - AI 分析：
  analyze_endpoints() → 参数分类（auto/manual/context_ref）
  generate_questions() → 生成需要用户确认的问题

Phase 3 - 请求生成：
  generate_requests() → 结合 AI 分类 + 用户回答 → 生成 ApiRequest
  save() → 可选自动按 OpenAPI tags 结构化组织
```

### 4.2 AI 参数分类策略

混合策略：先启发式规则，再 LLM 兜底
- **规则匹配**：`page/offset/limit` → auto，`id/*_id/token/api_key` → context_ref
- **LLM 兜底**：3 个以上不确定参数时调用 LLM 分类，角色 `field_classify`

---

## 五、常见面试问题 & 回答

### Q1: 这个项目里 AI 的准确率怎么样？怎么保证质量？

> 从几个维度保证：一是提示词工程，writer/reviewer 提示词经过多轮迭代，约束输出格式和覆盖维度；二是自动评审机制，生成后自动走 review 环节，评分低的触发修订；三是 LVM 预处理，需求文档里的图片先被识别描述后再进入 LLM，避免模型"看不到图"导致分析偏差。生成有效率 85%+，对质量不高的用例，评审环节基本能兜住。

### Q2: 流式输出怎么实现的？遇到长文档截断怎么办？

> 基于 OpenAI SSE 协议实现的流式生成。每个 chunk 通过回调写入数据库的 `stream_buffer` 字段，前端通过 SSE 端点轮询增量拉取。关键在于自动续写：检测到 `finish_reason=length` 时，将已生成内容追加到对话历史，自动请求模型继续输出，最多续写 5 次。这样长文档生成对前端是透明的，用户体验是连续流出的效果。

### Q3: Browser-Use AI Agent 和传统 Selenium 自动化有什么区别？

> 传统 Selenium 需要人工编写完整脚本：定位元素、操作、断言，维护成本高。AI Agent 只需要用自然语言描述任务（如"在百度搜索 Claude，点开第二条结果"），模型理解页面 DOM 后自主决策操作步骤。我们做了大量 monkey-patch 来解决中文模型输出不稳定的问题（格式校验、参数归一化、重试机制）。但 AI 模式的执行成功率约 70%，适合探索性测试和快速验证，回归场景还是用传统脚本更可靠。

### Q4: 这么多 AI 模型怎么管理和切换的？

> 通过 `AIModelConfig` 统一管理，每种角色独立配置。核心是统一用 OpenAI 兼容接口调用，`build_openai_compatible_url()` 智能补全 API 路径。切换模型只需在界面上改配置，不改一行代码。实际使用中 writer 通常用 DeepSeek（性价比高），reviewer 用 Qwen（评审更严格），Browser Use 用 SiliconFlow 的 Qwen 系列（对中文理解好）。

### Q5: 你在这个项目里主要负责什么？

>（根据实际情况调整）负责核心 AI 模块的迭代优化，包括：流式输出和自动续写机制的实现、LVM 视觉模型集成、Browser-Use AI Agent 的稳定性改进（monkey-patch 适配中文模型）、AI 导入的文档解析和参数分类策略。原有框架基础上做了大量稳定性增强和功能扩展。

### Q6: AI 调用会不会很慢？怎么优化的？

> 几种手段：一是流式输出让用户边看边等，感知延迟降低；二是使用异步 httpx 不阻塞线程；三是超时配置 900 秒 + 自动续写，保证大文档一定能生成完；四是 LVM 预处理用 `asyncio.gather` 并发处理图片。另外 cache 机制避免重复调用。

### Q7: Browser-Use 模式你们用的是什么视觉模型？准确率怎么样？

> 实际上 UI 自动化模式只用文本模式（`use_vision=False`），基于 DOM 解析来理解页面结构。视觉模式在 browser-use 层面是关掉的，因为视觉模式成本高、速度慢、且在中文页面上准确率不够稳定。视觉模型我们只在需求分析阶段用（LVM 识别文档图片），跟 Browser-Use 是两套逻辑。

### Q8: 数据工厂具体是怎么实现的？

> 51 个工具分 7 大类：测试数据（姓名/手机号/身份证/银行卡/营业执照等 11 种合规数据）、JSON 工具、字符工具、编码工具、随机工具、加解密工具、Crontab 工具。底层用 `fakerx` 库生成合规数据，银行卡号和营业执照号有独立的规则引擎实现校验位。支持跨模块数据引用，比如 API 测试可以引用数据工厂生成的身份证号。

### Q9: 项目的权限模型怎么设计的？

> 五级角色（owner/admin/developer/tester/viewer），基于 Django 的 permission 框架 + DRF 的 permission_classes。项目成员通过 `ProjectMember` 中间表关联。前端路由也有权限守卫配合。

### Q10: AI Import 的文档解析支持哪些格式？

> Swagger 2.0（JSON/YAML）、OpenAPI 3.0、Postman Collection v2.1、HAR 4 种格式。自动检测格式后解析成统一的结构化端点列表，然后走 AI 参数分类 + 用户确认 → 生成请求的完整流程。对 100+ 端点的超大 API 文档也能处理，LLM 只处理 LLM 擅长的分类问题，结构化解析靠规则引擎。

### Q11: 你觉得怎么写一个好的 prompt？

> 我总结成一个框架叫 **R.O.L.E.S.T**，六个部分：
> 
> **R — Role（角色）**：给 AI 明确的身份，它马上进入状态。"你是一个资深的交易所测试工程师"比"帮我写测试用例"效果好得多。角色设定了 AI 的知识范围和回答风格。
> 
> **O — Objective（目标）**：描述你要什么，越具体越好。不说"测一下接口"，说"为 POST /api/earn/subscribe 生成接口测试用例，覆盖正常申购、重复申购、金额超限、币种不支持四个场景"。
> 
> **L — Level（层级要求）**：控制输出格式和颗粒度。"每个用例包含：用例ID、前置条件、测试步骤、预期结果""步骤用 Given-When-Then 格式"。你不说层级，AI 默认给最通用的。
> 
> **E — Example（示例）**：给 1-2 个例子，比写一百字描述都有用。AI 看例子就懂了你要的格式和深度，不需要你解释。
> 
> **S — Source（参考材料）**：给 AI 开卷考试的材料，不让它空想。接口文档、业务规则、历史 Bug 模式，你给的信息越精确，它乱编的空间越小。这是抗幻觉的第一道防线。
> 
> **T — Tone（约束）**：收尾加一句边界条件。"不要编造不存在的接口和字段""不确定的地方标注[需确认]而不是自己假设"。
> 
> 另外我觉得最重要的是——**好的 prompt 不是写出来的，是迭代出来的**。第一次拿到结果后看哪里不满意，refine 再跑一轮。不要期望一次性写完美，快速出结果 → 发现问题 → 改进 prompt → 更好结果，这个循环才是关键。

### Q12: 大模型生成测试用例有幻觉，你怎么处理的？

> 我从五个层面来处理，每层解决一部分问题：
>
> **第一层，RAG + 上下文锚定（成本最低，效果最好）**：不让 LLM 空想，把需求文档、接口定义、业务规则作为上下文注入 prompt。你给的信息越精确，它编造的空间越小。本质上就是给 LLM 开卷考试。
>
> **第二层，分阶段管线**：我的 TestHub 是三段式——生成 → 评审 → 改进。评审阶段的 prompt 专门检测幻觉：接口是不是真的存在、数值算得对不对、逻辑有没有矛盾。评审阶段本身就是一道幻觉检测关卡。
>
> **第三层，确定性校验（最核心）**：我写了一个校验模块，对 AI 输出的关键字段做硬编码检查——它引用的接口名，我在 API 定义表里查一遍；它写的数值，我用业务规则验一遍。这完全不依赖 LLM 自查，是确定性代码，零误判。比如用例里写了 `/api/earn/settle`，但实际根本没这个接口，直接标记幻觉。
>
> **第四层，结构化输出 + Schema 约束**：让 AI 输出 JSON 而不是自然语言，配合 JSON Schema 做格式校验。格式上的胡编乱造能堵住大部分。
>
> **第五层，置信度标注 + 人工抽查**：让 AI 对每个用例标注 HIGH/MEDIUM/LOW 置信度，LOW 的必须人工审。同时 20% 定量抽查，确保整体质量。
>
> 核心思路是：**没有任何一个技巧能独自解决所有幻觉，但多层防线叠在一起，每层过滤一部分，最后剩下的已经足够少。**

### Q13: 投屏演示 Vibe Coding，面试官想看什么？你有什么建议？

> 面试官真正想看的不是 AI 写代码有多快，而是三个能力：**能不能清晰描述需求给 AI（prompt 能力）、能不能判断 AI 输出对不对（review 能力）、能不能把 AI 纳入规范流程（工程思维）。**
>
> **Demo 选题建议**：结合我的背景，最适合的是 AI 生成测试用例的演示——给 Claude/GPT 一段需求描述让它生成用例，然后我 review 指出不足，refine prompt 拿到更好的结果。这个过程完整展示了我"指挥 AI → 审查 AI → 改进 AI"的能力。
>
> **准备 checklist**：
> - 提前测好 2-3 个 prompt，确保 AI 工具账号有额度
> - 准备好截图备份，以防网络不行
> - 关掉屏幕通知和隐私内容，桌面要干净
>
> **关键加分操作**：主动制造一个"修正"环节。第一轮 prompt 故意留个模糊点，AI 生成后指出来："这里没考虑到并发申购的场景，我需要补充"，然后 refine prompt 看 AI 怎么改进。这就展示了你有业务深度，不是无脑接受 AI 输出。
>
> **常用工具**：Claude Code 做 vibe coding 最常用的是——自然语言对话写代码（最核心）、Agent 模式一条命令完成多步操作（如"写测试覆盖这个文件的所有分支"）、Edit 选中代码段修改、不同模型切换（复杂任务用 Opus，简单问题用 Haiku）。投屏时重点展示"自然语言描述 → AI 写代码 → 你 Review → 迭代"这个闭环就够了。

### Q14: 如何评估和测试一个 AI Agent？

> AI Agent 跟传统软件不一样——输出不是确定的，同一个输入可能走不同的路径。所以评估不能只看最终结果，要从多个维度分层来测。
>
> **第一层：单步决策正确性（最基础）**
>
> Agent 的每一步都是一个决策（调用什么工具、参数对不对、是否该结束）。测试方法：构造特定上下文，让 Agent 必须做出某个决策，验证它选对了。比如给一个包含登录表单的页面，Agent 应该选择「输入用户名密码」而不是「跳转到其他页面」。这层是确定性最高的，可以做成自动化验证集。
>
> **第二层：完整任务成功率（核心指标）**
>
> 构造一批标准化任务场景，让 Agent 独立执行，统计成功率。比如 10 个 E2E 场景——登录→搜索→下单→支付，每个场景跑 5 次，统计最终完成率。注意去掉随机因素（固定 temperature=0），才能区分是 Agent 的问题还是模型随机的波动。
>
> **第三层：鲁棒性测试（最容易出问题的地方）**
>
> Agent 在实际环境中会遇到各种意外情况，这是测试重点：页面元素变了（按钮 ID 改了但语义没变）、网络超时或接口返回异常、中间步骤失败后能否恢复、上下文超长时能否正确 truncate、多标签页/弹窗/iframe 等复杂 UI。
>
> **第四层：安全性测试（AI 特有的风险）**
>
> Prompt 注入——页面上恶意文本诱导 Agent 执行非预期操作；数据泄露——Agent 会不会在日志里输出敏感信息；越权——Agent 能否访问不应访问的资源；工具误用——Agent 调用了不该调的工具（比如删库）。这层需要红队测试，模拟攻击者输入。
>
> **第五层：性能和成本评估**
>
> 执行时间——一个任务从开始到结束花了多久；Token 消耗——每次调 LLM 消耗多少 token，累计到任务完成的总额；成本换算——按模型单价算每个任务的成本。在 Gate.io，一个 browser-use 的 E2E 场景平均消耗 5000-8000 tokens，成本约 $0.02-0.05，比 Selenium 贵得多但胜在灵活。
>
> **第六层：一致性评估（非确定性带来的挑战）**
>
> 同一个任务跑 10 次，行为路径一样吗？成功/失败分布如何？Agent 的问题在于——可能 9 次都走对了路径，第 10 次突然抽风选了错误动作。所以不能只看一次结果，要统计多次分布。我一般要求每个测试场景至少跑 5 次，记录成功率和路径方差。
>
> **评估指标体系总结：**
>
> 核心指标：任务完成率（目标 ≥80%）、工具调用准确率（选对工具+参数正确）、执行时间（控制在 N 步以内）。辅助指标：Token 消耗/任务（成本控制）、人工干预率（越低越好）、失败模式分布（卡在哪一步最多，反哺优化）。安全指标：Prompt 注入成功率（目标 0%）、敏感信息泄露（目标 0%）。

---

## 六、架构图（文字版）

```
┌─────────────────────────────────────────────────────────────┐
│                       前端 Vue 3 + Element Plus              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ 需求分析  │ │ API测试  │ │ UI自动化 │ │ APP自动化     │  │
│  │ 页面组    │ │ 页面组   │ │ 页面组   │ │ 页面组        │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ 数据工厂  │ │ 配置中心 │ │ 测试用例 │ │ 执行与报告    │  │
│  │ 页面     │ │ 页面     │ │ 页面     │ │ 页面          │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST API (JWT Auth)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                     Django REST Framework                    │
│                                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌──────────────────────┐  │
│  │ requirement_│ │ api_testing │ │ ui_automation        │  │
│  │ analysis    │ │             │ │  ┌─────────────────┐ │  │
│  │  ┌────────┐ │ │  ┌───────┐  │ │  │ BaseBrowserAgent│ │  │
│  │  │AIModel │ │ │  │AI     │  │ │  │ browser-use     │ │  │
│  │  │Service │ │ │  │Import │  │ │  │ LangChain       │ │  │
│  │  │LVM     │ │ │  │       │  │ │  │ Playwright      │ │  │
│  │  │Stream  │ │ │  │       │  │ │  └─────────────────┘ │  │
│  │  └────────┘ │ │  └───────┘  │ └──────────────────────┘  │
│  └─────────────┘ └─────────────┘                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ app_auto │ │ projects │ │testcases │ │ data_factory  │  │
│  │ -mation  │ │          │ │executions│ │ (51 工具)     │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       MySQL 8.0    Redis        Celery
                     (Cache,     (Async Tasks,
                      Session)    Scheduled Tasks)
```

---

## 七、关键数据指标速查

| 指标 | 数据 |
|------|------|
| 后端模块数 | 16 个 Django App |
| 数据模型 | 50+ 个数据库模型 |
| AI 角色数 | 5 种（writer/reviewer/vision/data_generator/field_classify）|
| 支持模型提供商 | 6+ 种（DeepSeek/Qwen/SiliconFlow/OpenAI/Anthropic/智谱）|
| 数据工厂工具数 | 51 个（7 大类）|
| AI 用例有效率 | 85%+ |
| 需求到用例效率 | 提升约 80% |
| UI AI 执行模式 | 仅文本 DOM 模式（`use_vision=False`）|
| 流式续写上限 | 最多 5 次自动续写 |
| API 超时设置 | 连接 60s / 读取 900s |
