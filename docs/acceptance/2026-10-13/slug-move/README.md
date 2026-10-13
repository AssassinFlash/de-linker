# 配置器页地址迁移 `/linker-planner/` → `/solution-configurator/`（2026-10-13）

业主裁定（2026-10-12）：**不保留旧 slug**。旧域名地址 301 到新地址。
本记录列出代码面、数据面与实例面的改动与实测证据；主线提交 `84f27c5`（代码）、`d0f4064`（迁移脚本精修）。

## 1. 代码与数据面（仓库）

| 位置 | 改动 |
|---|---|
| `Templates::PAGES`（linker-commerce） | 页面 slug `linker-planner`→`solution-configurator`、`linker-planer`→`loesungskonfigurator`；模板 slug（`linker-configurator`/`-de`）不变 |
| 页头/页脚 partials（EN/DE 各一） | 导航链接换新址 |
| `SizeHint`（Abilities） | `PATH` 常量 `/solution-configurator/` |
| `ProductShortcodes::configurator_page_url()` | `get_page_by_path( 'solution-configurator' )` |
| `legacy-redirects.json` | `pages` 表新增两条：`/linker-planner/`、`/linker-planer/` → `/solution-configurator/`（德语请求经 Polylang 孪生落到德语新址）；`retired_tools` 五条目标全部换新（design-canvas/entwurfsflache 指向 `?step=roof`）；`/request-a-project/` 目标换新。pages 19→21、retired_tools 5 不变（单测钉住计数） |
| `tools/migrate/12-site-chrome.py` | 新增 `rename_slugs()`（幂等；`resolve()` 按新旧两种 slug 找页，`post_name__in` 优先页面/分部、模板仅后备）；Site Detail 链接改写从严格 pair 改为 catch-all rules（早期运行留下的中间值 `/linker-planner/?step=roof` 被升级而不是拒写）；`verify` 校验 slug |
| 测试 | Unit `RedirectsTest`（新增迁移地址用例、live-addresses 用例移除两条）、Integration `RedirectsTest`、`ProductShortcodesTest`、`SizeHintTest`、e2e `chrome.spec.ts`、genie `test_ground.py`、cutover `test_target.py` 同步 |
| spec | `12-site-chrome.md`（跳转条目 + 验收项）、`14-solution-configurator.md`（地址与变更记录） |

## 2. 实例面操作（t110 = 终局门实例；t109 = 复刻扫掠实例）

对两个实例各做：`just up <name>`（把三个插件软链重新锚回本检出并重启服务）→ 页面 `post_name` 改名（EN/DE）→ 通知占位页处置（原件转草稿、重复删除）→ `just present <name>`（模板/分部装配）→ `just windpress-compile <name>` → `just present <name>`（幂等收敛）→ 12-site-chrome `apply --write`（t110）→ curl 矩阵。

**t110 实测**（`127.0.0.1:8975`，2026-10-13）：

```
EN 新址  /solution-configurator/    200；data-linker-app="configurator" ×1；字面短代码 ×0；旧应用标记 qcfg-root ×0
DE 新址  /de/loesungskonfigurator/  200；挂载 ×1；字面短代码 ×0
/linker-planner/         301 → http://127.0.0.1:8975/solution-configurator/
/de/linker-planer/       301 → http://127.0.0.1:8975/de/loesungskonfigurator/
/design-canvas/          301 → http://127.0.0.1:8975/solution-configurator/?step=roof
/de/entwurfsflache/      301 → http://127.0.0.1:8975/de/loesungskonfigurator/?step=roof
/quote-configurator/     301 → http://127.0.0.1:8975/solution-configurator/
/de/angebots-konfigurator/ 301 → http://127.0.0.1:8975/de/loesungskonfigurator/
follow /linker-planner/: 200，final=/solution-configurator/（一跳到 200）
```

迁移 apply 输出要点：`for-installer` EN/DE 链接 1x 升级到新址；两页 `slug already solution-configurator / loesungskonfigurator`（`rename_slugs` 幂等路径真实实例实测）；SEO 标题补写；`translation state: {'marked': 2}`；其余全部 `nothing to do`。

**t109 实测**（`127.0.0.1:8969`，业主浏览器标签所在实例）：

```
EN/DE 新址 200 + 挂载 ×1；索引 301 同 t110（域名换成 8969）；follow 一跳到 200
```

t109 特有处置：
- 该实例从未有德语页头/页脚分部（`header` #17、`footer` #18 无孪生），present 的 fail-closed 档位拒写（`RuntimeException: German header partial could not be resolved … refusing to report a header sync that skipped a language`，日志 `logs/php-error.log`）。按既有约定建 DE 孪生：`kopfzeile`(#6596)、`fuszeile`(#6597)，`pll_set_post_language` + `pll_save_post_translations` 链组后 present 通过。
- present 告警（非拦）：`German page types this site has no German template for: is_single_product` —— 该实例没有德语商品页型模板，德语商品页保留其原有模板；对配置器页无影响。

## 3. 两个坑（均已处置，写入记录防再犯）

1. **php -S 常驻 worker 会继续执行旧代码**：软链换目标（工作树 → 本检出）后，实例 web 请求仍在跑旧编译单元（表现为 `/linker-planner/` 404、design-canvas 301 到旧目标），而同一实例的 WP-CLI 已是新代码。处置：`just down <name> && just up <name>` 重启后再验全绿。**软链改动后必须重启实例服务再取证据。**
2. **迁移脚本的目标值演进**：实例若已被旧版迁移改写过，链接处的中间值会让严格 pair 拒写（`neither old nor new string found`）。处置：URL 改写改走 catch-all rules（可 0 次），并把 `resolve()` 的按名解析优先页面/分部、模板后备（present 建的 `lc_dynamic_template` 与页面同 slug 是设计使然，t110 上实测撞到）。

## 4. 复现命令

```bash
# 仓库侧
just check && just test
# 实例侧（以 t110 为例）
just up t110
just wp t110 post update <EN页ID> --post_name=solution-configurator --post_title="Solution Configurator"
just wp t110 post update <DE页ID> --post_name=loesungskonfigurator
just present t110 && just windpress-compile t110 && just present t110
python3 tools/migrate/12-site-chrome.py --wp ~/de-linker-local/t110/wp.sh plan     # 应全 no change / slug already
# 验线
curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' 'http://127.0.0.1:8975/linker-planner/?cbq=x'
curl -s 'http://127.0.0.1:8975/solution-configurator/?cbq=x' | grep -c 'data-linker-app="configurator"'
```
