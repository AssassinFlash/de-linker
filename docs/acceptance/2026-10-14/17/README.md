# #17 一次性切换：2026-10-14 夜执行记录

业主 2026-10-14 令：欠账清零后直接推进 #17，不等确认，早间见完成。本文件是执行记录；
工具与运行面的最终形态描述在 docs/specs/17-cutover.md 的变更记录（2026-10-14 条）。

## 预检（对生产只读；全部在窗口前）

- `just cutover data`（无异无--write）= 807 项待应用、0 漂移；7-facts/8-engineering plan exit 0；
  9-i18n plan 在部署前报 `linker-i18n` 命令未注册——预期（该命令随新插件部署存在，数据步在部署之后）。
- `just cutover hygiene`（报告模式）= 待删修订 2108、9 张旧表、103 个旧选项；autoload 快照落备份。
- `just cutover services`（报告模式）= 两条发布命令 + 两个地址变量；窗口运行前工具尚无远程发布实现（见修复）。
- 生产访问实证：`ssh hostinger-de-linker` = 共享主机 u388076051（/root 不可写）；服务 VPS = `linker-services`
  （新 ssh 别名，root@72.62.97.95，key codex_linker_vps_20260723）。线上插件面与 spec 17 §3 的删除清单一致。

## 预检暴露并修复的工具缺口（各带测试；均为此前只跑本地演练的后果）

1. 远程 shell 引用（两次实伤：hygiene 探针、备份 dump 收到裸 `set`）→ `Target.shell_command` 唯一实现。
2. `services --run` 发布目标 = 站主机（`/root` 不可写）→ 改 `linker-services`；暂存 mkdir 先行。
3. 发布随船 678 MB 本机 arm64 `.venv` → 排除；主机 uv `--frozen` 自建。
4. 备份/恢复脚本内嵌 ssh 前缀 → `Target.wp_on_target()`（`--path` 形式）+ bash 数组。
5. 远程目录大传输被站主机掐断（uploads 2.6 GB/8 分钟）→ `copy_out` 分块（每块一条 tar 流一条连接）。
6. 备份脚本把失败当成功写清单（tar 返回码未查）→ 两端返回码均查，任一失败即中止。

## 服务 VPS 运行面（窗口前已就位；命令按序可重放）

- 发布：`just cutover services --run`（LINKER_ENGINE_URL/LINKER_GENIE_URL 环境变量给出）→
  `/opt/linker-engine/<ver>/`、`/opt/linker-genie/<ver>/` + `current` 软链；两个 WP 选项写入。
- venv：`cd /opt/linker-{engine,genie}/current && /root/.local/bin/uv sync --locked`。
- 环境：`/etc/linker-engine.env`（FEED/COMPATIBILITY/CORS）、`/etc/linker-genie.env`（GENIE_WP_URL）；
  密钥以既有回退路径装到 `/root/.config/terravolt-builder/*.env`（600）。
- 单元：`linker-engine.service`（8901）、`linker-genie.service`（127.0.0.1:8902）；nginx 8443 加 `location /genie/`。
- 烟测：WP 主机 `curl -sk https://72.62.97.95:8443/genie/health` = `{"status":"ok"}` ✓；引擎 8443 旧单元仍在（旧令牌要求，属预期）。

## 窗口（进行中——每一步的输出与证据在本文件末尾追加）

（待录）

### 窗口记录（实时追加）

**① 维护窗口（工具修复 + 实际生效）。** `just cutover maintenance on` 的首次输出自相矛盾
（"activate (already active)" 后接 "status: Maintenance mode is not active."）。查明两层：
(a) 步骤用 `wanted in status.lower()` 判状态，而 `"active" in "maintenance mode is not
active"` 恒真——从未真正下发命令；(b) 手动执行 `wp maintenance-mode activate` 确认其写的是**字面
时间戳**，而 WordPress core 的 `wp_maintenance()` 对超过 10 分钟的时间戳不再展示维护页——短于
本窗口。故维护窗口改以 core 的 `.maintenance` 文件为唯一机制（自刷新 `<?php $upgrading =
time();`），步骤改为写/删文件并以读回为证（提交 e20d575，带说谎检测测试）。
实际生效证据：文件写入后 `https://de-linker.com/?cbq=m4` = **503 + "Briefly unavailable"**；
VPS 侧 REST 探针同被拦截（维护页覆盖 REST，feed 重取须排到维护关闭之后——见窗口⑥）。

