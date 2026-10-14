# /contact/ 卡渲染证据（2026-10-15，清账决策 2 评审修正轮）

本票（`fix/closure-contact-design`）把旧线上 contact 整卡移植进 `[linker_contact_form]`
之后，在**本地实例上真跑了一遍**集成用例与渲染——评审要求"至少在一台实例上把
`ContactFormMountTest` 真跑一次"，并把 CSS 的编译/渲染从"未跑"改为有据。

## 实例与命令

实例 `contactdesign`（`http://127.0.0.1:9005`），本 worktree 的三个插件以符号链接装入；
数据库是该实例装入线上快照（`~/de-linker-data/20261010-0027`）后跑 #9 德语迁移建成的
（快照里的德语还在旧插件的 `_linker_de_*` meta 里，Polylang 版由迁移生成）：

```
just up contactdesign --snapshot ~/de-linker-data/20261010-0027
just pull load contactdesign 20261010-0027
python3 tools/migrate/9-i18n.py --wp ~/de-linker-local/contactdesign/wp.sh --user 857558227@qq.com apply --write
#   → 335 imported, 330 synced, 5 not synced；/de/kontakt/ 200
just present contactdesign                      # 卷装入：contact-card.css 进 uploads/windpress/data + main.css 导入
just windpress-compile contactdesign            # 浏览器侧 Tailwind 编译
#   → cache recompiled (1792007243 -> 1792008431), anchor classes present
LINKER_WP_ROOT=~/de-linker-local/contactdesign/wordpress \
  php vendor/bin/phpunit -c phpunit.integration.xml.dist --filter ContactFormMountTest
#   → OK (3 tests, 33 assertions)；三个用例全跑（含德语用例，前一轮该用例因实例无德语页 skip）
```

## 截图（1440×900 / 390×844，EN / DE，视口对准卡）

每格两张，同一脚本同一轮拍：`<name>.png` 视口对准卡的顶端，`<name>-submit.png`
对准提交条（`scrollIntoView` 到 `.linker-form-primary`）——提交条在 390 的视口里不在卡顶那张
的范围内，故它由上表第二行与「实现值」段的探针数字共同作证。

| 文件 | 展示 |
|---|---|
| `en-1440.png` | 卡顶：眉题 CONTACT LINKER、What can we help with?、Your question（占位 What would you like to know?）、This about（A question）、分隔线、Where can we reply? 起始（Name / Reply email 同行） |
| `en-1440-submit.png` | 卡下：Company optional、免账号说明、同意行、Send message 通栏条（箭头在右）、脚注、两张副卡 |
| `de-1440.png` | 卡顶的德语：Wie können wir helfen?、Ihre Frage / Was möchten Sie wissen?、Es geht um / Eine Frage、Wohin dürfen wir antworten? 起始 |
| `de-1440-submit.png` | 卡下的德语：Unternehmen optional、…weder ein Konto noch ein **Projekt**、同意行（…Beantwortung dieser **Nachricht**… + Datenschutz）、Nachricht senden 通栏条、脚注、两张副卡 |
| `en-390.png` / `de-390.png` | 390 卡顶：字段单列（Your question → This is about → Where can we reply?）、Name 起 |
| `en-390-submit.png` / `de-390-submit.png` | 390 卡下：Reply email、Company optional、免账号说明、同意行、**Send message / Nachricht senden 通栏条（312 = 表单内宽）**、脚注、Prefer email? 副卡 |

## 浏览器里量到的实现值（与 `content/windpress/contact-card.css` 一致）

```
card  { w: 710 }                       # 与旧线上参考同宽（x682–1391 = 710）
form  { padding: 32px 32px, gap: 24px, radius: 22px, background: #fff, border: 1px }
rail  { columns: 347.203px 347.203px } # 卡下两张副卡，16px 间距
fields{ columns: 314.203px 314.203px } # Name / Reply email 同行（801px 以下折一列）
button{ width: 644, justify: space-between }   # 644 = 卡内宽 − 2×32，通栏条（与旧线上同形）
                                               # 390：submit 312 = 表单内宽，见 *-390-submit.png 与探针 metrics
```

## 同意行的实现值（本轮机读，1440/390 × EN/DE 四格一致）

上一轮这行还落在标记的工具类上（`text-xs text-neutral-600` / `mt-1`），实测是 15px /
`rgb(21,55,47)` / 13×13 方框 / 3px 上边距。本轮把它移到卡自己的样式表
（`contact-card.css` 的 `.linker-form-consent` 三条规则），**取值按旧线上参考卡**
（`contact-journal.css` 的 `.lkc-check` 与 `.lkc-check input|a`：11px、muted、18×18、
2px 上边距、链接下划线带 3px offset、10px 间距），颜色用现行 tokens：

