# fix/configurator-c-fidelity — 右侧输入屏的 C 视觉移植（证据）

正式配置器 `/linker-planner/`（本地实例 t109，插件软链到 `de-linker-worktrees/de-linker-cfg-c`）
的右侧从"无徽章粗体标题 + 单行选择卡 + 灰底分组框"改为原型 C 输入屏的样子：白卡片浮在浅色画布上、
组标签 chip、两行选择卡、分区头保持、"Calculate system" 落卡片右下深绿提交条。
B 左栏、引擎调用、加入 Lösungsentwurf、保存、设计报告、D2 手机换型滚动机制一律未动。

设计基准（只读）：`/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-proto-cfg/plugins/linker-tools/src/configurator/prototype/`
的 `proto-configurator.{css,js}`（variant C），本机在 t111（`http://127.0.0.1:8981/linker-planner/?variant=C&view=inputs`）截图。

## 1. 同视口对照（同一 chromium、同等待协议：fonts.ready + 逐屏滚动 + 图片 decode）

| 文件 | 内容 |
|---|---|
| `cmp-1440-en-app.png` | 左=S 原型 C 输入屏（1440×900 视口），右=正式页 EN 应用区；同高并排 |
| `cmp-390-en-app.png` | 同上，390×844 |
| `cmp-1440-de-app.png` / `cmp-390-de-app.png` | 同上，正式页 DE（`/de/linker-planner/`） |
| `prod-en-inputs-1440-full.png` / `prod-en-inputs-390-full.png` | 正式页 EN 全页（含站头站尾） |
| `prod-de-inputs-1440-full.png` / `prod-de-inputs-390-full.png` | 正式页 DE 全页（见 §5 的本地口径） |
| `before/prod-before-1440-viewport.png` / `before/prod-before-390-viewport.png` | 打回态（主检出 main 的插件，改动前） |
| `d2-after-model-change-390.png` | D2：390 上算完再换型后的落点 |
| `measurements.json` | 两侧同选择器形状的 computed style + 盒模型（proto-1440 / prod-en-1440 / prod-de-1440 / proto-390 / prod-en-390 / prod-de-390 / d2） |
| `tools/cfg-c-fidelity.mjs` | 产出以上全部的命令（本目录 `node tools/cfg-c-fidelity.mjs <out-dir>`） |

截图不是自证的全部：下面的数值来自同一脚本对两侧的 `getComputedStyle` 读取，逐项可比。

## 2. 清单（①–⑥，数值为 1440 视口实测）

| 要移植的要素 | 原型 C 实测 | 正式页实测（EN / DE 同） | 判定 |
|---|---|---|---|
| ① 整页容器：白卡片圆角浮在画布上 | `.pc-card` bg `#fff`、border `1px #dfe7ec`、radius `8px`、shadow `0 6px 24px rgba(23,38,54,.06)`；卡片内边距 30px（`.pc-body`） | `.linker-screen` 与 `.linker-section` 四项逐字相同；内边距 30px | 一致 |
| ② 组标签徽章芯片 | `.pc-fieldset legend span` bg `#f8fafa`、字色 `#0c7f73`、描边 `1px #dfe7ec`（底边 0）、radius `6px 6px 0 0`、padding `6px 10px`、uppercase、字距 `.08em` | `.linker-group > legend` 同五项同值（`letter-spacing` `.08em`，实测 C 1.28px vs 本站 0.88px 是字号差，见 §3） | 一致（字号按源码意图，见 §3） |
| ③ 项目类型：两行选择卡 | `.pc-check` 未选态 bg `#fff`、描边 `1px #dfe7ec`、radius `6px`、padding `9px 11px`、标题 13px 粗体、说明 10.4px/500 `#5f6b7c`；两列网格 `1fr 1fr`，gap `12px 16px` | `.linker-segments__tab` 未选态五项同值；标题 13px/700、说明 11px/500 `#5f6b7c`；两列网格 gap `12px 16px`；选中态=C 的描边高亮（accent 描边 + `#f1f9f8` 底） | 一致（选中态为既有实现，C 原型未定义） |
| ④ 分区头："粗体标题 + 右灰字 Step n · 说明" | `.pc-h h2` 19px/800、字距 `-0.01em`；`.pc-h-sub` 12px `#5f6b7c` | `.linker-block__title/.linker-section__title` 19px/800 `-0.01em`；`.linker-block__step` 12px `#5f6b7c` | 一致（本轮未改文案） |
| ⑤ 提交按钮：卡片右下深绿 | `.pc-footer` bg `#f8fafa`、上描边 `1px #dfe7ec`、padding `14px 22px`、下圆角 8px；`.pc-next` bg `#0c7f73`、radius `6px`、padding `9px 22px`、min-height 40px、右对齐 | `.linker-form__submit` 四项同值 + `.linker-button--primary` 同四项；实测盒 155×40 位于卡片右下（C 114×42） | 一致（按钮字重见 §3） |
| ⑥ 字号/间距/圆角/阴影 | 正文 13px/1.5；fieldset 内边距 `18px 14px 14px`；输入 min-height 40px、radius 6px、padding `8px 10px`、13.5px；字段标签 12.5px/700 | 应用根 13px/1.5；`.linker-group` 内边距 `18px 14px 14px`；输入 40px / 6px / `8px 10px` / 13.5px；`.linker-field__label` 12.5px/700 | 一致 |