**② 半落地核查（deploy 首败前已写文件）。** deploy 顺序为 mu-plugins → 主题 → 插件，首败发生在
插件复制段。逐一比对 sha256：`mu-plugins/linker-site-guards.php` = 8f192c841963dce6、
`linker-error-recorder.php` = 1cc4de2a2a97d0ea、`themes/picostrap5-child-base/functions.php` =
46c87d2279d73298——三处均与仓库提交一致（升级为加法，与旧插件并存的组合安全）。

**③ deploy 三次失败，三层工具缺陷逐层暴露（各带测试与提交）：**
1. `copy_in` 双前缀：`address()` 已含 `host:`，`_push_entry` 再加一次 → 目的地成为
   `hostinger-de-linker:hostinger-de-linker:/…`（e20d575）。
2. 接收端 rsync 只为最终路径组件建目录：线上 `plugins/linker-commerce` 尚不存在（新插件首次
   部署），首个文件块即死于 change_dir → copy_in 先以一条 shell `mkdir -p` 预建**全部 chunk
   的目标目录**（8a5a09e）。
3. **chunk 规则漏文件**：两类从未在任何 chunk 中——「一级目录内的直接文件」（`vendor/autoload.php`
   紧随 `vendor/composer/`，miss 后插件无法加载）与「无子目录的一级目录」（整目录消失）。列表
   补为四类（根文件 / 深度 2 文件 / 深度 2 目录 / 无子目录一级目录），两侧消费端同一规则；
   覆盖性测试以性质断言"每个文件恰属一块"（0eddb93）。

**④ 备份完整性缺口（同因 ③-3；回滚保险修复）。** 1844 备份用旧两类规则：线上 plugins 17000、
uploads 19327、mu-plugins 7；备份分别 16886 / 19247 / 6 —— 合 **191 个文件缺失**（修复脚本
输出）。修复：只补拉缺失文件（排除 deploy 已写、且不属于备份时点的 3 个新文件
`plugins/linker-commerce/*`、`mu-plugins/linker-site-guards.php`），补后逐树**集合相等**
（plugins 16997 = 线上 17000 − 3；uploads 19327 = 19327；mu-plugins 6 = 7 − 1），
manifest 重写为 36334 文件（`.scratch/cutover-run/repair-backup.py` 输出留档）。
工具侧补上使该类缺口可见的检查：每棵树落地后与站点自身 `find -type f` 计数对照不符即失败
（0eddb93；`_prove_the_tree_arrived`）。

**⑤ deploy 成功（第三次）。** 日志全文：`.scratch/cutover-run/deploy3.log` ——mu-plugins 2 件
（全覆盖写）＋主题 functions.php＋linker-commerce 571 文件＋linker-i18n 57＋linker-tools 140
＋`wp plugin install polylang --activate`＋`wp plugin activate linker-commerce linker-i18n
linker-tools`，EXIT=0。宿主侧核对：commerce 571 = staging 571 全量落地。

**⑥ 后续步骤与当晚新暴露的缺口（按发生顺序；全部在本轮闭合或立档）。**

- **plugins（步骤 3 后半）**：`just cutover plugins --backup …/cutover-20261013-2017`。第二次运行才通过：
  新增的硬失败门先暴露「snippets 导出」在远程宿主死于未引用的 `wp eval '<php>'` 参数（ssh 拼行、登录 shell 重裂——
  与预检修过的 shell 引用同因不同点，`Target.wp` 统一改为逐参 `shlex.quote`，fa38938）。重跑结果：
  `snippets: exported 4757 rows (2 active)`；四个旧插件 deactivate+delete；`terravolt-b2b-core-broken-20260704/`、
  两个旧 zip 删除；mu 目录归档并删除 `linker-error-recorder.php.bak-20260808T174655Z` 与
  `linker-i18n-mu-loader.php`（归档在 `docs/acceptance/2026-10-13/17/mu/`）。
