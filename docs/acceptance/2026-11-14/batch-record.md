# 2026-11-14 本轮修复记录

每条都是「现象 → 根因 → 修法 → 线上实测」，不含未验证的结论。

## 1. 配置器推荐错误（业主指出的「组件型号错误」）

**现象**：住宅 10 kWp 请求，头号推荐 `SAJ H2-25K-T3`（25 kW 三相机，DC/AC 0.40）；列表混入 `GoodWe GW80K/99.99K/100K` + 112.6 kWh 商用柜 15 组；同一组合重复 4 次。

**根因（三个叠加，每个单独足以致错）**：
1. `equipment_search_space.py` 只用 `device_class` 取候选，从未使用 `pa_application`（产品数据 55 对 home / 30 对 commercial）。
2. 无 DC/AC 比例约束，25 kW 配 10 kWp 属"合法但荒谬"。
3. `ranking: not_performed_before_qualification`，按产品 ID 排序，头号方案纯属巧合。
4. `QuickStart.tsx` 从未发送 `application` 字段，使第 1 项成为死代码。

**修法**：
- `dfd413037`：application 过滤（未知保留）、DC/AC 带 60–135%（引 SolarEdge 过配说明与 Enphase 白皮书）、按适配度排序、同组合去重。
- `29e7c7857`：`quickStartInputs` 与 `mergeQuickStartInputs` 都发送 `application`。

**实测（生产，1440）**：

| 场景 | 修复前 | 修复后 |
|---|---|---|
| 住宅 10 kWp 首选项 | SAJ H2-**25K**-T3 | SAJ HS2-**10K**-T2-X |
| 住宅 8 kWp 前 6 项 | — | 全部 **8 kW** |
| 住宅 15 kWp 前 6 项 | — | 全部 **15 kW** |
| 商用 50 kWp 首选项 | — | GoodWe **GW80K** + 208.9 kWh |
| 商用机混入住宅 | **15 组** | **0 组** |
| 重复条目 | 4 | **0** |

## 2. 图片传输

| 页面 | 修复前 | 修复后 | 降幅 |
|---|---|---|---|
| services-support 1440 | 3,000,095 | **390,129** | −87.0% |
| for-epc 1440 | 2,712,283 | **585,763** | −78.4% |
| about 1440 | 2,199,546 | **238,437** | −89.2% |
| contact 1440 | 700,113 | **181,538** | −74.1% |
| PDP 主图 390 | 577,604 | **137,735** | −76.2% |
| PDP 主图 1440 | 577,604 | **242,552** | −58.0% |

根因三类：20 页正文手写 `<img>` 无 srcset；`sizes` 表手工维护追不上（改为 36 页 × 2 视口实测生成 76 条）；桌面端无条件下载 `display:none` 移动层 1,395,060 B。

## 3. CSS 背景图（`7333e8e2b`）

**现象**：services 页三张背景图 539,400 B，显示盒 342/720/529 px，文件 2560/2560/1672 px。

**修法**：`linker-the-kit-arrives-together-scaled` 原本无任何变体，用 `wp media regenerate --only-missing` 补齐 9 个尺寸；WindPress 按断点指定覆盖各自盒子的变体。

**实测**：390 = **43,702 B（−91.9%）**、768 = **27,116 B（−95.0%）**、1440 = **91,964 B（−82.9%）**。

## 4. planner-core 首屏拆分（`b9c8303b0`）

**现象**：首屏 chunk 1,447,770 B（gzip 379,820），配置器白屏约 10 秒。

**根因**：`Workspace.tsx` 静态导入 `ProjectEditor`（1012 行），后者又静态引入 `EnergyWorkspace`（2112 行）与 `DesignEditor`（834 行）。

**修法**：`React.lazy` + `Suspense`，编辑器在打开项目时加载（项目内已有 `LazySceneViewport` 同款模式）。

**实测**：首屏 **1,447.77 → 770.95 kB（−46.7%）**，gzip 379.82 → 214.52 kB；`ProjectEditor` 682.12 kB 转为按需。

## 5. 视觉修复

- **contact hero**：手机端 `heroH 170 / 裁切 50px / object-position 50% 36%` → **`heroH 300 / 裁切 0px / 46% 50%`**；768 裁切 263px → 133px。根因是同一组件两套断点几何不一致（桌面纵向填满、手机按宽度裁切）。
- **FAQ 胶囊**：`scrollbar-width: none` 把唯一可滚动提示也隐藏，第 3 个胶囊被裁半词。加边缘渐隐遮罩，EN/DE 实测生效。

## 6. 运维缺陷

