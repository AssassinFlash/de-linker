# #68 验收记录：搜索框 / 联系表单 / 文档维护入口

实例 `t68`（http://127.0.0.1:8927），装配照 PR #62 的形态：`just up t68` → 摘检出软链
→ `just pull load t68 20261010-0033 --live-code`（ok:true，106 产品 / 2755 附件 / 0 残留
线上地址）→ 插件换装（linker-* 指向检出，terravolt-b2b-core 与 linker-ai-assistant
inactive，polylang/redis-cache/三插件激活）→ `wp linker-i18n setup --assign` →
`wp linker-commerce present` → `tools/migrate/9-i18n.py apply --write`（335 导入、330 同步、
5 留译者）→ `just serve t68`（engine :8928 / genie :8929）。

## 1. 检查（命令原文与结果）

| 检查 | 命令 | 结果 |
|---|---|---|
| 静态与构建 | `just check` | 全绿（PHPCS/PHPStan ×4、js lint/type/format、ruff/mypy ×6、build check） |
| 单元与套件 | `just test` | 见 PR（`php` commerce 675 项含本票新增、tools 34、i18n 135；vitest、playwright e2e、pytest ×6、pull pytest） |
| 端点（真实目录夹具） | `LINKER_COMMERCE_TEST_SITE=http://127.0.0.1:8927 php vendor/bin/phpunit --testsuite integration --filter CatalogSearchRestTest` | OK（9 tests, 62 assertions） |
| 端点（人工抽验） | `curl 'http://127.0.0.1:8927/wp-json/linker/v1/catalog-search?q=DLK-GOODWE-GW60KSTSG10&lang=de'` | 200，返回德语孪生 6573 与 `/de/produkt/goodwe-gw60k-sts-g10/` |
| 迁移脚本 | `python3 tools/migrate/68-contact-form.py --wp ~/de-linker-local/t68/wp.sh plan / apply --write / verify` | plan 两页有改动；apply 写入 EN #28 + DE #6915；verify `form=True old-fallback=False`、`ok` |
| 迁移幂等 | 同命令二跑 | `en #28: nothing to do`、`de #6915: nothing to do` |
| 联系表单端到端（EN，匿名） | `curl -X POST .../wp-admin/admin-post.php`（页面新鲜 nonce） | 302 → `/contact/?contact=sent#contact-form`；`~/de-linker-local/t68/mail/` 两封：To `sales@de-linker.com`（主题 `New message from Test Buyer`）+ To `buyer@example.test`（`We received your message`） |
| 联系表单端到端（DE + Bcc） | 同上，从 `/de/kontakt/`；`wp option update linker_commerce_team_bcc copy@example.test` | 302 → `/de/kontakt/?contact=sent#contact-form`；团队信 `Bcc: copy@example.test`，客户回执主题 `Wir haben Ihre Nachricht erhalten`，正文德语 |
| 搜索框端到端（浏览器） | Playwright：键入问句 → 芯片出现 → 点击 | 芯片 `✦ Ask Genie` 出现；点击后 dock 打开，Genie 以键入句为第一条消息并回答（EN 12 张卡；DE `✦ Genie fragen`，德语回答 5 张卡） |
| 型号/品号搜索（浏览器） | 键入 `DLK-GOODWE-GW60KSTSG10` 回车 | 直接导航 `http://127.0.0.1:8927/product/goodwe-gw60k-sts-g10/`（恰好一个命中 → 直达产品页） |
| ?s= 结果范围 | `SearchScope`（单元测试）+ 规格 13 变更记录 | 主查询、未指名 post_type 的搜索限定 `product,post`；显式 post_type 不动（见规格） |

## 2. 截图（1440 与 390，EN 与 DE）

同一浏览器（Playwright 的 chromium，本机同视口、禁动画不适用——本页无动画门），
文件在本目录：

| 文件 | 内容 |
|---|---|
| `search-en-1440-question.png` | EN 目录页，键入问句后芯片出现（1440） |
| `search-en-1440-answer.png` | 同一页，点击芯片后 Genie 以该问句开线并给卡（1440） |
| `search-en-390-question.png` | 同上，390 宽 |
| `search-de-1440-answer.png` | DE 页，`Genie fragen` 芯片 + 德语回答（1440） |
| `search-de-390-question.png` | DE 页芯片状态（390） |
| `contact-en-1440-idle.png` / `contact-en-1440-form.png` | EN 联系页与表单特写（1440） |
| `contact-en-1440-sent.png` | EN 发送后状态（`?contact=sent`，1440） |
| `contact-en-390-form.png` / `contact-de-1440-form.png` / `contact-de-390-form.png` | 390 / DE 对照 |

**挂载说明（重要）**：搜索框的 markup 属 #16 正在重建的 archive 模板（本票不得修改那三份
文件）。因此验收把**本票交付的部件**挂在一张 scratch 页上：页内容含与线上同一形态的
`form.wb-search` + `input#search-box`，以及 `[linker_genie_ask]` 打印的芯片（EN 页
`/search-box-check/` #6935，DE 页 `/suchfeld-pruefung/` #6936）。集成点见 PR：
#16 在 `[linker_catalog_head]` 的 `.wb-bar` 里（表单旁）挂 `[linker_genie_ask]` 即可，
JS 只绑定 `#search-box` 与 `[data-linker-ask-genie]`，与线上锚点同名。

## 3. 本票顺带修的两个既有缺陷（发现于验收，含复现）

1. **商品编辑器 Figures/FAQ meta box 在真实浏览器里从不保存**（#8/#15 的箱子）。
   证据（实例 2286，有 `_tv_b2b_figures`）：
   `wp eval-file` 用**浏览器真实的嵌套形态** `$_POST['linker_figures'][key][field]` 调
   `save()` → 值仍 660（无写入）；用**扁平键** `linker_figures[key][field]`（浏览器永不产生）
   → 被解析（并被引用校验拒绝，证明解析路径只在扁平键上成立）。
   修复：两个箱子的 `posted_rows()` 读 PHP 实际解析出的嵌套数组；测试夹具同步改为真实形态；
   本票新增的文档箱子用同一形态。文件：`includes/Admin/{FiguresMetaBox,FaqsMetaBox,DocumentsMetaBox}.php`。
2. **Genie app 每次点击被执行两次**：`Entries::script_deps()` 把入口自身的 URL 也当作依赖返回，
   装载器先插 deps 再插 app，同一 `build/genie.js` 被插入两次（浏览器 Network 里两个同 src 标签）。
   后果：`createRoot` 二次挂载、模块级副作用跑两遍——本票的 pending-ask 因此被第一次挂载读掉，
   芯片点击后 Genie 不发言。修复：`script_deps()` 跳过入口自身（`Self::HANDLE === $handle`）
   并留注释。修后浏览器实测 `genieScripts=1`，冷启动路径通。

## 4. 未做/留待后续

- archive/pdp 模板上的最终挂载：#16（本票已在 PR 里注明挂载点与短代码名）。
- `[linker_contact_link placement="header"]`（线上页头 partial 里未解析的旧短代码）不在本票范围
  （#12/#16 的页头对象）；本地实例上它以字面量出现，见 #16 的验收 README。
- 线上像素级比对不适用本票两块新面（搜索框芯片与联系表单是新建/重建面，非复刻面）；
  同页其余区块按复刻面规则归 #16 的验收。