- **data（步骤 4）**：三次失败逐一揭示三层问题——(1) 7-facts/8-engineering 自带 `--production` 守卫，
  步骤只按 note 放行（"绿了但什么都没写"）；现为 `Migration.production_guard` 字段 + 非零退出即失败（0ebaa13）。
  (2) 迁移写值备份前需要 `--backup-dir/migrate/` 已存在；步骤补 mkdir（bab7de4）。(3) 9-i18n 自己的 WP 包装器
  对远程前缀不引用（SQL 被拆词："Too many positional arguments"）；按 Target 同一条规则修复并带测试（f49c555）。
  终跑：四支迁移全部 exit 0；`335 imported, 330 synced, 5 not synced`；Polylang 配置成功。
  管理员参数 `--administrator 857558227@qq.com`。
- **schema（步骤 4 后半）**：`wp post update 978 --post_status=draft`（TerraVolt Product Entity Schema）。
- **hygiene（步骤 6）**：首次死于 revision 不能入回收站（`wp post delete` 全数拒收）——补 `--force` 并带头测试（48c2032）。
  终跑（EXIT=0）：revisions 删除 2156；redis-cache 已装已启；`WP_POST_REVISIONS=5`、`DISABLE_WP_CRON=true`（config set）；
  permalinks/cache flush；**9 张旧表 DROP**（wp_linker_ai_conversation、wp_linker_string、wp_snippets、wp_tv_b2b_*×6）；
  103 个旧选项删除；autoload 224 项 51,239 B 落档备份目录。
- **维护关闭 + 缓存**：`just cutover maintenance off`（removed .maintenance）→ 首页 200。LiteSpeed 插件在线上不存在
  （`wp litespeed-purge` 未注册），服务器级整页缓存维持原 MANUAL 项（hPanel 清缓存），验证一律带 cache-buster。
- **窗口⑥（服务运行面）**：feed 从 `https://de-linker.com/wp-json/linker/v1/engineering-feed` 重取成功
  （185,904 B，`generated_at` 2026-10-13T22:19:53Z）；`linker-design-engine.service` disable+stop、
  `linker-engine.service` enable+start；从 WP 主机烟测 `8443/health` 与 `8443/genie/health` 均 `{"status":"ok"}`。
- **verify（步骤 7，cutover verify）**：EXIT=0。核心子集全过：首页与 /de/、/products/、/de/produkte/、
  /proforma-request/、/de/proforma-anfrage/、/my-account/、/de/mein-konto/ 均 200 + lang=de；EN 与 DE 产品页
  各 **恰 1 个 Product 节点**；`/design-canvas/` 301。
