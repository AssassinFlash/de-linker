# document-library 族生产验收（2026-11-07）

8 状态 × EN/DE × 1440/390 全部在生产实测通过。证据：`library-states-batch1-20261107.json`（初始/切 tab/搜索/空态清除/rail）、`library-states-deep-20261107.json`（键盘建议）、`library-states-escape-lang-20261107.json`（Escape 可见性复核 + 语言切换 + 文档链接）。

- **initial**：7 个 tab（FAQ 202 / Documents 143 / Solutions / Services / Plan / Account / Contact，DE 名称独立）+ 39 卡 + 搜索框，EN/DE 结构对称。
- **switch-tabs-and-keyboard**：切 tab 写入 `?tab=documents` 且 aria-selected 正确。
- **search-results-and-live-count**：battery/batterie 命中 203，双语言一致。
- **search-empty-and-clear**：乱词出空态提示、无回显；清除恢复 39 卡。
- **suggestions-keyboard-selection-and-escape**：ArrowDown 驱动 `aria-activedescendant=linker-library-sug-0` 并高亮首条（EN "How are lithium battery system…" / DE "Wie werden Lithium-Batteriespe…"）；Escape 按可见性口径关闭建议框并保留查询（首测"未关闭"为隐藏元素误判，复核澄清）。
- **rail-and-mobile-chips**：49 个分类 rail/chips。
- **document-open-file-and-anchor**：Documents 面板可见下载链接 HEAD 200 `application/pdf`（如 `GW_BAT-C-208-261kWh_Datasheet_EMEA-DE_V1.1.pdf`）；zone 锚点落地 in-view。
- **filtered-results-language-switch**：hreflang 开关携带查询词（`?q=storage` ↔ `?q=speicher`）落地对侧，两侧卡片数对称（39/39）。

本地 e2e（faq-download.spec / library-visual-details.spec，针对本地实例）为回归层，不冒充线上证据；本批次为线上层。32 行 state-matrix 条目全部 `verified-production-20261107`。
