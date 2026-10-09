# #16 评审站整站验收与回归套件

## 环境
`just up review` + `just pull` 最新快照 + 全部新插件与服务（#7–#15 合并后的 main）。评审站是本地实例，不对外。

## 回归套件（`tests/e2e/`，Playwright，CI 可跑本地实例子集）
- Genie：R1–R14（`docs/acceptance/protocol.md` §5），EN/DE。
- 配置器：#14 的用例（8 户型、3 合规、工商业两路、屋顶步）。
- 商务链：注册 → 看价 → Lösungsentwurf → 询盘 → PI → 账户下载，EN/DE；邮件捕获断言。
- i18n：150 个德语 URL 200；同 slug；库存同步；`?lang=de` Store API。
- 产品分类页与产品页：筛选、价格隐藏、按钮文案。
- 页头页脚、跳转、sitemap、hreflang。

## 视觉验收（Computer Use）
全站主要页面（首页、分类页、产品页、Lösungsentwurf、提交页、账户四页、配置器三屏、Genie 四入口）× EN/DE × 1440/390，截图归档 `docs/acceptance/<date>/16/`，以设计稿与规格为基准，发现即修（本票内）。

## 验收
- [ ] 回归全绿、视觉验收无未修问题、本线 review 通过；#17 以此为前提。
