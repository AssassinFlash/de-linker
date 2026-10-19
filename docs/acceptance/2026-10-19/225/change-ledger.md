# #225 注册表单 · 裁定变更台账

授权：业主 2026-10-17 在 AGENTS.md §2 的裁定“注册表单：两步”（变体 B）与 #224 字段研究；该裁定取代 2026-10-15 验收原型的三段编号单页布局。本台账登记相对线上现状的全部客户可见变更。

对照：`before/` 为线上 de-linker.com 注册页（2026-10-19 只读截图）；`screens/` 为本地 c225（快照 20261019-0005）实现后同条件截图。EN/DE × 1440/390。

| # | 客户可见变更 | 裁定依据 | 边界 |
|---|---|---|---|
| 1 | 三段带编号（1 Company、2 Contact and address、3 Sign-in details）改为两段进度条：`Step 1 of 2 · Your company` / `Step 2 of 2 · You and your sign-in`；第 1 步公司，第 2 步您和登录 | 业主 2026-10-17 选定变体 B（#225 评论与 `docs/prototypes/2026-10-17-registration/DECISION.md`） | 仅注册卡；登录、忘记密码、重置、账户页不变 |
| 2 | 街道、邮编、城市移出注册；由 Proforma 请求页的原生 Woo 账单字段收 | 业主 2026-10-17（AGENTS.md §2）；#224 §0.2 | 历史地址仍可在后台账户页只读查看；结账/地址簿字段不变 |
| 3 | 业务类型由下拉改为三个单选块（Installer / EPC contractor / Distributor，DE 既有译名） | #224 §4.4（三个选项用下拉是公认差设计）；业主 2026-10-17 字段表 | 保存的 meta 值与既有三值完全一致，无数据迁移 |
| 4 | 国家下拉改为德国置顶、欧洲（Woo Europe 大洲）其次、其余最后，并启用 Woo 自带 selectWoo 搜索 | 业主 2026-10-17“全部国家，欧洲为重点”；#224 §8 | 全部国家仍开放；默认德国；无国家被排除 |
| 5 | 新增 `Company website` 字段；网站或 VAT ID 至少一项，上方一句说明用途 | 业主 2026-10-17；#224 §6.4 | VAT ID 字段与 VIES 检查保留；网站存为 `linker_company_website`，后台账户页与新客户通知自动显示 |
| 6 | 必填/选填标记、邮箱提示、网站格式错误、网站/VAT 组合错误、机器人/限流错误文案 | #225 完成标准；文案对抗评审 `copy-review.md` | 错误文案不透露防机器人机制；客户可见邮箱仍为 sales@de-linker.com |
| 7 | 多错误时 WooCommerce 通知由横排改为图标列 + 逐行消息 | 本票引入多字段同时报错，原单行布局在 500px 卡片内不可读（bug 修复） | 只影响 `.linker-auth` 卡内的列表式通知；单条通知与门禁样式不变 |

## 前后对照

| 状态 | 线上（before） | 本地（after） |
|---|---|---|
| EN 1440 第 1 步 | [before/live-en-1440.png](before/live-en-1440.png) | [screens/en-1440-step-1.png](screens/en-1440-step-1.png) |
| EN 390 第 1 步 | [before/live-en-390.png](before/live-en-390.png) | [screens/en-390-step-1.png](screens/en-390-step-1.png) |
| DE 1440 第 1 步 | [before/live-de-1440.png](before/live-de-1440.png) | [screens/de-1440-step-1.png](screens/de-1440-step-1.png) |
| DE 390 第 1 步 | [before/live-de-390.png](before/live-de-390.png) | [screens/de-390-step-1.png](screens/de-390-step-1.png) |

线上第 2 步与第 1 步同页（单页三段）；本地第 2 步截图见 `screens/<lang>-<width>-step-2.png`。错误态：`screens/<lang>-<width>-step-1-client-errors.png`、`-step-1-server-errors.png`、`-step-2-server-errors.png`。

## 不变的部分

注册卡的品牌面板、卡片圆角/阴影、字段高度与颜色、按钮、登录链接、页面页头页脚均沿用线上；页头、页脚、商城、产品、博客不属于本票。像素门只适用于复刻面；注册卡属裁定重设计，按变更台账逐状态验收，不做整页像素相等声明。
