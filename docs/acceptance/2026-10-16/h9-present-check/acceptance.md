# H9 · `present --check`：部署后防再发断言 · 验收记录（2026-10-16）

台账 H9（#182 建议项）：部署后没有只读断言可以证明「实例与仓库模板一致」——
只能重跑 `present` 看它的 `created/updated/unchanged` 计数，而那是一次写入。
本票加一个只读模式，把那条断言变成一条命令。

## 1. 做了什么

- `wp linker-commerce check`（`Cli\PresentCommand::check()`）：**不写任何东西**——
  不写 post、不写 option、不建备份、不碰文件；逐注册模板比对仓库文件与实例
  `post_content`，比对 header/footer partial 对，比对 WindPress 卷文件的哈希与
  `main.css` 导入行。
- 全部一致：`Success: presentation in sync`，exit 0。
- 有漂移：逐条列出 `drift: <surface> — <target>: <detail>`，再 `WP_CLI::error`
  （exit 1），错误行说清修法（`wp linker-commerce present --user=<admin>`）。

两个只读实现落点（与 `present` 共用同一批查找，避免「检查用一套、写用另一套」）：

- `Presentation\Templates::drift()`：页型模板与工具页模板对导出文件、German
  page-type twin 对它的翻译组、工具页的 `lc_use_template_of_slug` 指认、
  header/footer partial 对（含 German twin 解析失败）。行的判定范围**等于 sync()
  会写什么**：`check` 报的行 `present` 都能修，`present` 不修的事 `check` 不报
  （例如内容已一致的 draft 模板）。
- `Presentation\WindPressVolume::drift()`：卷内每个 `content/windpress/*.css`
  的 md5 与导入行；卷目录不存在时报一条，不创建。

## 2. 测试（进既有 `PresentCommandTest`，不新开文件）

4 条新测试（commerce PHPUnit 1073 通过）：

| 测试 | 断言 |
|---|---|
| `test_check_reports_a_synced_site_and_writes_nothing` | 全同步 fixture → `wp-cli success: presentation in sync`；`wp_update_post` / `wp_insert_post` / `update_post_meta` / `update_option` / `wp_update_custom_css_post` / `delete_option` 一次都没被调；备份 option 不存在 |
| `test_check_names_drifted_templates_and_fails` | 改一条模板内容 → 恰 1 行漂移、消息带 `1 presentation drift row(s)`、指名 `page type is_shop_page — post N: content differs from shop_page.html`；check 没写 |
| `test_check_reports_every_drift_surface` | 四个面各造一处漂移（German twin 丢失 / 工具页指认错误 / header twin 解析失败 / 卷文件缺失），四行全部出现 |
| `test_check_reports_a_missing_template` | 模板整体不在 → `page type is_search — search.html: not installed` |

fixture（`mock_synced_site()`）是一个「`present` 跑过之后」的完整站：18 个模板
post + 8 个工具页 + header partial 对（live id 17/6919）+ 真实卷目录（跑真的
`WindPressVolume::install()`，所以 md5 比对对着真字节）。测试修改一个字段即造成
漂移；`tearDown` 清掉临时卷目录。

另有一条既有行为得到覆盖：WP_CLI 的派发形状（`present( array(), array() )`）与
`check( array(), array() )` 相同。

## 3. 真实例上的验证（`nfinal`，快照 20261015-1852）

只读断言的价值只能在一个**真的站**上证明；下面三幕都在真实例上实测：

1. **能抓到真漂移**：实例刚 load 快照、还没跑 `12-site-chrome.py` 时，
   `check` 报 `page assignment linker-configurator-de — loesungskonfigurator (de):
   the page this template belongs to is not installed`（1 行）——这正是 README 要求
   的 setup 差口，`check` 把它变成了一条可执行的诊断。跑过迁移后该行消失。
2. **写入式探针**：注入一处模板漂移 + 一处卷文件漂移（`<!-- h9 probe -->`，
   `products.css` 加注释），`check` 报：
   ```
   drift: page type is_shop_page — post 6961: content differs from shop_page.html
   drift: windpress volume — products.css: the volume copy does not hash the same as the export
   Error: 2 presentation drift row(s): …
   ```
3. **双向闭环**：`present` 修回 → `check` 报 `Success: presentation in sync`。

（真实例上另有一次 `#197` 已记录的部署完整性终证：线上 `present` 净跑
created 0 / updated 0 / unchanged 18——即今天的线上本就是 in sync，
`check` 会以 0 行、exit 0 回答。）

## 4. 静态与测试

- `just php-check`：PHPCS + PHPStan level 8 全 `No errors`（新增代码包括
  只读侧的全部 docblock 类型）
- `just php-test`：commerce 1073（+4）/ 152 / 113 / 6 通过，跳过 54

## 5. 结论

`wp linker-commerce check` 是 `present` 的只读孪生：同一批查找、同一套「什么算
需要修」的判定、零写入。单元测试证明「全一致 exit 0 / 有漂移逐条列出 exit 1 /
一个字节都不写」，真实例三幕证明它在真站上的读与报都对得上。