```
consent { font-size: 11px, line-height: 20.35px (=11×1.85), color: rgb(90,99,99) = --proto-neutral-500, gap: 10px }
box     { 18×18px, margin-top: 2px, accent-color: rgb(12,127,115) = --proto-accent }
link    { color: rgb(12,127,115) = --proto-teal-600, text-decoration: underline, text-underline-offset: 3px }
```

选择理由（也写在 `copy-review.md` 的 **§2b「同意行的取值选择」**；§3 是另一件事——相对
旧线上的「有意差异」登记，本行与旧线上同值、不在其中）：/contact/ 是复刻面、像素门按旧线上卡逐行比，
同意行是可见面，取旧线上的几何；站内现行 tokens 提供颜色。另一条候选（#68 登记的
12px/neutral-600 + 浏览器默认 13px 方框）不取，故不上台账——本行与旧线上同值。

隐私链接：该实例原先没设隐私政策页（`get_privacy_policy_url()` 为空、页面不渲染链接），
本轮 `wp option update wp_page_for_privacy_policy 1673` 后链接出现，上表即其量值；
`underline` 工具类同族失效的问题因此不再影响本行（样式在卡的表里）。

## 上一轮那处异常：实测根因（本轮量到，替换上一轮的"成因不追"）

**现象**：第一轮编译后量到提交条 167px、`.linker-form-submit` 计算 `display: block`；
本轮量到同意行 15px / 13×13 方框，而标记声明的是 12px（`text-xs`）与 4px（`mt-1`）。

**根因**：编译缓存 `uploads/windpress/cache/tailwind.css` 里有**未分层**（不在任何
`@layer` 内）的规则

```
:where(#lc-header, #lc-footer, body[data-page] #theme-main) :where(*):not(svg, svg *, img, video),
:where(#lc-header, #lc-footer, body[data-page] #theme-main) :before,
:where(#lc-header, #lc-footer, body[data-page] #theme-main) :after { all: revert; }
```

（同类还有 `#theme-main:where(body[data-page] *), :where(#lc-header, #lc-footer){ all: revert }`）。
未分层样式压过 `@layer utilities`（层序先于特异度），所以 **`#theme-main` 这一页内容区
里的 Tailwind 工具类一律失效**：`display` 被 revert 回 `block`（提交条那处），
`font-size`/`color`/`margin` 被 revert 回继承或初始值（同意行这处）。

**对照实验**（`probe-card.mjs` 的 `controlProbe`，同一个
`class="grid text-xs text-neutral-600 mt-1"` 的 div 放两处）：

```
outside #theme-main: { display: grid, fontSize: 12px, color: neutral-600, marginTop: 4px }
inside  #theme-main: { display: block, fontSize: 16px, color: ink(#0c0f0f), marginTop: 0px }
```

所以上一轮"工具类在该环境可用"的句子的前提是**在 `#theme-main` 之外**；上一轮的探针把
控制 div 挂在 `document.body`（页头/页脚之外、`#theme-main` 之外），量不到该现象。
本轮的探针已把两个位置都记上，结论改为有前提的表述：**页头/页脚与 `#theme-main` 内**的
工具类被那条 `all: revert` 吃掉，其余位置正常。

**范围（不是孤立一处）**：插件的短代码输出里仍有多处把样式/布局交给工具类。本机复跑
`grep -rno 'class="[^"]*\(grid\|flex\|text-\|mt-\|p-[0-9]\|gap-\)[^"]*"' plugins/linker-commerce/includes --include="*.php"`
的**命中数/行数**（`grep -o` 计命中、`grep -c` 计行）：`Presentation/ComparePage.php`
**13 命中 / 12 行**（:209 一行两个 class 属性：`linker-compare-actions mb-4 text-sm` 与
`text-(--proto-accent) underline`；其余为 `linker-compare-cell … p-3 …`、
`linker-compare-chip … inline-flex …` 等）、`Presentation/LibraryPage.php` 11 命中 / 11 行
（`linker-documents … gap-6`、`linker-documents-count text-sm …` 等）、
`Presentation/Shortcodes.php` 1 命中 / 1 行（`linker-price font-semibold text-[#0c7f73]`）。
`Contact/Form.php` 3 命中 / 2 行（:167 同意行与 `mt-1`、:174 提交条）**本轮已全部由
`contact-card.css` 的自带规则承接**，不再依赖工具类。
在 `#theme-main` 内上面这些仍未覆盖的类同样失效；是否有卷内 CSS 兜住，本票只核了
contact 卡这一面，其余面未逐面核，故此处按面登记，不按"已关闭"记。

**处置与本票的范围**：contact 卡的所有可见组成（卡框、块间距、字段布局、提交条、同意行、
副卡、链接）现在都由 `content/windpress/contact-card.css` 自带规则承载，不再依赖工具类；
其余面（上段所列）不在本票改动层。
