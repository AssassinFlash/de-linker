# 空 Lösungsentwurf 说明 · 文案对抗评审

规则：AGENTS.md §2（2026-10-11：客户可见文案走对抗评审；EN 先行，DE 独立撰写非翻译）。术语锁：Solution draft / Lösungsentwurf；Sie 体。不承诺站点已撤掉的功能。

页面只留两个动作：浏览产品、注册登录。中间的批量货号导入对应 GAP-11（业主 2026-10-11 终裁不做，docs/audit/2026-10-11-surface-inventory.md：146 行），说明句里不得再提货号匹配——main 上的定稿串（`You can browse the products and match an item-number list now. …`）正是这一处承诺了站点没有的入口。

## 说明句

- 初稿（main 现状，EN）：`You can browse the products and match an item-number list now. Adding to the solution draft is possible only after your account has been reviewed.`
  评审：后半句是账户审批的事实（票 #73），可留。前半句承诺「匹配货号清单」，该入口已随 GAP-11 终裁不存在。删掉匹配，只留浏览。
  **定稿**：`Browse the products now. Adding to the solution draft is possible only after your account has been reviewed.`
- 初稿（main 现状，DE）：`Sie können die Produkte durchsuchen und eine Artikelnummernliste abgleichen. Das Hinzufügen zum Lösungsentwurf ist erst nach der Kontoprüfung möglich.`
  评审：同一处承诺（Artikelnummernliste abgleichen），且是从英文初稿直译来的。DE 独立重写：只写浏览，保留 Kontoprüfung 那句——它说的是审批门这同一事实。
  **定稿**：`Durchsuchen Sie jetzt die Produkte. Das Hinzufügen zum Lösungsentwurf ist erst nach der Kontoprüfung möglich.`

标题与两个按钮沿用已定稿串，不新写：`Your solution draft is empty.` / `Ihr Lösungsentwurf ist leer.`；`Browse products` / `Zu den Produkten`；`Sign in or register` / `Anmelden oder registrieren`。询盘页（LoginGate）的标题、说明与按钮串本轮未动，沿用 #148 的定稿。

定稿落在 `plugins/linker-commerce/includes/Presentation/Shortcodes.php` 的空态说明、`linker-commerce.pot` 与 `linker-commerce-de_DE_formal.po`（.mo 由 msgfmt 重新生成）。
