<link href="resume.css" rel="stylesheet"></link>

<div class="resume-header">
  <h1>王 鹏</h1>
  <div class="subtitle">测试开发工程师 · 7 年经验 · AI 测试方向</div>
  <div class="contact-info">
    <span>
      <img class="icon" src="assets/phone.svg" /> 18017087850
    </span>
    <span>
      <img class="icon" src="assets/location.svg" /> 上海
    </span>
    <span>
      <img class="icon" src="assets/email.svg" /> wangpeng@email.com
    </span>
    <span>🎂 26 岁 · 本科 · 软件工程</span>
  </div>
</div>

## 个人优势

- **AI 测试平台实战**：从 0 搭建 AI 智能测试平台，深度集成 LLM（DeepSeek / 通义千问），实现 AI 生成测试用例、AI Agent UI 自动化、AI 失败根因分析三大核心能力，已在交易所核心业务线落地。
- **自动化测试体系**：精通 pytest + requests + allure 接口自动化框架设计，pytest + selenium UI 自动化框架搭建，Jenkins Pipeline CI/CD 集成，三引擎分层覆盖（Selenium / Playwright / AI Agent）。
- **全链路质量保障**：具备交易所核心交易系统（永续合约 / 余币宝）、供应链 ERP（采购/库存/财务）、金融 C 端 APP 全生命周期测试经验，熟悉高并发资金安全场景的测试设计。
- **AI 工程化能力**：熟练使用 LLM API 集成（OpenAI 兼容 API / LangChain）、提示词工程、AIModelConfig 统一模型调度、流式 SSE 输出、browser-use Agent 定制开发。

## 工作经历

<div class="entry-header">
  <span class="title">Gate.io <span class="role">· 测试开发</span></span>
  <span class="date">2024.07 — 2026.06</span>
</div>

- 负责 AI 测试平台（基于 TestHub 框架）的 AI 模块设计与开发，覆盖 AI 用例生成、AI Agent UI 自动化、AI 失败分析三个方向。
- 设计统一 AIModelConfig 配置层，按 writer / reviewer / vision / browser_use_text 等 8 种角色管理模型调度，支持 DeepSeek / 智谱 / Qwen 等多模型切换。
- 实现 AI 生成→评审→改进三段管线，结合 LVM 图片转文本预处理，AI 生成用例评审通过率 85%，用例编写效率提升 60%。
- 集成 browser-use 实现 AI Agent UI 自动化，LLM 自主操控浏览器替代固定脚本，覆盖复杂 E2E 场景（登录→搜索→下单→支付）。
- 设计 AI 智能回归选择方案，基于代码变更影响范围推荐用例集，全量 2000+ 缩减到 800+，缺陷检出率保持 95% 以上。
- 搭建 Jenkins Pipeline + CI/CD 质量门禁，接口通过率 <95% 阻断发布，AI 失败根因分析实现 CI 失败自动分诊（环境/业务/数据问题分类）。

<div class="entry-header">
  <span class="title">西域供应链（上海）有限公司 <span class="role">· 高级软件测试工程师</span></span>
  <span class="date">2021.07 — 2024.06</span>
</div>

- 负责 Odoo ERP 全链路（采购→库存→财务→售后）功能测试与数据一致性保障，设计自动化对账脚本比对 WMS/ERP/财务三端数据。
- 从零搭建 pytest + requests + allure 接口自动化框架，覆盖核心业务接口，集成 Jenkins 每日定时执行并输出 Allure 报告。
- 主导搜索引擎 SEO 与电商算法推荐专项测试，构建 500+ 条测试集，覆盖分词、多级召回、动态权重排序全链路。
- 主导财务大数据平台 T+1 流水线质量保障，设计逐层计数比对方案（源头→抽取→清洗→加载），保障海量财务数据零丢失零重复。

<div class="entry-header">
  <span class="title">纬创软件（武汉）有限公司 <span class="role">· 测试工程师</span></span>
  <span class="date">2018.07 — 2021.05</span>
</div>

- 担任易金通（上海黄金交易所官方 APP）测试组长，主导测试计划制定、任务分配及进度把控。
- 使用 JMeter 完成性能测试方案设计与报告输出，Jenkins + Shell 自动化部署测试环境。