- **管理员邮箱确认过期**：`admin_email_lifespan` 到期后 WordPress 把所有管理员登录重定向到 `confirm_admin_email`，`just windpress-compile-production` 报 302 失败。已按核心 `admin_email_check_interval` 续期 180 天。
- **部署残留**：生产 `wp-content` 积着 10-11 至 11-02 的 10 个 `.prev`，部署预检一见即 `exit 1`，等于每次发布被自己的旧残骸挡住。已留档清除。
- **快照轮转静默失效**（`004b94fff`）：`_verified` 要求 inode 完全一致，文件重写后校验永久失败，快照从上限 3 份涨到 **37 份 / 287 MB**。改为「stamp 快路径 + SHA256 内容校验」，cutover 305 测试通过。已回收 28 份 216.4 MB。
- **发布缺可用性自检**（`7e335b0b3`）：`activate` 成功、进程正常、读接口 200，但引擎读不到产品数据，全区 503。现在 worker 启动后、admission 恢复前，以服务用户读第一页产品，失败即回滚。

## 7. LCP / CLS 基线（首次测量）

| 页面 | LCP | CLS | TTFB |
|---|---|---|---|
| home EN 390 | 3,416 ms | 0.0028 | 1,720 ms |
| home EN 1440 | 3,396 ms | 0.0027 | 1,998 ms |
| home DE 390 | 4,312 ms | 0.0016 | 3,019 ms |
| home DE 1440 | 3,536 ms | 0.0031 | 1,841 ms |

CLS 全部远低于 0.1。LCP 中 TTFB 占大部（同机 GitHub TLS 握手也要 1.17 s，属测量点网络延迟）。

## 测量方法教训

本文件早期版本的图片数字曾用 `loading='eager'` 强制加载测得，会触发轮播隐藏幻灯片下载，把首页从约 299 KB 虚高到 1.9 MB。**此后所有数字统一采用自然懒加载**，方法不同者不得相减。

另外背景图一项我一度误报「字节反而上升」，原因是统计把 `<img>` 标签的图片也算进了背景图。只统计 CSS 实际引用的 URL 后才是真值。

## 三条被证据推翻的判断（留作方法警示）

1. **「opcache 命中率 0% 是全站 TTFB 根因」——错。**
   我用 `wp eval` 查 `opcache_get_status()` 得到 `hits=6 / misses=3894`，但连续查两次、中间打两个真实请求，数字**完全不变**：CLI 进程的 opcache 与 Web 的 lsphp worker 隔离，CLI 永远看不到 Web 统计。站点由 LiteSpeed + lsphp 提供服务（`php-fpm` 进程为零），`x-litespeed-cache: hit` 表明页面走全页缓存。缓存命中时真实 TTFB 是 **1.67–1.75 s**（各页一致），其中约 1.17 s 是同机 GitHub TLS 握手也有的网络延迟。之前 2.4–4.8 s 那组是用 `?cb=随机数` 绕过缓存测的，不能代表客户体验。

2. **「`planner-core` 混入 maplibre 与 Three.js」——错。**
   那两个词只是致谢链接表里的字符串 `"MapLibre GL JS": "https://maplibre.org/..."`。真库在按需 chunk 里。

3. **「34 个按钮无标签、5 个输入框无标签、1 张破图」——前两项是探针漏检。**
   探针只查 `aria-label`/`title`/文本，漏了 `aria-labelledby` 与 `placeholder`。EPC 页那 3 个按钮有 `aria-labelledby` 指向真实标题；首页 hero 输入框有 `placeholder`。修正探针后重跑。破图项两视口复测均不存在（HTTP 无 4xx），是首轮瞬时加载失败。

**真实缺陷**：PDP 主图按钮 `pdp-gallery-main-wrap` 只含 `<img>`、无任何可访问名称，德语 17 个产品页 × 2 视口全部命中。已加 `aria-label`（`61efd7ee4`）。

## 修完之后自己引入的缺陷（`15c10de20`）

`61efd7ee4` 上线后我验证两个语种，发现**德语页用的是英文句子**：

- EN：`Enlarge the product image: GoodWe ESA GW10K-EHA-G20 (10 kW single-phase power module)` ✓
- DE：`Enlarge the product image: … (10 kW einphasiges Leistungsmodul)` ✗

根因：新 msgid 在 `linker-commerce-de_DE_formal.po` 里没有条目，`__()` 回退到英文。同一文件里 `Produktbild` 系列翻译本来就存在，是我漏补。已按 Sie 体独立撰写 `Produktbild vergrößern: %s`，`msgfmt --check` 通过、MO 重编译并 `msgunfmt` 验证。

**可复用的检查点**：任何新增 `__()`/`_e()` 字符串，必须在同一批次内补德语 PO 并在两个语种的真实页面上各读回一次。只测英文会漏。
