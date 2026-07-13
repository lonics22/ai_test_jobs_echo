**Selenium：** 执行稳定约 98%，但对元素定位强依赖，前端改 className 就红，复杂场景半天到一天写脚本。

**browser-use：** 写 prompt 代替写脚本（几分钟），前端小改动不影响，但执行时间波动大，稳定性约 85%。

我的策略是 70% 回归用 Selenium（页面验证、数据校验），30% 复杂 E2E 用 browser-use（登录→搜索→下单→支付）。

踩坑记录：
- Kimi temperature 强制 1.0
- 标签页焦点丢失导致"幽灵点击"
- Chrome 僵尸进程堆积
