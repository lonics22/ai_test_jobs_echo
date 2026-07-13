设计了一个统一的 AIModelConfig 管理层，通过 role 区分场景。数据库里定义了 writer、reviewer、vision、data_generator、browser_use_text 等 8 种角色。

每个角色独立配置 provider / api_key / base_url / model_name / temperature / top_p，PromptConfig 支持版本管理。

调用方式两种：
- **requirement_analysis** 和 **api_testing** 用 httpx.AsyncClient 直调 OpenAI 兼容 API
- **ui_automation** 因为 browser-use 依赖走 LangChain ChatOpenAI 包装

切换模型不用改代码，页面上把 role 的 base_url 和 api_key 切一下就行。
