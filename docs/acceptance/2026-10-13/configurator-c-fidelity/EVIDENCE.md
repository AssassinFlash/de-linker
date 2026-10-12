# fix/configurator-c-fidelity — 右侧输入屏的 C 视觉移植（证据）

正式配置器 `/linker-planner/`（本地实例 t109，插件软链到 `de-linker-worktrees/de-linker-cfg-c`）
的右侧从"无徽章粗体标题 + 单行选择卡 + 灰底分组框"改为原型 C 输入屏的样子：白卡片浮在浅色画布上、
组标签 chip、两行选择卡、分区头保持、"Calculate system" 落卡片右下深绿提交条。
B 左栏、引擎调用、加入 Lösungsentwurf、保存、设计报告、D2 手机换型滚动机制一律未动。

设计基准（只读）：`/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-proto-cfg/plugins/linker-tools/src/configurator/prototype/`
的 `proto-configurator.{css,js}`（variant C），本机在 t111（`http://127.0.0.1:8981/linker-planner/?variant=C&view=inputs`）截图。

## 1. 同尺度对照（原尺寸 1:1 裁切，两侧都不缩放）

两侧的并排图都是 **同一浏览器、同一视口宽、deviceScaleFactor 1 拍摄的全页截图的裁切**，
裁切窗口 = 视口宽 × 视口高，起点在该侧应用卡片顶边上方 24px；图片以固有尺寸显示（不设
`width`/`height`，`max-width: none`），所以并排图里 **1 图像像素 = 1 CSS 像素，左右一致**，
一张图上量到的元素尺寸可以直接和另一张图上量到的比。裁切只做平移，不做任何缩放。

脚本在出图时当场断言这一点（`img.getBoundingClientRect().width / img.naturalWidth`，两侧都必须
= 1.000），并把每个面板在成图中的矩形与它显示的源行写进 `measurements.json`
（`sheets.<name>.panels`、`sheets.<name>.imgScale`）。断言不通过脚本直接抛错。

独立复核（PIL，不依赖脚本自己的判断）：`python3 tools/cfg-c-scale-check.py <cmp-*.png>` 从
`measurements.json` 读面板矩形，按运行时的盒模型预测卡片边框该落在哪一行/哪一列，再在像素里找它：

```
$ python3 tools/cfg-c-scale-check.py cmp-1440-en-app.png
  proto    proto-c-inputs-1440-full.png: predicted rows 62..666, found 61..665 … height 604 px vs runtime 604 (1.0000x); borders at columns 301..1164 -> width 863 px vs runtime 864 (0.9988x)
  prod-en  prod-en-inputs-1440-full.png: predicted rows 62..376, found 62..376 … height 314 px vs runtime 314 (1.0000x); borders at columns 1805..2690 -> width 885 px vs runtime 886 (0.9989x)
$ python3 tools/cfg-c-scale-check.py cmp-390-en-app.png
  proto    … height 769 px vs runtime 769 (1.0000x); width 361 px vs runtime 362 (0.9972x)
  prod-en  … height 389 px vs runtime 389 (1.0000x); width 357 px vs runtime 358 (0.9972x)
```

1440-DE 与 390-DE 两张同法复核，数值与同宽的 EN 图逐项相同（原型侧一致；正式侧 DE 见 §5 的口径）。
比值 1.0000×0.9972 是 1px 边框取整的结果，不是缩放：上一版并排图把 1240px 宽的应用元素截图拉到
1440px 显示（1.1613×），已废弃，本轮全部重出。

| 文件 | 内容 |
|---|---|
| `cmp-1440-en-app.png` | 左=S 原型 C 输入屏、右=正式页 EN 应用区；两侧均为 1:1 原生裁切（左 `proto-c-inputs-1440-full.png` x=0 y=221、右 `prod-en-inputs-1440-full.png` x=0 y=115，均 1440×900） |
| `cmp-390-en-app.png` | 同上，390×844（左 y=255、右 y=148） |
| `cmp-1440-de-app.png` / `cmp-390-de-app.png` | 同上，正式页 DE（`/de/linker-planner/`，左 1440 y=221 / 390 y=255，右 1440 y=26 / 390 y=67） |
| `proto-c-inputs-{1440,390}-full.png` / `-viewport.png` | 原型 C 输入屏的全页与视口原图（并排图左栏的源） |
| `prod-en-inputs-{1440,390}-full.png` / `-viewport.png` | 正式页 EN 全页与视口原图（含站头站尾） |
| `prod-de-inputs-{1440,390}-full.png` / `-viewport.png` | 正式页 DE 全页与视口原图（见 §5 的本地口径） |
| `before/prod-before-1440-viewport.png` / `before/prod-before-390-viewport.png` | 打回态（主检出 main 的插件，改动前） |
| `roof-gap-1440.png` / `roof-gap-390.png` | 屋顶步打开时提交条下缘与屋顶面板上缘（§5a） |
| `d2-after-model-change-390.png` | D2：390 上算完再换型后的落点 |
| `measurements.json` | 两侧同选择器形状的 computed style + 盒模型（proto/prod-en/prod-de × 1440/390）、`footer-1440`/`footer-390`、`d2`、`sheets` |
| `tools/cfg-c-fidelity.mjs` | 产出以上全部的命令（本目录 `node tools/cfg-c-fidelity.mjs <out-dir>`） |
| `tools/cfg-c-scale-check.py` | 同尺度复核（PIL，见上） |

