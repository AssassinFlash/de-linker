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

## 回归套件入口（2026-10-11，本段落地）
`tests/e2e/`（Playwright，独立 npm 包）：`just e2e <实例名> [playwright 参数]`，实例先按 §环境 建好（`just up` + `just pull load … --live-code` + `just serve`）。套件连的是 `~/de-linker-local/instances.toml` 里登记的实例端口，`just check` 里的 `e2e-check` 跑它的类型与格式（跑不动实例的部分不进门）。

- `specs/genie.spec.ts`：R1–R14（EN/DE，真模型 deepseek-flash）＋ Jev→DeepSeek 级联逐问判分（`services/genie/eval/judges/score.py`，判据即 #13 试点）。
- `specs/genie-dock.spec.ts`：披露句、商品页芯片（R13，带 product_id）、登录客户的询盘（R7）、刷新后的线程恢复。
- `specs/configurator.spec.ts`：8 户型、3 合规、工商业两路、屋顶步、设计报告 PDF。
- `specs/commerce.spec.ts`：注册→看价→Lösungsentwurf→询盘→后台出 PI→账户下载（EN/DE），邮件捕获断言。
- `specs/i18n.spec.ts`：150 德语 URL（经 `just pull check-urls` 请求快照自己的德语 sitemap）、同 slug、库存镜像、`?lang=de` Store API。
- `specs/catalogue.spec.ts`：分类页筛选、隐价、按钮文案（访客/登录）。
- `specs/chrome.spec.ts`：页头页脚命名、301、sitemap、hreflang。

**待主线终态的部分在套件里以 `pending-main` 标注**（运行时 skip 并写明原因），不静默删除：商品页 Genie 芯片（模板侧）与 hreflang 的旧站点残留（快照 SEOPress 数据）。
