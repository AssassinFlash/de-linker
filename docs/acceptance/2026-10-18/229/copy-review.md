# #229 页头文案核对与定稿

2026-10-18；本实现会话对照线上页头、仓库 LC partial 与 `.po` 术语核对。
本票没有新写、替换或缩短任何客户可见字符串。

| 位置 | 英语定稿（保持线上） | 德语既有定稿（保持线上） |
|---|---|---|
| 产品 | Products | Produkte |
| 解决方案 | Solutions | Lösungen |
| 工具入口 | Plan with Linker | Planen mit Linker |
| 服务 | Services | Dienstleistungen |
| 客户 | For Partners | Für Partner |
| 公司 | About | Über uns |
| 联系按钮 | Contact Linker | Linker kontaktieren |

## 初稿与评审意见

初稿选择：保留现有 EN/DE 原文，通过 WindPress 布局恢复德语桌面导航。

对抗检查：

- “Dienstleistungen”与“Linker kontaktieren”是否必须缩短？否。首条浏览器回归测试在 1440 失败；收回桌面导航左右留白后同条测试转绿，原文完整显示。
- 缩为“Service”或“Kontakt”是否更好？布局已经承载完整原文，缩词没有本票依据，不采用。
- 术语是否漂移？联系按钮与 `plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po` 和 `plugins/linker-tools/languages/linker-tools-de_DE_formal.po` 的 `Contact Linker` → `Linker kontaktieren` 一致。没有改动称谓、语气、承诺或工具名。
- 英语是否改动？LC partial、`.po`、PHP 字符串及脚本内客户可见字符串均无修改；像素验证单列在 README。

## 定稿

采用全部既有原文。由于没有德语新稿，不发生翻译或缩写，也没有待批准的新措辞。登录／创建账户链接归 #223，本票不改。

## PR #294 第 1 轮复核

固定 5px 留白未通过 1282–1287 的边界要求，也在大屏留下多余空间。改用流动留白后，
90 个扫描宽度的折叠状态一致，1300/1366/1440/1920 的最大可用留白测试通过，原文仍完整保留。
这一轮没有新增客户可见字符串，既有措辞和上述定稿继续适用。
