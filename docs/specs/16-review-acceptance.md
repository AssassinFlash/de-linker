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
- `specs/genie-dock.spec.ts`：披露句、商品页入口（R13，点工具行的 `[data-pdp-ask]`，随轮次带 product_id）、登录客户的询盘（R7，从常驻 dock 问）、刷新后的线程恢复。
- `specs/configurator.spec.ts`：8 户型、3 合规、工商业两路、屋顶步、设计报告 PDF。
- `specs/commerce.spec.ts`：注册→看价→Lösungsentwurf→询盘→后台出 PI→账户下载（EN/DE），邮件捕获断言。
- `specs/i18n.spec.ts`：150 德语 URL（经 `just pull check-urls` 请求快照自己的德语 sitemap）、同 slug、库存镜像、`?lang=de` Store API。
- `specs/products.spec.ts`：分类页筛选、隐价、按钮文案（访客/登录）。
- `specs/chrome.spec.ts`：页头页脚命名、301、sitemap、hreflang。

**待主线终态的部分在套件里以 `pending-main` 标注**（运行时 skip 并写明原因），不静默删除。2026-10-16 清账：本段原先点名的两处都已落到实跑——商品页 Genie 入口（R13 行改为点页面实际带的 `[data-pdp-ask]` 入口，芯片组不在 LC 产品模板上）、hreflang 的旧站点残留（快照 SEOPress 数据已不带线上自己的 alternates，断言改为硬判）；chrome.spec 的 301 落点依赖 `12-site-chrome.py` 迁移，未跑该迁移的实例以具名 skip 报出（README 的前置清单已补该步）。`genie-dock.spec.ts` 那一处 skip 的口径是 `pending-fixture`（既非主线欠行，也非迁移前置）：套件客户由 `products.spec.ts` 的 `ensureCustomer()` 在运行时自建，因此该行实例上跑过一遍套件后即转实跑；三种标注（`pending-main`/`pending-setup`/`pending-fixture`）的定义见 `tests/e2e/README.md`。

**判分记录落盘**（2026-10-11 修复轮）：级联的逐问记录写在实例目录下（`~/de-linker-local/<实例>/e2e-judge/<本地时间戳>/`，与 `mail/` 同级），`run/summary.json`、`run/jev.jsonl`、`run/deepseek.jsonl`、`run/cascade.jsonl` 在跑完后仍可查阅；判分开始的路径会打印在运行输出里。判分答案里的商品按角色分列（`This page's product:` 与 `Recommended products:` 两行，`linker_judges.turns.answer_with_offers` 是唯一实现）——R5 分歧的根因正是把「本页产品」与「推荐产品」压成一张清单。


## CI 随差异收敛

check.yml 先用实际 Git 差异选检查，并核实缩减范围内文件的类型、UTF-8 编码和非二进制内容。纯文档不安装运行环境；只修改既有 Commerce LC/CSS 文件及其模板合同测试时，执行原有 Presentation 合同；修改模板时保留德语、站内地址与 i18n-coverage 守卫，修改模板合同 PHP 测试时保留该文件的 PHPCS 和 PHPStan，并先核实基线已有成功检查。Planner、Engine、Genie 的独立包变化只运行对应包，Planner 的构建清单还必须证明非 Planner 产物未变；既有 Commerce 白名单变化保留 Commerce 与全部 native 组。共享、未知、重命名、改类型、其他运行代码、共享依赖或工作流改动，以及无法识别或无法证明基线的变化，仍执行完整检查与原生集成。界面变更的 Computer Use 验收照旧，不把 CI 选中范围当作视觉验收。

main 合并结果的完整 Git 树等于第二父提交时，仍须核实成功运行实际测试的合成提交：run-name 记录 github.sha，各 checkout 显式使用同一 SHA；解析其 Git tree 并与候选完整树严格比较，同时核对工作流 blob 相同、对应 attempt 的检查范围确为 full/scoped（push 可为 reuse），不把 docs-only 结果当运行基线。已通过独立门禁的 scoped PR 同时证明其完整基线与本次选中包，可作为后续局部 PR 的传递基线。只有这些证明齐全且该 PR head 最新运行已完成并成功时，才复用结果；失败、API 不可用、没有可核对结果或 Git 树不同均执行完整检查。唯一聚合门禁 `check` 重新计算差异与选择，要求选中任务成功、未选中任务确实跳过，并复验 scoped/reuse 证明；`mu-smoke` 是 native 分组任务。计划失败、取消或模式未知时最终门禁明确失败。计划写明选中或复用范围；不把未执行的用例写成新通过。手动 workflow_dispatch 始终执行完整检查。

差异的空白检查遵循 `.gitattributes`：源码、当前可执行测试和手写规格保留通常检查；构建输出中的第三方 shader 字符串、官方页面原始抓取、终端／AX／JUnit／补丁存档，以及已登记的原始 CSV 和两份历史探针，保留记录的字节，不为格式门重写。生成物仍须通过既有构建清单核对，归档证据不替代当前测试。这一属性只影响空白诊断，不缩减 CI 选中的运行检查。
