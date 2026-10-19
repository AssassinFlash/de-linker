# GA4 与同意横幅站点接入

2026-10-19 重新施工。来源：[同意横幅与 GA4](https://github.com/AssassinFlash/de-linker/issues/201)。

## 结果与边界

用 CookieYes 免费版承接同意 UI，WP Consent API 承接类别，Site Kit 承接 Analytics。Basic：未同意统计时不加载 Google 标签、不发送测量或无 Cookie ping。Woo 原生订单来源保留，由其已有 WP Consent API marketing 接线管理。Search Console 连接和验证不得改变。

本票从当前 main、新线上快照和新实例开始。旧撤案 PR 的测试与截图不算本次证据。所有者 Google 账号设置只记录已核实状态；不把其他站点的数据流接进来。

## 状态合同

| 访客状态 | Google 标签/请求 | Woo sbjs | 必需功能 |
| --- | --- | --- | --- |
| 首次，无选择 | 无 | 无 | 保持 |
| 全部拒绝 | 无 | 无 | 保持 |
| 仅统计 | 放行，广告信号拒绝 | 无 | 保持 |
| 仅来源归因 | 无 | 记录来源 | 保持 |
| 全部同意 | 放行 | 记录来源 | 保持 |
| 撤回全部 | 停止后续请求，移除分析/归因 Cookie | 清除 | 保持 |

返回访客与跨 EN/DE 导航使用同一选择。撤回必须处理已经执行的 Google JS，单纯改 Cookie 不足以阻止其继续发事件；撤回后重新加载页面，重新进入 Basic 阻断状态。

## 原生能力核实

WooCommerce 11.2.0 `src/Internal/Integrations/WPConsentAPI.php` 的类别是 marketing；自带脚本动态更新追踪并清理来源 Cookie，先实测，不另造归因系统。

Site Kit 1.189.0、CookieYes 与 WP Consent API 的实际安装版本、白名单与阻断行为在本次验收记录确认。原生能力不能承接的部分才加窄接线，逐项记事实和原因。

## 文案与呈现

EN 与 DE 两套横幅，第一层同等接受、拒绝，统计和来源归因独立选择。披露 Google 接收方和境外处理；页脚有重新打开入口；隐私政策同步反映实际 Cookie 和保存期。新文案需对抗评审与操作者审稿确认。页面组成走原生 CMP 和 LC partial；站点样式走 WindPress。

## 验收

- 真实浏览器验证上表全部状态、返回访客、EN/DE 切换和撤回后下一页；保存请求与 Cookie 证据。
- 同一浏览器 1440 / 390 × EN / DE 逐状态视觉验收；横幅、页脚入口、政策变更列进变更台账，其他区域像素零差异。
- 配置可重放，部署校验保住 CMP、Consent Mode、Basic 阻断和 GSC。
- Spec + Standards 全 diff 评审，相关真实夹具及仓库检查，PR 与 CI。
- 线上复查无选择/拒绝、同意后 GA4 实时出现、撤回可用才关 playbook 票。

## 当前起点

2026-10-19 SSH 只读：线上无 CMP 和 WP Consent API，Site Kit 已激活，Analytics account/property/stream/measurement ID 全为空。尚未部署。

## 2026-10-19 用户更改选型与执行授权

用户明确要求 CookieYes，线上与本地同步安装、配置，由当前会话负责。因此取代旧 Complianz 实现；用户当期直接授权覆盖 AGENTS 中实现者不写生产的分工约束，仅限本票。生产仍先完整备份、后写入、后读回。使用官方 WordPress.org 3.5.7 免费包、独立存储模式，不接 CookieYes SaaS、不购买插件。

CookieYes 原生 Polylang 语言选择、原生双语 banner settings/contents、原生 WP Consent API 映射、原生脚本阻断/放行/撤回按钮。解析器插入的 Site Kit 标签先经 WP script_loader_tag 设 text/plain + data-cookieyes= cookieyes-analytics，防止仅靠 MutationObserver 时静态脚本已开始请求。Google 广告信号不随 Woo 的本地归因开启。

## 当前最终呈现与批准

操作者要求改善默认样式及德文密度，最终批准“可以了，英德两版一起上线”。最终截图见验收cookieyes目录内`*-redesign.png`与`de-*-refined.png`，旧默认截图只保留为迭代证据。站点字体/圆角通过WindPress卷consent.css管理；CookieYes只保留原生UI/存储/交互，页脚入口替代多余悬浮圆钮。原生德语错误关闭文案与英语ARIA标签已修正，ARIA引用实际译文标题。

## 2026-10-19 样式例外（业主裁定）

CookieYes 横幅是插件自己的界面。横幅、按钮和标题的颜色写在 CookieYes 原生设置里（`tools/migrate/201-consent.php`），不迁到 WindPress，也不改这些颜色。AGENTS.md §5 的「客户可见页面的样式只在 WindPress」约束站点页面，不约束第三方 CMP 的原生设置。`content/windpress/consent.css` 继续只管已批准的字体、圆角和页脚入口，不接管上述颜色。

## 2026-10-19 复核后的门

部署校验除 `/` 与 `/de/` 外还读取产品页 `/product/saj-b2-10-0-hv1/` 与 `/de/produkt/saj-b2-10-0-hv1/`。这些未带同意 Cookie 的读取里，分析同意是拒绝，页面必须带有 `id="google_gtagjs-js"`。

Handle 改名而 CookieYes 仍激活时，屏障按 `googletagmanager.com/gtag/js` 继续把标签设为 `text/plain`，并写一条 `linker-consent` 警告。部署校验仍因 handle 缺失而失败，不把 URL 兜底当成 handle 还在。

CookieYes 停用（没有 `CLI_VERSION`）时不改写标签，因为没有放行方；同一次请求写一条警告。部署校验因插件未激活、且标签没有被拦住而失败。

独立运行 `tools/migrate/201-consent.py --write` 必须带 `--backup-dir`。它先导出受影响的设置、横幅、分类、Cookie、两份隐私政策和 Site Kit consent 选项，再写入，再读回；读回仍有漂移则失败。部署路径 `configure_consent` 不使用这个参数：切换前的数据库快照是它的备份，每次部署写一次再读回一次，重复部署发送同一对调用。

隐私政策先写英文，再由原生 adopt 写入德文。写入前记下两页正文。任一步失败或读回与计划不一致时，两页都恢复成写入前的正文。
