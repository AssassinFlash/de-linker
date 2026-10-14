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

| 文件 | 展示 |
|---|---|
| `en-1440.png` | 卡：眉题 CONTACT LINKER、What can we help with?、Your question（占位 What would you like to know?）、This is about（A question）、分隔线、Where can we reply?（Name/Reply email 同行、Company optional）、免账号说明、同意句、Send message 通栏条（箭头在右） |
| `de-1440.png` | 同一张卡的德语：Wie können wir helfen?、Ihre Frage / Was möchten Sie wissen?、Es geht um / Eine Frage、Wohin dürfen wir antworten?、Unternehmen optional、…weder ein Konto noch ein **Projekt**、…Beantwortung dieser **Nachricht**…、Nachricht senden 通栏条 |
| `en-390.png` / `de-390.png` | 390：字段单列、双列折成一列（Name → Reply email → Company）、提交条通栏 |

## 浏览器里量到的实现值（与 `content/windpress/contact-card.css` 一致）

```
card  { w: 710 }                       # 与旧线上参考同宽（x682–1391 = 710）
form  { padding: 32px 32px, gap: 24px, radius: 22px, background: #fff, border: 1px }
rail  { columns: 347.203px 347.203px } # 卡下两张副卡，16px 间距
fields{ columns: 314.203px 314.203px } # Name / Reply email 同行（801px 以下折一列）
button{ width: 644, justify: space-between }   # 644 = 卡内宽 − 2×32，通栏条（与旧线上同形）
```

## 本轮在渲染里发现并修掉的一处：提交条没有通栏

第一次渲染（编译后截图）量到按钮宽 167px（内容宽），与旧线上"提交条横跨卡"的形不同。
量法：Playwright 读 `.linker-contact-card .linker-form-primary` 的
`getBoundingClientRect().width`；同一轮 CDP `CSS.getMatchedStylesForNode`
(`.linker-form-submit`) 返回的 `display` 命中只有 UA 的 `div{display:block}` 与
`.grid{display:grid}`（Tailwind `@layer utilities`），而计算值 `block`——即当时那一轮里，
布局落在标记的工具类上没有生效。

处置：卡的组成不依赖工具类——`contact-card.css` 自己声明提交条与同意行的布局
（`.linker-form-submit{display:grid}`、`.linker-form-consent{display:flex;align-items:flex-start}`），
符合 AGENTS §5"样式只在 WindPress"。修后按钮宽 644（= 卡内宽 − 2×32），EN/DE 两侧一致。

对照探针（同实例、修后，见 `probe-card.mjs` 的 `controlProbe`）：在页面里新建
`div.grid` / `div.flex` 读到 `grid` / `flex`——工具类在该环境可用，故上面那一轮的读数
不写成"工具类不可用"的结论。成因不追（卡的布局已自带规则、渲染实测通过，本项以此关闭）。