截图不是自证的全部：下面的数值来自同一脚本对两侧的 `getComputedStyle` 读取，且**与截屏同一次
页面加载**（本轮改为每次加载只取一次数据，量到的盒子就是图里的那份），逐项可比。

## 2. 清单（①–⑥，数值为 1440 视口实测）

| 要移植的要素 | 原型 C 实测 | 正式页实测（EN / DE 同） | 判定 |
|---|---|---|---|
| ① 整页容器：白卡片圆角浮在画布上 | `.pc-card` bg `#fff`、border `1px #dfe7ec`、radius `8px`、shadow `0 6px 24px rgba(23,38,54,.06)`；卡片内边距 30px（`.pc-body`） | `.linker-screen` 与 `.linker-section` 四项逐字相同（同一组声明，见 §7）；内边距 30px | 一致 |
| ② 组标签徽章芯片 | `.pc-fieldset legend span` bg `#f8fafa`、字色 `#0c7f73`、描边 `1px #dfe7ec`（底边 0）、radius `6px 6px 0 0`、padding `6px 10px`、uppercase、字距 `.08em` | `.linker-group > legend` 同五项同值（`letter-spacing` `.08em`，实测 C 1.28px vs 本站 0.88px 是字号差，见 §3） | 一致（字号按源码意图，见 §3） |
| ③ 项目类型：两行选择卡 | `.pc-check` 未选态 bg `#fff`、描边 `1px #dfe7ec`、radius `6px`、padding `9px 11px`、标题 13px 粗体、说明 10.4px/500 `#5f6b7c`；两列网格 `1fr 1fr`，gap `12px 16px` | `.linker-segments__tab` 未选态五项同值；标题 13px/700、说明 11px/500 `#5f6b7c`；两列网格 gap `12px 16px`；选中态=C 的描边高亮（accent 描边 + `#f1f9f8` 底） | 一致（选中态为既有实现，C 原型未定义） |
| ④ 分区头："粗体标题 + 右灰字 Step n · 说明" | `.pc-h h2` 19px/800、字距 `-0.01em`；`.pc-h-sub` 12px `#5f6b7c` | `.linker-block__title/.linker-section__title` 19px/800 `-0.01em`；`.linker-block__step` 12px `#5f6b7c` | 一致（本轮未改文案） |
| ⑤ 提交按钮：卡片右下深绿 | `.pc-footer` bg `#f8fafa`、上描边 `1px #dfe7ec`、padding `14px 22px`、下圆角 8px；`.pc-next` bg `#0c7f73`、radius `6px`、padding `9px 22px`、min-height 40px、右对齐 | `.linker-form__submit` 四项同值 + `.linker-button--primary` 同四项；实测盒 155×40 位于卡片右下（C 114×42） | 一致（按钮字重见 §3） |
| ⑥ 字号/间距/圆角/阴影 | 正文 13px/1.5；fieldset 内边距 `18px 14px 14px`；输入 min-height 40px、radius 6px、padding `8px 10px`，字号取源码写的 13.5px/500（**原型渲染是 16px/400**，见 §3）；字段标签 12.5px/700 | 应用根 13px/1.5；`.linker-group` 内边距 `18px 14px 14px`；输入 40px / 6px / `8px 10px` / 13.5px/500；`.linker-field__label` 12.5px/700 | 一致（输入字号同 §3） |

顺带对齐的细节：卡片间距 2rem、卡片最大宽 920px（`.pc-wrap` C=920，本站 stage 提到 920）、
select 的自绘箭头（C 的 chevron data-URI，`appearance:none`）、空态/提示框改为 C 的 note 盒
（`1px #dfe7ec` + `#f8fafa` 底 + radius 6px + `10px 12px`）、次要按钮取 C 的 `.pc-back` 形制。

## 3. 三处"取源码意图、不取原型渲染值"（实测记录，不是猜测）

原型自己的三条规则在 Chromium 里**不生效**：

```css
.pc-fieldset > legend { font: 800 11px/1 inherit; }        /* 实测渲染 16px/400 */
.pc-next              { font: 700 13px/1 inherit; }        /* 实测渲染 16px/400 */
.pc-field input,
.pc-field select      { font: 500 13.5px/1.3 inherit; }    /* 实测渲染 16px/400 */
```