- **旧地址 301 抽验（spec §7 全项）**：`/product/<撤回 slug>/` 与 `/produkt/<同 slug>/` **同落点** 301
  （/product-category/home-storage/）；`/product-category/*` → /products/；`/application/`→/solution/、
  `/de/application/`→/de/loesung/（德语孪生自寻址）；**`/checkout/`→/proforma-request/**、
  **`/de/kasse/`→/de/proforma-anfrage/**；`/de/design-canvas/`→`/de/loesungskonfigurator/?step=roof`；
  `/de/angebots-konfigurator/`→/de/loesungskonfigurator/。
- **80-customers（spec §4）**：apply 写 10 个存量账号为 approved（0 locale 补写）；verify：`10 customers, all approved`。

**⑦ 走查线上时新发现的四个真实缺口与处置（均不属于任何既有步骤清单）。**

1. **#12 站点 chrome 迁移从未上线** → 线上导航仍指旧名（/linker-advisor/、/linker-planner/），而本次部署的
   Redirects 映射把旧地址 301 到不存在的新页——**访客级断链**。处置：先修 12-site-chrome 的远程可执行性
   （本地临时文件 eval-file → stdin；包装器补引用规则；1c4274d），plan→apply→verify；四页改名落定
   （linker-planner→solution-configurator、linker-planer→loesungskonfigurator、linker-advisor→genie、
   linker-berater→genie，9 个翻译状态标记）。一条 wp eval 全站扫描：**301 个已发布对象 0 处旧名**。
   链条复测：新 URL 全 200（含 /de/genie/、/de/loesungskonfigurator/），旧别名 301 到**语言正确**的新页。
2. **页模板 meta 全站被清**（预切换 dump：23 页 `page-templates/empty.php`；窗口后：0）→ 主题默认模板把
   每页包上 "Home" h1 + Bootstrap 容器。处置：`tools/migrate/page-template-empty.py`（以 t110 为权威）
   恢复 **36 页**（EN+DE）；首页 body class 与 t110 逐类一致，display-4 归零。
3. **`_thumbnail_id` 全站被清**（dump 273 行 → 0）：全站产品图/卡片全部无图。处置：从预切换 dump 取出
   273 组 post→attachment 映射（附件全部存在），单次 eval 写回 `restored=273 skipped=0`；写入触发
   Polylang 同步把德语孪生一并补齐（现 546 行）。**推定机制**（两处被清键都恰在 linker-i18n Setup 的
   Polylang `sync` 清单：`_wp_page_template`、`_thumbnail_id`；9-i18n 导入保存德语孪生（无这些 meta）时
   同步把空值传播回英文原件）——同批导入的其余键（taxonomies 529 关系、post_parent 等）经全键计数对照
   无损失；此机制说明作为回滚后的追查线索记档。
4. **表现层从未发布**：线上仍是旧 Bootstrap hero/旧语言切换，t110 才是新版。处置：`wp linker-commerce present
   --user=… --allow-stale` —— templates created 12 / updated 8；tokens Additional CSS 清点；WindPress volume 安装。
   随后 **WindPress 浏览器侧编译**（唯一编译方式，Tailwind v4 无服务端构建）：临时部署本地栈的一次性登录
   mu 件（十分钟、一次使用、哈希存储）→ mint → `tools/windpress-compile.mjs` 驱动线上后台 →
   **compiled:true，file_size 673,300**（旧缓存 205 KB、编译于 2026-07-13）→ **立即撤除登录件**（mu 目录
   复核为：hostinger×2、error-recorder、site-guards、livecanvas）。首页复测：新缓存 ver=1791934554，
   `lnk-lang-toggle` 6 处、`tv-b2b-acct` 22 处、`--proto-teal` 97 处在编译产物中。
   结构对照：首页 class 集合 **279 = 279，零差**（HTML 337,316 vs 337,011 B）。

**⑧ 服务链的真机修复（genie 真实请求三轮）。**

- R1/R2 首轮：页面答 "Genie did not answer." —— PHP 侧 `wp_remote_post` 对
  `https://72.62.97.95:8443`（**自签证书**，CN=linker-design-engine，SAN=IP）走公共 CA 校验必败。
  旧插件（linker-ai-assistant）当年以 `data/engine-ca.pem` **钉扎**（sslverify=true + sslcertificates），
  新树从未携带该机制。处置：`mu-plugins/linker-engine-pin.php` + `linker-engine-ca.pem`（随仓库，
  `http_request_args` 过滤 `linker_genie_url`/`linker_engine_url` 两个选项的地址；具名主机自动让位——
  将来换公共证书无需改码）。部署后：会话被记录、侧栏出现标题（传输层已通）。
- 第二轮：服务答降级句 "I could not answer this time." —— 服务端 turn log（`~/.cache/linker-genie/turns.sqlite`）
  给出真相：`linker/search-products returned 404`。客户端把能力名编码为 `linker%2Fsearch-products`，
  而线上 LiteSpeed **拒收编码斜杠**（实测：编码形态 404，原生 200）。处置：`quote(name, safe='')` →
  `safe='/'`（名字先过白名单再入 URL），带测试（7b3120c）；`just cutover services --run` 重发布
  （engine 字节不变，genie 含索引）；两单元重建 venv（`uv sync --locked`：发布后 `.venv` 仍绑旧 release
  路径导致 203/EXEC——此步是每次发布后的例行动作）并重启。
- 第三轮（终态）：R1 = 真答案（引用 GW10K-ETA-G20/GW10K-EHA-G20 并追问相位）；R2 同类；卡片经
  Store API + get-product 能力全部 200 渲染（图、型号、在库、Add to solution draft/Save solution）。
  发现并修复**答案文本双重渲染**（thread 消息与 turn text 块各渲染一遍；t110 同样存在，属构建件缺陷）：
  blocks 视图跳过 text，构建产物三件部署到线上（8d47f9d），复测单次渲染。

**⑨ 唯一开放项（已知、有证据、两条修法）。**

**配置器的浏览器→引擎直连**：页面渲染与表单正常，但引擎调用（`data-engine-url=https://72.62.97.95:8443`）
在浏览器内 `fetch` 被自签证书拒于响应之前（页内实测：`TypeError: Failed to fetch`；证书 subject=issuer=
CN=linker-design-engine）。浏览器无法钉扎，需其一：
(a) **引擎具名域名 + 公共证书**——`de-linker.com` 的 DNS 在**阿里云（dsc23/24.hichina.com）**，不是 Hostinger，
    我们今晚没有该处凭据；加一条 `engine.de-linker.com → 72.62.97.95` 的 A 记录 + VPS 上 8443 换 Let's Encrypt
    证书即可（VPS 80 端口空闲，certbot standalone 可行；mu 钉扎对具名主机会自动让位）。
(b) **同源代理**：配置器的引擎调用改经站点自身 REST 代理（PHP 侧已有钉扎机制可复用）——一次小的功能票。
两条都不阻塞其他任何面；建议 (a)（更小、也把管理面 TLS 一并正规化）。

## 回滚预案（两层，均已物资就位）

- **全量回退（撤销整个窗口）**：`cutover-20261013-1844`（备份完整性已修复并集合级验证：36334 文件、
  db dump sha256 28b2e464…）。路径：`just cutover rollback --backup ~/de-linker-data/cutover-20261013-1844`
  （恢复 DB/plugins/uploads/mu/.htaccess）+ 手动补充三项窗口外写法：删 `wp-content/mu-plugins/linker-engine-pin.php`
  与 `linker-engine-ca.pem`（新增文件）、重新激活旧插件（备份里有它们的目录，DB 恢复即带回激活态）、
  `systemctl disable --now linker-engine && systemctl start linker-design-engine`（VPS 旧引擎回归），
  LiteSpeed 清缓存。注意：`present` 自己的备份也在 `linker_commerce_present_backup` 选项里，
  可单独 `wp linker-commerce rollback --user=<admin>` 撤表现层而不动其余。
- **步级回退**：`cutover-20261013-2017`（plugins 删除前快照：含旧插件目录、snippets 导出 4757 行、
  migrate 值备份）。sed 步骤各自可重跑；本窗口的额外数据写法（页模板 36、缩略图 273、chrome 改名、present）
  都记载在本文档，逐一可逆（改名回链在 Redirects 映射里、present 有自带 rollback、meta 恢复源=1844 dump）。
- **VPS**：两服务均为版本化发布（`/opt/linker-{engine,genie}/<ver>` + `current` 软链），
  `linker-design-engine.service` 单元仍在，仅被 disable——`systemctl enable --now linker-design-engine`
  + `systemctl disable --now linker-engine` 即回到旧引擎。

## 窗口后的清晨状态（给业主的三件先知道的事）

1. 线上已是新版：新头部/首页/产品页/Genie（含产品卡）/配置器页面与改名后的全部地址；德语 149 个 sitemap URL
   全量 200+lang=de（本文件的 de-sweep2 证据）；产品图恢复。
2. 唯一开放项：配置器的"出方案"调用被自签证书挡在浏览器侧（见 ⑨，两条修法，建议 DNS+Let's Encrypt 那条）。
3. 两个手动项留档：hPanel 的每分钟 cron（原 spec §6 MANUAL）与服务器级 LiteSpeed 整页缓存清理（插件不在，
   走 hPanel）；验证均已带 cache-buster，不受其影响。

**⑩ 德语 149 URL 全扫（改名与 present 之后的新 sitemap 全集）**：`evidence/de-sweep2.txt` ——
149 检查中 1 处瞬时 `000`（`…/de/produkt/ecoflow-ocean-2…flagship/`，随即三次复测均 200 + lang=de-DE），
其余全部 200 + lang=de。4 个退休工具别名已随改名/草稿化退出 sitemap（早前扫描的 151→149 正由此而来）。

**⑨ 更新（2026-10-14 晚，业主指路后当晚关闭）**：业主指出"Genie 能通、配置器应同理"——正确。已按**同源路线**实现：`linker-tools` 新增
`Configurator\EngineProxy`（`linker-ai/v1/engine/<path>`，GET+POST），由站点 PHP 转发引擎调用并复用既有证书钉扎；白名单只放
`api/engine.ts` 实际调用的路径；上游状态码原样回传（422/404/503 语义不变）；`report/pdf` 以字节流经
`rest_pre_serve_request` 直出（不能被 JSON 编码）。`Mount` 交给前端的 `data-engine-url` 改为该路由；选项
`linker_engine_url` 保持为服务端地址（代理与健康监控读取）。实测（Playwright，线上）五类调用全部 200：`geo/plz` →
点图 `roof/outline`（"Official building model found."，4 个屋面）→ 手绘面片 `roof/pack` →
`design/residential`（发电量/储能/自给率 + 三件产品）→ `report/pdf`（浏览器真实下载
`linker-design-report-10115-en.pdf`）。过程中修复两处：
`Plugin` 构造为固定类型参数导致新组件未被接线（首次调用 404，a5cc8b0 前后两提交）；`WP_REST_Response::get_header()`
在核心不存在（测试双簧自造的方法骗过了单测，线上 500——错误记录器首日即定位到行，修理并让双簧镜像核心）。
**DNS/Let's Encrypt 路线不再必需**（保留为日后管理面 TLS 正规化的可选项）。

## 欠账盘点与手动项闭合（2026-10-14 晚，全部自理）

业主 MCP 认证恢复后，spec §6 的两项 MANUAL 均已用 Hostinger API 自理关闭，无需业主点击：

- **hPanel 每分钟 cron**：`hosting_cron-jobs_create` 建 `* * * * *` 任务
  `/usr/local/bin/wp --path=… cron event run --due-now --quiet`（uid `fesXZNtJ0u`，list 读回一致）。
  **运行证据**（非仅安装）：`wp_version_check` 的 next_run 从 "2 分钟 3 秒" 跳到 "11 小时 59 分钟"、
  `wp_privacy_delete_old_export_files` 从 "2 分钟" 跳到 "59 分钟"——到点执行并重排，机器在跑。
- **LiteSpeed 整页缓存**：插件本体未安装（API 读得 `is_installed:false`，与 `wp litespeed-purge` 未注册一致）；
  服务器级缓存以 `hosting_cache_clear-website` 清除（"Request accepted"），清后站点 200 复测通过。
- **i18n 的 "5 未同步" 审计**：4 个 `needs_review`（英文侧在德语手编后被改：/de/、footer、/de/loesung/ 等）
  与 2 个 `pending`（归档/单品德语孪生等自动翻译，站点无 DeepSeek key）**均为插件自身台账**——实质核验：
  德语 header/footer/归档/单品四件与仓库语言源文件**逐一 IDENTICAL**（规范化后）， /de/ 与 /de/loesung/
  渲染抽查均为德语（无英文回退）。无需动作；日后若要自动翻译再谈 key。
- **旁注**：Hostinger 账号下另有一个沉睡的 `staging.de-linker.com` WordPress 安装（旧项目时期，
  标题仍为 TerraVolt）；该域名**不解析**（从 VPS 侧 `getent hosts` 无记录），非公开面，仅记录。
