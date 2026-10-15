# 生产部署验收（2026-10-15）

本记录对应「像素债修复轮 + 清账轮」成果的一次性生产部署：本地 → 评审站（跳过，按业主夜间指令直连）→ 线上。
管线依据：`docs/specs/17-cutover.md` 与 2026-10-14 夜窗口执行记录（`docs/acceptance/2026-10-14/17/README.md`）。

## 1. 备份（先备份后写入）

- `just cutover backup` → `~/de-linker-data/cutover-20261014-2205/`
- 数据库 `db.sql.gz` 4,915,184 字节，sha256 `0a54390484b14588…`（全套见 manifest.json）
- wp-content（uploads/plugins/mu-plugins）+ options.json/.htaccess；**38,358 文件，manifest 已写**；共 4.2 GB
- 回滚命令：`just cutover rollback --backup ~/de-linker-data/cutover-20261014-2205`

## 2. 部署

- `just cutover maintenance on` → `just cutover deploy`（receipt：mu-plugins `linker-engine-pin.php`+`linker-engine-ca.pem`+`linker-error-recorder.php`+`linker-site-guards.php` 各就地替换；主题 `picostrap5-child-base/functions.php`；插件 linker-commerce **578** / linker-i18n **57** / linker-tools **141** 文件；`wp plugin activate` 三件齐）→ 后续维护窗关闭。
- 依 #17 补记的三步照跑：`present --allow-stale`（templates updated **8**；WindPress volume 安装；rollback 副本进 `linker_commerce_present_backup`）→ **WindPress 浏览器编译**（一次性登录桥 `tools/local/mu/001-linker-local-login.php` 临时部署 → mint → `tools/windpress-compile.mjs`：`{"compiled":true,"file_size":708563,"ms":63376}` → **登录件即时撤除**，mu 目录复核=hostinger×2+引擎钉扎(.php+.pem)+记录件+守卫+livecanvas）→ `present` 净跑（`cache is newer than the templates/tokens and contains the template classes`）。
- 缓存：Hostinger API `hosting_cache_clear-website`（"Request accepted"）+ `wp cache flush`（Success）。
- 冒烟：`/`、`/products/`、`/de/produkte/`、`/contact/`、`/de/kontakt/` 全 200；首页已引用新编译 `tailwind.css?ver=1792020656`。

## 3. 数据迁移（承载 DE 归档与分类关系修复）

- 首次 `just cutover data` 为**演练**（"dry run: add --write"）；`--write` 后 9-i18n 因 `setup --assign` 需要管理员而停——最终以 `just cutover data --write --administrator=857558227@qq.com` 执行：
- 7-facts：803 objects 全部已最新（`0 to apply, 803 done, 0 drifted`）；8-engineering 同；**9-i18n：imported 335/335、`Success: Post categories restored for 10 of the snapshot's 10 posts`**、`335 imported, 325 synced, 10 not synced`（10 个页面孪生留 pending 属既定状态）；`DATA_EXIT=0`。
- 复验：`/de/category/system-design/` → **200、`lang="de-DE"`、`<title>Systemauslegung`**、列出 `hybridwechselrichter-vs-ac-speicher`；德语单页 200 de-DE。

## 4. 探针断言（部署后 97 面重拍 + HTML 断言）

- 探针表：`.scratch/live-recheck/dom-counts.json`（新）对照 `dom-counts-20261014-before.json`（部署前）；脚本 `assert-postdeploy.py`：**30/30 PASS**（短代码字面量全站 0、contact 双语表单 form=1 无兜底行、搜索面无产品条目、九类 DE 目录无旧页指纹、筛选计数 1-24/38、抽屉 filterOpen=true、DE 归档 200 de-DE）。
- HTML 级复验：solution/EPC/services/博客单页 EN+DE 字面量 **0**；contact 整卡 `linker-contact-rail` 双语言在位；`/products/?brand=goodwe&sort=name` 首卡 GoodWe ESA（排序生效）；aio 侧栏含 Inverters 行；空草稿 `sf-cart-empty` 两按钮无 item-number。

## 5. 修复面 SRC|REP 对照（旧线上参考 | 现线上）

` .scratch/live-recheck/deploy-evidence/` 内（对照图与放大图；原图不进仓库，路径可复跑）：

- `CMP_sol-util-EN1440`、`CMP_epc-EN1440`、`CMP_contact-EN1440`、`CMP_cat-aio-EN1440`、`CMP_blogpost-EN1440`、`CMP_search-EN1440`、`CMP_cart-EN1440`、`CMP_shop-filt-EN1440`
- 等高（结构对齐的最强信号）：cat-aio 1177=1177、blogpost 1956=1956、search 1532=1532、shop-filt 4106=4106（缩放像素）；contact 1566/1561、epc 4208/4180 近等；sol-util 3901/4147（联系带恢复增高，方向正确）。
- 放大：`ZOOM_cat-aio-card1-specs.png` / `ZOOM_cat-aio-card1-full-specs.png`（发现第四格差异 → 见 §7 修复 #172）。

## 6. 旧品牌清除（DB 内容）

- 全库扫描 `post_content LIKE '%terravolt%'`：36 处（模板 5、页面 10、草稿 3、ACF 3、附件 3、修订 23 等）。
- **真缺陷**：多张页面内联 `@font-face` 指向**已删除旧插件**的字体文件（404 死链）→ 删除整块 `@font-face{…terravolt-b2b-core…}`；模板注释/ACF 描述/附件文本 TerraVolt→Linker、`terravolt-b2b-core`→`linker-commerce`（before 件存 `deploy-evidence/post-<id>-terravolt-before.txt`）。
- 二次扫描发现 **DE 产品归档模板可见水印「TERRAVOLT」**（全大写躲过首轮替换；`/de/produkt-kategorie/*` 与 `/de/produkte/` 正在渲染）→ 替换为 LINKER，复验渲染面 0。
- 保留项（如实记录）：draft 页面 693 的 ACF 字段名 `terravolt_relevance`（内部标识符，与允许保留的 tv-* id 同类；未发布面）；23 条修订版（不可见历史，随修订策略自然淘汰）。
- 复验：关键页 EN/DE 大小写不敏感扫描 0。

## 7. 部署后收口修复（本轮发现本轮修）

- **#172 identity() 的 kind 兜底**：ESA GW125/261 等 265 台带 `_delinker_type` 但无 registry 绑定的产品，卡片落 'other' 序（第四格 Max. efficiency 而非 Ingress protection IP54，见 ZOOM 图）→ identity() 读产品自带类型；已绑定产品零影响。合并后增量部署（deploy + 缓存）并线上 eval 复验。
- **数据迁移首次执行的 dry-run 陷阱**与 `--administrator` 依赖已如实记入流程笔记（pipeline 用 pipefail 复跑）。

## 8. 已知且有意保留的差异（变更台账口径）

- 工具页（Genie/配置器/compare）为已批准重设计，不受复刻像素门约束。
- 页头微调（下划线几何/分隔线/390 位移）＝ Q5a 已批（台账族 24 收口段）。
- Batch item numbers / Nameplate photo 两芯片按业主 2026-10-13「不补齐」保持移除；空草稿 CTA 两枚（GAP-11）。
- 全站冷色调/字体（tokens 权威）为 2026-10-13 裁定。