顺带对齐的细节：卡片间距 2rem、卡片最大宽 920px（`.pc-wrap` C=920，本站 stage 提到 920）、
select 的自绘箭头（C 的 chevron data-URI，`appearance:none`）、空态/提示框改为 C 的 note 盒
（`1px #dfe7ec` + `#f8fafa` 底 + radius 6px + `10px 12px`）、次要按钮取 C 的 `.pc-back` 形制。

## 3. 两处"取源码意图、不取原型渲染值"（实测记录，不是猜测）

原型自己的两条规则在 Chromium 里**不生效**：

```css
.pc-fieldset > legend { font: 800 11px/1 inherit; }   /* 实测渲染 16px/400 */
.pc-next              { font: 700 13px/1 inherit; }   /* 实测渲染 16px/400 */
```

`font` 简写不能以 CSS 级关键字（`inherit`）作 family，整条声明被丢弃，所以原型渲染出的是
继承来的 16px/400：`measurements.json` 的 `proto-1440.chip.font = "16px 400"`、
`proto-1440.submit.font = "16px 400"` 就是它。

移植取规则**写的值**（chip 11px/800、主钮 13px/700）：一是原型作者的意图就是 11/800 与 13/700，
二是本站控件字阶一致、主钮不取正体细字更稳。差异只在两处小元素上，其余全部逐字相同；
若业主按渲染值判 chip/按钮字大一号，改这两个值即可（`--linker-*` 一处）。

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
  因此本地 DE 页没有站头/站尾，应用区才是被比对的面；`cmp-*-de-app.png` 右栏即应用区元素截图。
  这是本地快照的缺口，不是本次改动引入的差异（EN 页站头站尾齐全）。

## 6. 跑过的检查（命令与结果）

| 检查 | 命令 | 结果 |
|---|---|---|
| 单元测试 | `plugins/linker-tools: npm run test:unit` | 16 文件 79 用例全过（含 `i18n.test.ts` 两条、`Steps.test.tsx` 三条 D2） |
| Storybook e2e | `plugins/linker-tools: npm run test:e2e` | 10 passed（Chromium） |
| 构建 + 清单 | `npm run build`、`npm run build:check` | `build/` 与 src 同步（`build/` 随提交） |
| lint / 类型 / 格式 | `npm run lint:js`、`npm run lint:types`、`npm run lint:format` | 全过 |
| 禁用词 | `just banned-words` | clean |
| 空白符 | `git diff --check` | clean |
| D2（浏览器内，复用 `Steps.test.tsx` 的规则） | `tools/cfg-c-fidelity.mjs` 的 d2 段 | rail `position: sticky`、`top: 89px`、rail bottom 130px，Solution 标题 top 181px → **间距 51px ≥ 32px**，标题完整可见（844 视口内），且标题/分区**没有** sticky 祖先 |
| 全树检查 | `just check` / `just test` | 本机见 `/tmp/cfg-just-test.log`（记录在案）；CI 的 `check` 工作流跑完整 `just check` + `just test`，PR 上以 run 结果为准 |

D2 一句：390 上算出方案后再换型（"Other inverter" 选第二项），页面滚回 Solution 分区，
标题不被钉住的步骤条盖住——`d2-after-model-change-390.png` 是那一刻的截图。

## 7. 提交内容

- `plugins/linker-tools/src/configurator/App.tsx`：`segments` 带 `scope`；头与项目类型块包进
  `.linker-screen` 卡片；卡片按 `aria-labelledby`/`aria-describedby` 提供两行内容与可访问名。
- `plugins/linker-tools/src/configurator/configurator.css`：C 的令牌与卡片/芯片/两行卡/卡脚条/
  按钮/输入/select 箭头/空态。
- `plugins/linker-tools/languages/linker-tools-de_DE_formal-linker-tools-configurator.json`：
  新串与定稿 DE，删去不再使用的 `Commercial` / `Utility-scale` 两键（`i18n.test.ts` 的
  "holds only texts the code uses" 是这道门）。
- `plugins/linker-tools/build/**`：构建产物。
- 本目录：证据与文案评审。
