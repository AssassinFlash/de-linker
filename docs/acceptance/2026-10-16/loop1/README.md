# loop round 1 · 修复批验收记录（2026-10-16）

分支 `fix/loop-round-1`（worktree `de-linker-loop1`，自立于 `main` c31c88bf），PR #207。
批次内容：只读验证两轮的 FAIL 清单——仓库面 `.scratch/debt-sweep/verify-repo.md` 的 8 项、
线上/运行态面 `.scratch/debt-sweep/verify-live.md` 的 4 项（9–12），加 Matt 双轴评审的返工项 R1–R10。
逐项一个提交（12+10 个提交）。

## 1. 实例与跑法

- 实例 `loop1`（快照 `20261015-1852`，http://127.0.0.1:9054，插件符号链接到本 checkout）。
- 快照装入后按 `tests/e2e/README.md` 的前置清单跑：`linker-i18n setup --assign`、`present`、
  `12-site-chrome.py apply --write`、`9-i18n.py apply --write`；实例上另跑了 `68-contact-form.py
  apply --write`（短代码安装是该迁移的本职）。`8-engineering.py --write` 拒写（见 §6）。
- CSS 改动一律 `present` → `just windpress-compile loop1`（cache recompiled、anchor classes present）
  后再测。

## 2. 十二项落点与证据

| # | 落点 | 证据 |
|---|------|------|
| 1 | `includes/Products/Materials.php`（删 `availability_text()`） | 全仓零调用/零 meta 写方；单测 1020、phpcs、phpstan 绿 |
| 2 | `mu-plugins/{phpcs.xml.dist,phpstan.neon.dist,linker-site-guards.php}` + `tests/php/Integration/SiteGuardsSmokeTest.php` | 实例冒烟 4/4（先故意改坏 `X-Frame-Options`，测试如设计失败） |
| 3 | `plugins/linker-tools/`（删 shared 入口及其测试/构建件）+ `tools/local/tests/test_stack.py` | vitest 96、`build::check`、stack 测试 1/1 |
| 4 | `tools/migrate/7-facts.php`（`seven_facts_group_fate()`） | t7 上四种结局实跑；migrate 94 passed |
| 5 | `tests/e2e/specs/{chrome,i18n}.spec.ts`（归一化比较 + origin） | loop1：chrome 5/5、i18n 10/10 |
| 6 | `tests/e2e/specs/genie-dock.spec.ts`（标签口径，见 R3） | 三处口径一致（grep） |
| 7 | `tests/e2e/specs/products.spec.ts`（吸住几何断言） | loop1：EN/DE 1440 各一条通过（R6 后） |
| 8 | `includes/Presentation/{Module,ProductShortcodes}.php`（句柄 `linker-pdp-ui`） | loop1 PDP 输出 `id="linker-pdp-ui-js"`，代码内旧名 0 |
| 9 | `content/livecanvas/de/*` 9 处 + DE 页头页脚 3 处 `href="/de/blog/"` | `/de/`、`/de/blog/`、`/de/category/system-design/`：`/blog/` 计数 0 |
| 10 | `content/windpress/auth.css`（chevron/状态/红框提权） | §3、§5 |
| 11 | `content/windpress/site-base.css`（页面 reset 进 `components` 层） | §3、§5 |
| 12 | `plugins/linker-commerce/data/faq-trade.json:73`（`Partner-Konto`） | JSON 合法；台账行见 PR |

## 3. 两处实测偏离处方

- **R1/项 10 的特异度**：批次的处方是 `:is(` → `:where(`。实跑后注册页两个 select 的字段**整块换成
  WooCommerce 自己的表单样式**（实测 `background-color:#fff`、`border:1px`、`height:auto`、
  Woo 的 SVG chevron、`padding-right:3em`；Woo 的 `.woocommerce form .form-row .input-text/select`
  在 0,2,2，而 `:where` 基础规则 0,2,0）——既非线上外观也非业主已接受的注册原型。改走验证报告自己给的
  另一条：变体提到与基础规则同权重（`select[name]`；`:is(input[type], input, select, textarea)`），
  由源码顺序取胜，基础规则继续挡住 Woo。实测：chevron = 本文件的两条 linear-gradient、`padding-right:44px`、
  `background: var(--acct-fill)`、边框透明。
