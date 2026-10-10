# #12 站点外壳

## 改动清单
1. **页头与页脚**（LiveCanvas 页眉页脚模板，经 WP 后台或迁移脚本改）："Plan with Linker" 区块只剩两张卡：Genie（"Genie - Linker's AI assistant"，一句功能描述）与 Solution Configurator / Lösungskonfigurator（功能描述里包含 "Roof detail / Dachdetails" 一句）；移除 Site Detail 卡与链接；"Products" 菜单文案照旧。
2. **跳转**：`/design-canvas/` 与 `/de/design-canvas/`（及其德语别名）301 → 配置器页屋顶步（`/linker-planner/?step=roof` → 页面 slug 保持 `linker-planner`，标题改为 Solution Configurator / Lösungskonfigurator）。
3. **LiveCanvas 升级** 4.9.3 → 4.9.4（本地验证 `wp/v2/pages?page=2` 返回纯 JSON）。
4. **工具相关文案重写**：工具页标题、副标题、空态、按钮、提示、工具卡——每处单独写 EN/DE，对抗评审记录附 PR（AGENTS.md 文案规则）；营销十页正文不改。
5. **产品分类页筛选**接 #7 契约（相数、功率、用途、容量的 data-* 来自 SelectionFacts）。
6. **产品页模板**（新插件的 Woo 单品模板覆写，LiveCanvas 不参与。**2026-10-10 方向反转（PR #55）**：产品页与商城/购物车/结账/账户页改走 LiveCanvas 动态模板（lc_dynamic_template + is_shop_page 等 meta，官方 starter 底稿），归 #54——本项"LiveCanvas 不参与"与模板覆写的呈现本体已废止；#12 交付的机制（分类筛选、原生字段优先、门店文案）由 #54 的模板继续消费）：图库、简介、正文只来自 Woo 原生字段（维护人员在标准编辑器改了就生效——旧票 189 的意图）；关键数字来自 #7 契约；参数表来自产品属性与图值（`_tv_legacy_acf_json` 里的参数表/卖点在 #8 迁移时写入产品属性与一个 `linker_specs` 元框，之后只在标准编辑器维护）；FAQ 来自 #15 的字段；文档列表来自产品文档；按钮与价格按 #11；Genie 产品页芯片按 #13。EN/DE 由 #9 的德语对象提供。
7. **营销页交互**：五页内容模块增加桌面悬停切换，点击、键盘、触屏行为不变，不改文案（旧票 192）。
8. **页头菜单图片懒加载**：隐藏菜单的大图在打开菜单时才加载，比例与清晰度不变（旧票 193）。

## 验收
- [ ] 页头/页脚 EN/DE 对照截图（1440/390）；跳转 301 → 200。
- [ ] 分类页筛选结果与旧实现一致或仅因 #7 的修正而变，逐件列出。
- [ ] 文案评审记录（每处：初稿、评审意见、定稿）。
- [ ] 产品页：在标准编辑器改图库顺序、简介、正文并保存 → 前台与 `wc/store/v1/products/<id>` 立即采用；只改价格不影响图文。
- [ ] 五页内容模块：悬停切换生效，键盘与触屏回归通过；菜单打开前网络面板无菜单大图请求。