`font` 简写不能以 CSS 级关键字（`inherit`）作 family，整条声明被丢弃，所以原型渲染出的是
继承/初始值 16px/400——三条紧接着的 `font-family: inherit` 是分开写的、有效，所以只有
weight/size/line-height 三个分量丢失。`measurements.json` 的
`proto-1440.chip.font`、`proto-1440.submit.font`、`proto-1440.input.font` 都是 `"16px 400"`，
而本站对应元素是 `11px 800`（chip）、`13px 700`（主钮）、`13.5px 500`（输入）。

移植取规则**写的值**（chip 11px/800、主钮 13px/700、输入 13.5px/500）：一是原型作者的意图就是
这三个值，二是本站控件字阶一致、输入不取正体细字更稳。差异只在三处小元素上，其余全部逐字相同；
若业主按渲染值判 chip/按钮/输入字大一号，改这三个值即可（各一处）。

三条都记为同一类决策（"取源码意图值"），不是因为第三条看起来更顺眼：判定依据同一——原型声明的
分量值 vs Chromium 丢弃该声明后的渲染值，两条都有实测。

## 4. 明确不做的（向业主说明，不擅自加）

- **C 的 TASK 区不搬**：`What should Linker work out?` 下拉与 `Similar systems` 是原型演示用的
  假输入，正式引擎没有这个输入（`residential-input.schema.json` 里无对应字段）。不伪造输入。
- **C 的顶部步骤进度条不搬**：B 左栏是业主选定的步骤导航，同一页不做第二个步骤指示。
- **选择卡里不做装饰性单选圆点**：正式卡是 `role="radio"` 按钮（无 `input`），选中由 C 的描边
  高亮表达；可访问名仍是标签本身（`aria-labelledby` 指向粗体标题、`aria-describedby` 指向说明），
  实测 aria 快照：`radio "Residential"` / `radio "Commercial & industrial"` / `radio "Utility"`。

## 5. DE 证据的本地口径（诚实记录）

- 线上 `/de/linker-planner/` 是 200（只读 GET 实测）。本实例原本没有任何德语页面（`/de/` 只有
  blog 壳），所以 DE 证据页是本实例新建的 3302 的**德语 twin**：`wp eval` 建页 + 设语言 `de` +
  `pll_save_post_translations`，再用 `wp post update 6574 --post_name=linker-planner` 设同 slug
  （本站 `linker-i18n` 的 SameSlug 机制，`plugins/linker-i18n/includes/SameSlug/PostSlugs.php`），
  最后 `wp cache_flush`（Redis 对象缓存会让直改库不生效）。页面挂载由实例本地 stand-in
  `100-t109-configurator-mount.php` 打印——与 EN 页同一条路径，该文件从不部署。
- **本实例没有德语 LiveCanvas partial**：德语页只显示德语 partial（`plugins/linker-i18n/includes/Twins.php`
  的类注释，LiveCanvas 4.9.3 `modules/templating.php:149`），本实例 `lc_partial` 仅 en 三条。
  因此本地 DE 页没有站头/站尾，应用区才是被比对的面；`cmp-*-de-app.png` 右栏即应用区裁切。
  这是本地快照的缺口，不是本次改动引入的差异（EN 页站头站尾齐全）。
- 上述缺口在 390 上有一个可见后果：D2 的步骤条是 `position: sticky; top: 89px`
  （`configurator.css` 的 `≤860px` 块，D2 已上线，本 PR 未动），它的流内位置本应在 89px 站头之下；
  本地 DE 页没有站头，流内位置落在 18px，于是被钉到 89px、压在卡片顶边上
  （`measurements.json`：`prod-de-390.steps.box = [16, 89, 358, 41]`、`prod-de-390.card.box = [16, 91, 358, 389]`，
  站头在位的 EN 页是 steps `y=131`、card `y=172`，不重叠）。所以 390-DE 那张并排图的右栏里，
  卡片顶边被这层半透明步骤条盖住，PIL 复核在该栏量不到顶边（记 0 个边框像素），
  改量底边：预测 451、实测 450（87 个边框像素），宽度 357/358（0.9972×），尺度仍成立。
  线上 DE 页有站头，不存在这一处遮挡。

### 5a. 提交条与屋顶步（本轮修复）

`.linker-form__submit` 的卡脚形态靠负外边距抵消卡片内边距（下缘 `-var(--linker-card-pad)`）。
它只在"提交条就是卡片末尾内容"时成立；屋顶步打开时（`RoofStep` 是 `<form>` 的兄弟），
负下边距与屋顶面板的 `margin-top: 24px` **相邻坍缩**，净 24-30 = **-6px**（390 上 24-18 = +6px，
即评审说的"24px 被压成 6px"）。本轮的修法：负下边距只给 `.linker-section > .linker-form:last-child`
的提交条，其后还要渲染东西时（屋顶面板或它的加载行）保底边距 0，并让后随块保留自己的上边距。
实测（`measurements.json` 的 `footer-1440` / `footer-390`，评审同法：提交条下缘到面板上缘）：