- **项 11 的层级**：`base` 层过低（`@tailwindcss/forms` 的字段内边距渗进首页 hero 输入框，出现线上复刻
  没有的 23px 带）；chrome 那半 reset 进层后主题容器的 margin/box-sizing 穿透（每页页头满幅差异）。
  `components` 位于 base 与 utilities 之间，两个边界同时满足；chrome 那半保持 unlayered（见 R4）。

## 4. 像素证据（同机同浏览器 1440×900，全页截图逐像素比对）

基线 = 本分支改动前（项 1–9 已入、CSS 改动未入）的 loop1 截图集。

| 面 | 结果 |
|---|---|
| 商城 `/products/`、产品页 `/product/saj-h2-10k-t3/` | **0 px**（项 10/11 安装后） |
| 首页 `/`、`/de/` | 仅轮播进度条（`.home-stor-progress span`：实测 scaleX 随加载时长增长 0.246→0.5，属时间动画，掩膜外唯一动态区） |
| 注册页 `/my-account/register/`、`/de/mein-konto/register/` | **132 px**＝两个 select 的箭头（项 10 的预期变更） |
| 页头带（0–120 px，首页/商城） | **0 px**（R4 后与改动前完全一致） |

R4 补充证据（删页头容器两个失效类）：`#lc-header .tv-container` 计算值前后一致
（`box-sizing:content-box`、content 1360px、box 1392px、`margin:0 24px`、`padding:0 16px`）；
产品页出现过 13 像素的缩略图圆角抖动——**无源码改动的重编译复现同样 13 像素**（jit），最终态与改动前截图
0 像素差，判定为编译抖动而非该类所致。

## 5. 修复后复测（R1–R7，loop1）

| 项 | 读数 |
|---|---|
| R1 红框 | `/my-account/edit-account/` 真实提交（两次密码不一致，account-ui.js 落 `aria-invalid`）：`#password_2` `background rgb(250,240,237)` + `border rgb(184,90,69)`；未标记时不变 |
| R1 状态 | 聚焦 = 边框 `rgb(12,127,115)` + 4px ring（修复前为 Woo 的深色 `currentcolor`，ring 与填充本来就在）；悬停 = `rgb(231,234,234)`；invalid 场不再吃悬停/聚焦样式 |
| R2 | `just mu-smoke loop1` 4/4（接线错时 `proc_open` 明确失败）；CI 新增 `mu-smoke` job 自建裸实例跑同一配方 |
| R3 | 标签 `pending-fixture` 在 spec、`tests/e2e/README.md`、`docs/specs/16-review-acceptance.md` 三处一致 |
| R4 | 见 §4 |
| R5 | PDP（EN/DE）各一次 `pdp-ui.js`，`?ver=`＝资产 mtime；PDP 7 条用例通过 |
| R7 | `legacy-surfaces.py` 首次跑即抓到 `id="tv-contact-v1"`（接触页自有 id，按 B11 `tv-*` 裁定入白名单并注明）；产品面纳入 id 扫描 |
| R9 | **按证据撤销，不写代码**（复核：线上渲染面与发布面 DB 均 0；仓库携带该串的三处都合法——68 的正则本就为剥它、测试断言清除、fixture 是其输入；loop1 上看到旧串是快照 20261015-1852 早于 M2 次日德语 meta 刷新，属快照陈旧，未来 pull 取自现行线上）。本批为此改的 README 一行已 revert。实例上跑 68 的副产品是零旧政权扫描 CLEAN（各页 0 资产引用 / 0 TerraVolt / 0 旧 id） |
| R10 | WordPress 侧 group 规则夹具用例 3/3（t7，24s） |

## 6. 未了与环境注记（非本批缺陷）

- `tools/migrate/8-engineering.py --write` 在最新快照上拒写（213 行 drift；计划写于 20261010 时代）→
  该实例没有写工程数据；本批所有规格都不读它。
- `genie-dock.spec.ts` 需要模型服务；本批只改了它的 skip 口径（R3），未跑。
- 旧句柄名 `tv-b2b-pdp-ui` 仅存于 `docs/acceptance/2026-10-13/debts/evidence/*.html`（当时页面的捕获证据）
  与 `.scratch/`；代码、模板、测试为 0（grep）。
- CI 的 `mu-smoke` job 建裸实例的步骤本 PR 首次上跑；后续若因 runner 差异失败，按 job 内注释的现行机制调整。