## 项目经历

<div class="entry-header">
  <span class="title">TestHub AI 智能测试管理平台</span>
  <span class="date">2025.01 — 2026.06</span>
</div>
<div class="entry-sub">AI 驱动的一站式测试平台 · 角色：AI 模块负责人</div>

- 基于 Django 4.2 + DRF + Vue 3 搭建后端 API 和前端展示层，AI 模块使用 httpx.AsyncClient 直调 OpenAI 兼容 API。
- **AI 生成用例**：设计生成→评审→改进三段管线，支持 PDF/Word/TXT 文档上传，LVM 预处理图片转文本描述后喂给 writer 模型生成用例，reviewer 模型评审后再由 AI 按意见修改。自动断点续写处理 token 截断问题。
- **AI Agent UI 自动化**：集成 browser-use 框架，LLM 自主分析 DOM 树决策操作路径，自定义 Controller（完成/关闭标签页/更新状态）+ on_step_end 回调做进度追踪。对国产模型做 11 处 monkey-patch 适配。
- **AI 失败分析**：聚合日志/报文/截图/console 错误，LLM 自动分类失败根因（环境/业务/数据），匹配历史相似失败，定位时间从 15 分钟缩短到 3 分钟。
- **统一模型调度**：AIModelConfig 按 role 管理 8 种模型角色，支持 DeepSeek v4-pro / v4-flash / 智谱 LVM 等模型灰度切换。

<div class="tag-list">
  <span class="tag">Django</span>
  <span class="tag">DRF</span>
  <span class="tag">Vue 3</span>
  <span class="tag">DeepSeek</span>
  <span class="tag">LangChain</span>
  <span class="tag">browser-use</span>
  <span class="tag">pytest</span>
  <span class="tag">Allure</span>
</div>

<div class="entry-header">
  <span class="title">Gate.io 交易所核心交易链路测试</span>
  <span class="date">2024.07 — 2026.06</span>
</div>
<div class="entry-sub">永续合约 + 余币宝 · 角色：测试开发</div>

- 负责永续合约核心交易链路测试：资金费率 8 小时结算、标记价格计算、强平清算（普通强平/阶梯强平/穿仓/高并发排队）。
- 负责余币宝全链路测试：申购赎回、自动赚币定时划转（每日 2:30/15:30 UTC）、利率市场化匹配、数据一致性对账。
- 设计自动化对账脚本，逐笔比对数据库余额/缓存快照/用户流水三端一致性，上线前发现缓存更新时序问题，避免资损。
- 全链路性能压测（JMeter），发现数据库连接池瓶颈和慢 SQL，优化后 TPS 从 500 提升到 1200+。

<div class="tag-list">
  <span class="tag">Python</span>
  <span class="tag">pytest</span>
  <span class="tag">JMeter</span>
  <span class="tag">MySQL</span>
  <span class="tag">Redis</span>
  <span class="tag">Kafka</span>
</div>

## 教育经历

<div class="entry-header">
  <span class="title">电子科技大学 · 软件工程 · 本科</span>
  <span class="date">2019 — 2021</span>
</div>

## 技能清单

<div class="skill-line"><span class="label">AI 能力</span>LLM API 集成 · 提示词工程 · AI Agent · 多模型调度 · LangChain · LVM 视觉模型</div>
<div class="skill-line"><span class="label">测试开发</span>自动化框架设计 · CI/CD 集成 · 质量门禁 · 测试平台开发 · 数据对账 · 性能压测</div>
<div class="skill-line"><span class="label">后端开发</span>Python · Django / DRF · Celery · RESTful API · SSE 流式 · HTTPX</div>
<div class="skill-line"><span class="label">前端开发</span>Vue 3 · Element Plus · Pinia · Axios · JavaScript</div>
<div class="skill-line"><span class="label">自动化测试</span>pytest · requests · Selenium · Playwright · Allure · Appium</div>
<div class="skill-line"><span class="label">CI/CD & 工具</span>Jenkins · Docker · Git · JMeter · Grafana · SonarQube</div>
<div class="skill-line"><span class="label">数据库</span>MySQL · PostgreSQL · Redis · Hive SQL</div>