| 视口 | 关闭态 | 打开态 |
|---|---|---|
| 1440 | 提交条下缘 1355 = 分区底 1356 - 1px 边框（卡脚贴边） | 面板上缘 1379 − 提交条下缘 1355 = **gap 24px**，`overlaps: false` |
| 390 | 提交条下缘 1737 = 分区底 1738 - 1px 边框 | 面板上缘 1123 − 提交条下缘 1099 = **gap 24px**，`overlaps: false` |

修改前同法实测 1440 = **-6px**、390 = **+6px**（重叠/挤压），`roof-gap-{1440,390}.png` 是修后的
现场截图。

## 6. 跑过的检查（命令与结果）

| 检查 | 命令 | 结果 |
|---|---|---|
| 单元测试 | `plugins/linker-tools: npm run test:unit` | 16 文件 79 用例全过（含 `i18n.test.ts` 两条、`Steps.test.tsx` 三条 D2） |
| Storybook e2e | `plugins/linker-tools: npm run test:e2e` | 10 passed（Chromium），含屋顶步两条与手机宽度两条 |
| 构建 + 清单 | `npm run build`、`npm run build:check` | `build/` 与 src 同步（`build/` 随提交） |
| lint / 类型 / 格式 | `npm run lint:js`、`npm run lint:types`、`npm run lint:format` | 全过（prettier `All matched files use Prettier code style!`） |
| PHP 测试（整棵链路） | `just php-test` | `linker-commerce` 863 用例 **0 失败**（43 skipped）、`linker-i18n` 142、`linker-tools` 96、`mu-plugins` 6 全 OK |
| 禁用词 | `just banned-words` | clean |
| 空白符 | `git diff --check` | clean |
| 对照图同尺度 | `python3 tools/cfg-c-scale-check.py cmp-{1440,390}-{en,de}-app.png` | 见 §1：两侧均 1.0000×（高）/ 0.9972–0.9989×（宽，1px 边框取整） |
| 提交条 / 屋顶步间距 | `tools/cfg-c-fidelity.mjs` 的 footer 段 | 见 §5a：关闭态贴边、打开态 gap 24px、`overlaps: false`（1440 与 390） |
| D2（浏览器内，复用 `Steps.test.tsx` 的规则） | `tools/cfg-c-fidelity.mjs` 的 d2 段 | rail `position: sticky`、`top: 89px`、rail bottom 130px，Solution 标题 top 181px → **间距 51px ≥ 32px**，标题完整可见（844 视口内），且标题/分区**没有** sticky 祖先 |

上一轮记录的"main 侧既有红"（`PresentCommandTest` 的德语页头 twin 用例）在本轮 rebase 到
`c697e0c` 后已随主线的修复消失：本轮 `just php-test` 整链绿（上表）。
全树 `just check` / `just test` 的其他链（py-test、pull::test、cutover::test）本轮未重跑，
以本 PR 的 CI run 为准。

D2 一句：390 上算出方案后再换型（"Other inverter" 选第二项），页面滚回 Solution 分区，
标题不被钉住的步骤条盖住——`d2-after-model-change-390.png` 是那一刻的截图。

## 7. 提交内容

- `plugins/linker-tools/src/configurator/App.tsx`：`segments` 带 `scope`；头与项目类型块包进
  `.linker-screen` 卡片；卡片按 `aria-labelledby`/`aria-describedby` 提供两行内容与可访问名。
- `plugins/linker-tools/src/configurator/configurator.css`：C 的令牌与卡片/芯片/两行卡/卡脚条/
  按钮/输入/select 箭头/空态。本轮清理：`.linker-screen` 与 `.linker-section` 合并成一条卡片声明
  （五条重复声明去掉）、删掉 `.linker-block` 的空转重置规则（改为说明性注释）、删掉
  `.linker-empty--error/--none` 里已随基态变 solid 而失效的 `border-style`、`.linker-form__roof`
  的 `min-height` 对齐 2.5rem 控件尺度、提交条的负下边距改为只作用于卡脚位置（§5a）。
- `plugins/linker-tools/languages/linker-tools-de_DE_formal-linker-tools-configurator.json`：
  新串与定稿 DE，删去不再使用的 `Commercial` / `Utility-scale` 两键（`i18n.test.ts` 的
  "holds only texts the code uses" 是这道门）。
- `plugins/linker-tools/build/**`：构建产物。
- 本目录：证据（同尺度对照、复核脚本、测量、屋顶步间距）与文案评审。
