# #17 一次性切换上线

## 前提
#16 通过；业主确认维护窗口（夜间，停机以分钟计）；本地演练过完整切换脚本两次（干净快照 → 切换 → 回滚 → 再切换）。

## 脚本 `tools/cutover/`（经 `ssh hostinger-de-linker`，每步可单独重跑）

### 文件发布与回滚（#298；PR #299 第 1 轮裁定）

共享库存函数 `deployment_artifacts()` 同时供发布与回滚使用，覆盖三个仓库插件、mu-plugin PHP/PEM、仓库管理的子主题文件。先验证所有输入并完成全部本地 Composer 构建，再把所有产物上传到各自 live 同目录的隐藏 `.next`。任何构建或上传失败都不切换 live。所有目录与文件的 rename 在**同一条远端 shell** 内完成；一套 EXIT/HUP/INT/TERM trap 在任意 rename 失败或可捕获中断时恢复整批。回执 `Receipt` 含 deploy ID、全部路径、站外备份目录和**总切换耗时**；计时只覆盖整批 live rename 命令段，不包含构建、上传、网络等待或备份准备。

**选 rename 的依据**（[已裁定的评审意见](https://github.com/AssassinFlash/de-linker/pull/299#issuecomment-6241352856)）：符号链接发布会使 `__DIR__`、`plugin_basename()` 与 WordPress 的 realpath registry 涉及 release 目录，opcache 键也随 release 路径变化；相同路径的 rename 保持 WordPress 已登记的插件路径稳定。评审已在 Hostinger 只读取证确认 plugins / mu-plugins 同文件系统，因此采用 rename，不做生产 symlink 试验。每次发布还会检查全部目标父目录与站外 `~/deploy-prev` 的 device 相同，且备份目录解析后确在 web root 外；不满足时在切换前失败。

**残余风险**：两次目录 rename 间仍有短暂缺路径窗口；跨过切换点的既有 PHP 请求，以及 opcache 的时间戳重验，仍可能观察不同阶段的代码。单 shell 将跨插件窗口收敛到整批 rename 段，实际总耗时写入回执，不以“微秒级”代替测量或生产零 fatal 验收。没有后台自动换 symlink 或修改 opcache 设置。

每批 deploy ID 为 UTC 时间加 git SHA。`~/deploy-prev/<deploy-id>/manifest.json` 为这一批每个备份记录相同 deploy ID、完整库存、先前存在与否、备份 device/inode 及新 live device/inode；`latest` 只指向这一个 manifest。成功切换后为 `pending`：备份暂在隐藏 `.prev` / `.prev-absent` 同目录。普通 `just cutover deploy` 在激活与语言包步骤之后运行既有 verify（含生产 Search Console 读回），只有通过才把全部备份**按 rename** 移到站外 `<deploy-id>/files/`，读回备份 inode 并确认 web root 内对应 `.next/.prev/.prev-absent` 均已消失，再删除较早部署的备份。**只保留最近一批备份**。verify 失败会返回非零，保留这一批供回滚，不能把失败的 verify 当成成功归档。

PR #299 第 3 轮裁定的恢复边界：已有目录的失败恢复先 `mv live .<slug>.failed && mv previous live`，最后才删除 `.failed`；清理失败不损坏已恢复 live，残留 `.failed` 会阻止下一次发布覆盖它。live 尚未装回时直接 rename previous 回来。切换计时只解析独立的 `LINKER_CUTOVER_SWITCH_SECONDS=` 行；其他输出不参与数值解析，缺失、损坏或重复的计时记录均报 `CutoverError`。切换成功但回执丢失或解析失败时，pending manifest 继续可用。

`just cutover resume-deploy` 从同一发布检出版本读取 pending manifest，预检同批库存、备份与新 live inode，重新运行同一 verify，通过后归档；不重建、不上传、不切换 live，不补造丢失的切换耗时。verify 继续失败则保持 pending。下一次成功归档并读回后，专用 `~/deploy-prev/` 根下的较早批次连同被强制中止、尚未写出 `manifest.json` 的批次目录一并清理；归档失败时不清理这些目录。

`just cutover rollback-deploy` 从同一发布检出版本读取同一个库存函数。预检逐项比较 manifest 的 deploy ID、库存与实际备份 inode，明确列出混批、缺失、被替换的备份，任一不符则零写入；还拒绝 live 在发布后发生未登记变更。回滚从 pending 同目录或 archived 站外目录把整批文件 rename 回来，可捕获失败时恢复整批当前版本。完成后逐路径读回恢复的 device/inode（原先不存在则确认不存在），用 `wp plugin list --fields=name,status` 确认三个插件 active，再运行与部署相同的 verify；输出实际读回结果，任何检查不通过均非零。回滚会消耗上一版，不提供 redo，不导入数据库，也不改插件激活状态。原完整备份回滚入口不变。

### 部署前快照与完整备份（#305）

业主 2026-10-18 问：每次部署前都做一次完整备份是否必要（4.6 GB，30–60 分钟）。结论按"部署能改动什么"分层：

- **代码**（三个插件、mu-plugin、子主题文件）：原子切换保留上一版，`just cutover rollback-deploy` 一条命令改回（上文）。
- **数据库**（插件激活、选项、语言包会改）：`just cutover deploy` 的**第一步**是数据库快照，在构建与上传之前；快照失败则部署在切换前停止。快照由主机上的 mysqldump 经标准流**直接传到本机** `~/de-linker-data/snapshots/db-<UTC>.sql.gz`，主机上不写任何文件（业主 2026-10-18：服务器空间留给站点）；先写隐藏的 partial 文件，gzip 读到结尾才改名，失败不留残件；本机保留最新 20 份。快照**不含** `wp_genie_chunks`：它占数据库 817.9 MB（2026-10-18 线上实测，其余表合计约 110 MB），是已退役的库内知识索引（Genie 读 VPS 上的 SQLite 索引，#257），站点代码不读不写，部署改不到它；完整备份仍包含它。实测（2026-10-18 线上）：快照 6,200,721 字节，用时 14 秒；导入本机空库得到 61 张表（线上 62 张减去该表）、`siteurl` 为 https://de-linker.com。还原：`just cutover snapshots` 列出；`just cutover restore-snapshot <名称>` 只预览并校验名称与文件，加 `--write` 才执行：先把**当前**数据库再存一份快照（还原本身是数据写入，还原错了也能一条命令撤回；该次修剪不会删掉正要读取的那份），再导入并清缓存。导入只替换快照里有的表：被排除的那张不动，快照之后才建的表（例如新插件激活时建的）连同数据保留。代码与数据库要一起回到同一时刻时，与 `just cutover rollback-deploy` 一起用。
- **uploads**：代码部署碰不到，不随部署复制。

主机上唯一保留的是原子切换的上一版代码（`~/deploy-prev/`，只留最近一批，约 28 MB：三个插件实测 22 + 4.2 + 2.1 MB），供 `rollback-deploy` 同盘改名即时回滚；它是部署机制的一部分，不是备份。备份（快照与完整备份）只存本机。

**完整备份**（`just cutover backup`）用于数据写入之前（导入、批量修改、迁移；`data`、`hygiene`、`plugins` 三步本就先自取完整备份，`schema --write` 现在也先取）与**每周一次**，不再是每次代码部署的前提。没有定时任务替你做每周那一次：每次部署在最新一份完整备份超过 7 天（或一份都没有）时在日志里提醒。它改为**增量**：与最新一份完整备份相同的文件用 `rsync --link-dest` 硬链接而不重新下载，每份仍是可独立还原的完整目录树；只有带 manifest 的完整备份才被当作链接来源。


普通更新需让 verify 看到真实站点；本票生产探针不启用维护页。完整首次切换的 `Drill` 使用同一 `deploy()` 阶段，在数据步骤完成且维护关闭之后调用同一 `finish_deploy()`，因此不会拿维护响应作为归档依据。下文“就地替换”只指 URL / 插件 slug 不变。

生产实走用 `just cutover probe`，端点来自 `plan.DEPLOY_PROBE_ENDPOINTS`，root / URL 来自 `Target`，插件来自 `plan.NEW_PLUGINS`。探针与部署同时运行，用单一 worker 轮询首页、联系页、Proforma 请求页、产品页，以及 commerce 的产品搜索、i18n 的德语 REST 过滤、tools 的只读会话路由。按第 3 轮决定 5 降载：构建和上传期每次响应后等 **1 s**（总流量至多约 1 GET/s），即将调用切换 shell 时由部署进程刷新 `LINKER_CUTOVER_SWITCH_START` 行，观察进程收到后改为每次响应后等 **0.1 s**（总流量至多约 10 GET/s），直到 verify / archive 读回完成，且至少采完一轮全部端点。两个频率均为本票选定的验收配置：保留原来用于约 30 s 故障窗的 0.1 s 间隔，但从“每端点”改为“全体合计”；构建上传再降十倍。它们不是实测主机容量或 Hostinger 许可上限；任意时刻最多一个探针 GET 在途，慢响应自然继续降速。前后快照依次请求，最终 fatal 元数据读取在所有请求结束之后。同时记录目录 rename 的 inode 证据与每次采样的 cadence。具体命令、回滚边界及 Claude 的未完成生产验收见 [2026-10-18 部署记录](../acceptance/2026-10-18/deploy/README.md)。

1. **备份**（完整、增量，见上文“部署前快照与完整备份”）：mysqldump 导出数据库（`wp db export` 在生产主机不可用：WP-CLI 的 export 先调 `exec()`，而主机的 `disable_functions` 含 `exec`——理由与出处见变更记录 2026-10-11（#81））、`wp-content/uploads`、`wp-content/plugins`、`.htaccess`、选项导出 → 本地 `~/de-linker-data/cutover-<date>/`，sha256 清单。
2. **维护模式开**（`wp maintenance-mode activate`）。
3. **部署**：rsync 三个新插件（含 `vendor/` 与 `build/`；`linker-i18n` 同 slug 就地替换；`.po/.mo` 随各插件自己的 `languages/` 走，不单独复制）；Polylang 用 WP-CLI 从 wordpress.org 原生安装并激活（已装则只补激活）；**WP 核心与 WooCommerce 的 de_DE_formal 语言包同样用 WP-CLI 原生安装（只装不激活，全站默认语言保持英文、前台语言由 Polylang 逐页切换；2026-10-15 事故：切换后线上没有任何语言包，德语页的 Woo/WP 核心字符串全部回退英文——本地栈在实例创建时就装这两份包，tools/local `install_language_packs`，所以缺陷只在线上可见）**；`mu-plugins/*.php`（含新错误记录件）装入 `wp-content/mu-plugins/`。停用并删除 `terravolt-b2b-core`、`linker-ai-assistant`、`woocommerce-gateway-stripe`、`code-snippets`（先按**当时的活动行**把代码导出到备份目录——本仓库不携带旧树的自定义代码，仓库里只留"活动行的功能已由新插件承接"的确认记录；2026-10-11 盘点活动行为 2 条）、`terravolt-b2b-core-broken-20260704/` 与两个备份压缩包、以及插件与 mu 目录里的 `*.bak-*`。
   - **mu 目录**：把 `mu-plugins/linker-error-recorder.php` 装到 `wp-content/mu-plugins/`（新记录件，替换线上同名文件：主机 `log_errors=OFF` 且没有可读的错误日志，记录件是唯一能回答"站点为什么坏了"的面；文件写进 `wp-content/linker-errors/php.log`，256 KB 轮转，目录带 `.htaccess` 拒绝与空 `index.html`）。
   - **mu 卫生**：删除 `wp-content/mu-plugins/linker-i18n-mu-loader.php`（旧 i18n 的早载垫片；请求语言解析现在归 Polylang 与 linker-i18n）与 `linker-error-recorder.php.bak-*`（旧记录件的备份）；保留 LiveCanvas 自带的 `livecanvas-must-use-plugin.php` 与主机平台的 `hostinger-*`。删除前把这两个文件复制到 `docs/acceptance/<date>/17/mu/` 存档（作为删除记录，不作代码继续使用）。
4. **数据**：运行 #7、#8、#9 的迁移脚本（`write`），#7 的写入器再跑一遍 `c15-facts.json`（五台相位与功率，同一份 from/to 合同）；`python3 tools/migrate/80-customers.py --wp <WP-CLI> --user <admin> plan` 复核后 `apply --write`（存量客户一次性置为已通过，见该脚本的头部说明与 `rollback` 子命令：切换前就在的客户不该被账号审批门挡在外面）；Polylang 配置；运费区域清空；Woo 邮件收件人；选项清理（旧插件选项按清单删除）。
5. **服务**：发布 `services/engine` 与 `services/genie`（含索引）到 VPS；写入服务地址与令牌到 WP 选项（令牌不经仓库）。
6. **主机卫生**（共享主机留用、不升级）：启用 Redis 对象缓存（Hostinger 提供的对象缓存或 `wp plugin install redis-cache` + 主机 Redis 套接字，二选一按实测），并在 wp-config 设 `WP_REDIS_GRACEFUL=true`（缓存读失败降级为请求内缓存与日志，而不是杀掉请求——本地实例同常量，规格 5）；hPanel 设每分钟 cron 调 `wp cron event run --due-now`，并 `DISABLE_WP_CRON`；`wp post delete $(wp post list --post_type=revision --format=ids)` 清修订版并在 wp-config 设 `WP_POST_REVISIONS=5`；删除旧插件遗留的自定义表（`wp_tv_b2b_*`、`wp_linker_*`，先备份）；删除旧插件遗留的 WP-Cron 事件（钩子前缀 `tv_b2b_`、`linker_ai_`，`plan.LEGACY_CRON_PREFIXES`；处理函数随插件删掉后事件仍每天到期，#221 2026-10-17 在线上发现 6 个）；`wp option list --autoload=on --format=json` 审查 autoload 体量，清理旧 transients 与过期选项；LiteSpeed 全清；固定链接刷新；`wp cache flush`。
7. **维护模式关**；跑线上只读回归子集（150 个德语 URL、首页、分类页、产品页、Genie R1/R2 真实请求）；抽验旧地址 301（`data/legacy-redirects.json` 的三张表各取若干条 EN 与 DE，含 `/checkout/` → `/proforma-request/`、`/de/kasse/` → `/de/proforma-anfrage/`、`/shop/` → 商城页地址、`/produkt/<撤回 slug>/` 与其 `/product/` 兄弟同落点）；一次真实询盘（测试账号，随后撤销并删除）。

   mu 件生效实证：`wp eval 'trigger_error( "cutover smoke", E_USER_WARNING );'` 之后 `wp-content/linker-errors/php.log` 里必须出现该行（文件不存在或为空即视为部署失败）。
8. **回滚**（预案，演练过）：恢复备份的插件目录与 `.htaccess`，导入备份数据库，重新激活旧插件，清缓存。

## 验收
- [ ] 线上全部英文页面与 150 个德语 URL 200；`/design-canvas/` 301。
- [ ] Genie R1/R2 线上通过；询盘流程线上通过；**测试邮件只发一封、只发 `chester@de-linker.com`**（AGENTS.md 测试邮件纪律，业主 2026-10-11：任何测试场景的 To/Cc/Bcc 一律重写为这一个人，一封送达即证明投递链路畅通）；多收件路由（客户副本、团队、Bcc）的正确性以 **Outbox 队列的收件人数据**断言——写在队列里即正确，不做多封实发。
- [ ] `wp plugin list` 无旧插件；Snippets 表不存在或为空；插件目录无残留；`wp-content/mu-plugins/` 只剩 LiveCanvas 自带、主机平台的两件与新记录件。
- [ ] 旧地址 301 抽验通过（三张表各若干条 EN/DE，`data/legacy-redirects.json`）；存量客户全部为已通过（`tools/migrate/80-customers.py verify`）。
- [ ] 视觉验收：首页、产品页、配置器、Genie、账户 × EN/DE × 1440/390（线上）。

## 变更记录
- 2026-10-18（#305，部署前快照与增量完整备份）：部署第一步改为数据库快照（流到本机、主机不留文件、排除已退役的 `wp_genie_chunks`、失败即不切换）；`snapshot` / `snapshots` / `restore-snapshot` 三个命令；完整备份改增量（`--link-dest`），只在数据写入前与每周做。依据：业主 2026-10-18 的时间与服务器空间要求，及代码由原子切换保留上一版。
- 2026-10-14（#145）：`just cutover verify` 之后再跑 `search-console` 段（`steps.search_console`）：Site Kit 启用、已连接 `https://de-linker.com/`、验证文件不带 cache-buster 可取；任一不成立退出码 1。只对生产主机跑（`--target local:…` 与 `drill` 都不跑：本地实例不连 Google）。规格 `docs/specs/145-search-console.md`。
- 2026-10-14（#17 首跑生产）：预检把工具从没有跑过的生产路径都跑了一遍；六处修复，逐条有理由：
  - **远程 shell 的引用**：脚本现在以单个 shlex 引用词随 ssh 出发（`Target.shell_command`，唯一实现，备份的 `_stream` 同用）。`ssh host 'bash -c' 'script'` 会被登录 shell 重新按空格拆分——实测两次：hygiene 的第一个探针死于 `then`，备份的 dump 收到裸 `set`（落地的"db.sql.gz"是环境清单）。本地演练从不走远程分支。
  - **发布去服务 VPS，不去站主机**：`services --run` 现在 rsync 到 `linker-services`（新增 ssh 别名 = 服务 VPS 的 root，与 `hostinger-de-linker` 同风格）。`release.sh` 在它运行的机器上取源、`/opt` 在服务 VPS 上，而站主机是共享主机普通用户（`/root` 不可写）；此前该步在两种目标上都跑不通，演练也从未跑到第 5 步。暂存根 `plan.SERVICES_STAGING`，先 ssh `mkdir -p`（macOS 的 openrsync 建不了多级目标）。
  - **发布排除 `.venv` 与缓存**：本机 678 MB 的 arm64 虚拟环境随船一次即被断线；主机用自己的 uv `--frozen` 建环境。
  - **备份/恢复脚本内的 WP-CLI 用 `Target.wp_on_target()`**：脚本按本文"一段脚本两个目标"在机器本机运行，内嵌 ssh 前缀在站主机上解析不了别名（实测：`Could not resolve hostname`）。远端形式 = `/usr/local/bin/wp --path=<root>`（cd 变成 `--path`，无传输层）；脚本内以 bash 数组构建（`wp=(…)` + `"${wp[@]}"`），字符串 + 无引号 `$wp` 会把前缀拆散。
  - **远程目录拷贝分块**：主机掐长传输（uploads 2.6 GB / 约 8 分钟即断，实测两次）。`copy_out` 先一次 ssh 列出块（一级文件 + 二级目录：uploads 的月、插件的子目录），每块一条 tar 流、一条独立连接。
  - **§5 的运行面**（本文此前只写"发布…并写入地址"，没有写"谁把它跑起来"）：服务 VPS 上两个 systemd 单元——`linker-engine.service`（`/opt/linker-engine/current/.venv/bin/python -m uvicorn linker_engine.app:app --port 8901`，与既有 8443 TLS 入口复用）与 `linker-genie.service`（127.0.0.1:8902，经同一 8443 入口的 `location /genie/` 对外）；环境文件 `/etc/linker-engine.env`（`LINKER_ENGINE_FEED`、`LINKER_ENGINE_COMPATIBILITY`、`LINKER_ENGINE_CORS_ORIGINS=https://de-linker.com`）与 `/etc/linker-genie.env`（`GENIE_WP_URL`）；模型密钥走既有的 `~/.config/terravolt-builder/*.env` 回退路径（服务端安装，600）。引擎的 feed 在数据步之后从线上 `linker/v1/engineering-feed` 取（该路由随新插件部署才存在）。
- 2026-10-13（C15）：§4 的数据步在 `7-facts.py` 之后再跑同一写入器，计划是 `tools/migrate/c15-facts.json`。那份计划覆盖 #7 计划里没有的五台相位与功率；不进数据步就只存在于仓库，切换时落不了地。
- 2026-10-09（#5）：切换时写入两个选项，指向 VPS 上的服务：`linker_engine_url`（#14 的引擎）与 `linker_genie_url`（#13 的 Genie）。本地由 `just serve` 写入同名选项。
- 2026-10-11（#81）：脚本落在 `tools/cutover/`（uv 项目 `linker-cutover`，just 模块 `tools/cutover/cutover.just`），第 1–8 步各是一个可单独重跑的子命令；`just cutover drill <实例>` 在一台本地实例上跑完整切换、回滚、再切换，并写出 `docs/acceptance/<date>/17/drill.json`。同一份代码两个目标：`--target local:<实例>` 与默认的生产主机（`ssh hostinger-de-linker`），因此演练证明的是窗口里要跑的那份代码，不是一套排练装置。对本文的偏差与补给，逐条各有理由：
  - **§1 的 `wp db export` 换 mysqldump**。生产主机的 PHP `disable_functions` 含 `exec`，而 WP-CLI 的 export 在碰 mysqldump 之前先调 `exec()`（wp-cli/db-command `DB_Command.php:655`），在那里是致命错误；理由与脚本同 `docs/specs/6-live-pull.md` 的变更记录。备份与恢复都走 mysqldump/mysql，且两个脚本只读写标准流——本地实例与主机上运行的是同一段脚本。顺带修一处本地栈缺陷：MySQL 8.0.32 起，`--single-transaction`（线上与本地都在用的那个一致性开关）会先 `FLUSH TABLES`，那是全局权限，而 `linker_local` 只有自己库的权限，因此本地实例无法按线上的方式被 dump——`tools/local` 的建库路径现在补授 `FLUSH_TABLES, RELOAD`。
  - **§3 的 Polylang 用 WP-CLI 装**（`wp plugin install polylang --activate`），不是 rsync。原生安装器会核对 wordpress.org 的包；从某个检出 rsync 一份会是同一个插件的第二个、不可核对的来源。
  - **§3 的 snippets 导出落在仓库外**（备份目录里的 `snippets/`），仓库里只留"活动行的功能由新插件承接"的确认记录——导出按**实际 active 行**做（线上 2026-10-11 是 2 条，本文 §3 写的"三条"是 2026-10-09 的盘点）。理由：本仓库不携带旧树的自定义代码（AGENTS.md 第 5 节），而导出物的用途是那次确认。
  - 另有两处补进清单：§3 的删除清单按现状写成数据（`terravolt-b2b-core`、`linker-ai-assistant`、`code-snippets`、`woocommerce-gateway-stripe`、两个备份压缩包与 `terravolt-b2b-core-broken-20260704/`、旧 i18n 的 mu-loader）；`linker-i18n` 走同 slug 就地替换，不列删除。`linker-error-recorder.php` 保留——它**换成新件**而不是被拿走：`mu-plugins/linker-error-recorder.php`（#80）同名就地替换线上那份旧版本，`just cutover deploy` 的第一步就是它（记录件要在切换期间就在记），只有它自己的 `*.bak-*` 旧备份随其他残留一起清。
  - §6 的 hPanel 每分钟 cron 与 LiteSpeed 全清框不进脚本：那两件只能在主机的控制面板里做，脚本把它们打印出来，不声称做过。
  - 新增一步不在本文里：`just cutover schema` 退役留用的 SEO 插件自己那份 Product 模板（见下条）。
- 2026-10-11（#81，GAP-7 的核验与落点）：在产品页上用 curl 断言（证据见 PR 与 `docs/acceptance/2026-10-11/17/`）——留用的 SEO 插件**确实**输出一个 `Product` 节点，来源是它自己的 schema 模板库（一个 `seopress_schemas` 条目，规则匹配 `post_type=product`），内容是一条写死的模板：`"brand": "Linker"`、`"manufacturer": "Linker"`、`"category": "Energy storage system"`，没有 sku、model、image、description、availability。关掉它（或关掉它依赖的基座）该节点即消失（1 → 0），来源因此可证。而线上今天真正输出的那个节点来自切换要删掉的那个插件：sku、brand/manufacturer = 厂商名、model、category、description、image、offers{url, availability}，**无价格**。两者不等价，且模板库内容在仓库里不可见、不可测——所以按票面"补结构化数据输出"分支：产品页的 `Product` 节点由 `linker-commerce` 输出（`Storefront\ProductSchema`，与读同样字段的 `ProductView` 同处；语义与今天一致：无价格、availability 取 Woo 原生库存、brand 取产品自己的 `pa_brand`），SEO 插件模板库里那条 Product 模板由切换退役（`just cutover schema`：`wp post update … --post_status=draft`——该 CPT 不支持回收站，draft 同样不再被插件的查询取到，且可以手工放回）。`/products/` 的 CollectionPage/BreadcrumbList 与首页的 WebSite/Organization 仍由它输出，未动。§7 的只读回归因此多一条状态看不出来的断言：**产品页的 `Product` 节点恰为 1**（两个节点与一个节点都是 200）。
- 2026-10-11（#81，mu 目录的部署、清理与备份覆盖面）：`just cutover deploy` 把 `mu-plugins/*.php` 装进 `wp-content/mu-plugins/`（同名即替换；检出里没有该目录则停在这一步，而不是装完三个插件报成功）；`just cutover plugins` 用同一条 `*.bak-*` 规则清理 `wp-content/mu-plugins/`，其中被删的旧 i18n 垫片与记录件的旧备份**先复制到 `docs/acceptance/<date>/17/mu/` 再删**（§3 的 mu 卫生；那两份字节在站点上删掉之后仓库之外再无副本）。备份与回滚把 `wp-content/mu-plugins/` 与 `.htaccess` 一并覆盖：切换写这两处，回滚必须能还原，`drill` 的指纹把 mu 目录的内容也算进"回滚后与切换前逐项相同"。
- 2026-10-11（#81，§7 的邮件验收行对齐业主终裁）：原行写"邮件 24 小时内到达 sales@ 与 Bcc"，那是多封实发才能验的做法。业主 2026-10-11 的测试邮件纪律（AGENTS.md §5：测试只发一封、只发给 Chester，To/Cc/Bcc 一律重写为 `chester@de-linker.com`，多收件路由以 Outbox 队列的收件人数据断言）把它改成上面那条；窗口里那次真实询盘同样走这个开关，验证后关闭。
- 2026-10-11（#80）：部署面加错误记录件 `mu-plugins/linker-error-recorder.php`（轮转，非 WordPress 依赖）；mu 卫生点名旧 `linker-i18n-mu-loader.php` 与旧记录件备份进删除清单；数据步加存量客户迁移 `tools/migrate/80-customers.py`；验收加旧地址 301 抽验、存量客户状态与记录件实证。
- 2026-10-11（#80 修复轮）：抽验清单补上本轮数据化的两条线上硬编码规则——退役归档 `/shop/` 与英文 `/produkt/<撤回 slug>/` 别名基底（映射表 pages 的 `/shop/` 一条与 `requested_product()` 的路径解析），两者落点以线上实测为准。

- 2026-10-14（夜窗口的实际执行记录在 `docs/acceptance/2026-10-14/17/README.md`，此处只补规格缺口）：
  演练里看不到、窗口里必须有的步骤此后按三步补全——`wp linker-commerce present --user=<admin>`（表现层：
  LiveCanvas 模板 + partial + WindPress volume，`--allow-stale` 先行、浏览器编译后再净跑一次；
  2026-10-16 起净跑之后并排跑 `wp linker-commerce check --user=<admin>`——只读断言，0 行 exit 0
  才算部署面收口，见 `docs/acceptance/2026-10-16/h9-present-check/acceptance.md`）、
  WindPress 浏览器侧编译（唯一编译方式；线上以临时一次性登录桥驱动 `tools/windpress-compile.mjs`，用完即撤）、
  与 `12-site-chrome.py` / `page-template-empty.py`（改名与页模板，指向这两个脚本而非复制其规则）。
  服务侧两处必须在窗口内做、此前只写在运行面：`LINKER_ENGINE_CORS_ORIGINS` 之外，**PHP 侧对自签证书的
  钉扎**（`mu-plugins/linker-engine-pin.php` + `engine-ca.pem`，旧插件同名机制的移植）与**发布后重建 venv**
  （`uv sync --locked`；否则新 release 的 `current` 触发 203/EXEC）。引擎端点仍为 `https://<ip>:8443`；
  浏览器侧信任需具名域名的公共证书（DNS 在阿里云，见 README ⑨）。
