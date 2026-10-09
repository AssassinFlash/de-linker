# #12 站点外壳

## 改动清单
1. **页头与页脚**（LiveCanvas 页眉页脚模板，经 WP 后台或迁移脚本改）："Plan with Linker" 区块只剩两张卡：Genie（"Genie - Linker's AI assistant"，一句功能描述）与 Solution Configurator / Lösungskonfigurator（功能描述里包含 "Roof detail / Dachdetails" 一句）；移除 Site Detail 卡与链接；"Products" 菜单文案照旧。
2. **跳转**：`/design-canvas/` 与 `/de/design-canvas/`（及其德语别名）301 → 配置器页屋顶步（`/linker-planner/?step=roof` → 页面 slug 保持 `linker-planner`，标题改为 Solution Configurator / Lösungskonfigurator）。
3. **LiveCanvas 升级** 4.9.3 → 4.9.4（本地验证 `wp/v2/pages?page=2` 返回纯 JSON）。
4. **工具相关文案重写**：工具页标题、副标题、空态、按钮、提示、工具卡——每处单独写 EN/DE，对抗评审记录附 PR（AGENTS.md 文案规则）；营销十页正文不改。
5. **产品分类页筛选**接 #7 契约（相数、功率、用途、容量的 data-* 来自 SelectionFacts）。

## 验收
- [ ] 页头/页脚 EN/DE 对照截图（1440/390）；跳转 301 → 200。
- [ ] 分类页筛选结果与旧实现一致或仅因 #7 的修正而变，逐件列出。
- [ ] 文案评审记录（每处：初稿、评审意见、定稿）。
