# 空 Lösungsentwurf 说明 · 文案对抗评审

规则：AGENTS.md §2（2026-10-11：客户可见文案走对抗评审；EN 先行，DE 独立撰写）。术语锁：Solution draft / Lösungsentwurf。Sie 体。不承诺站点已撤掉的功能。

页面只留两个动作：浏览产品、注册登录。中间的批量货号导入对应 GAP-11（业主 2026-10-11 终裁不做），说明里不得再提货号匹配。

## 说明句

- EN 初稿：`You can browse the products and match an item-number list now. Adding to the solution draft is possible only after your account has been reviewed.`
  评审：后半句是账户审批的事实（票 #73），可留。前半句承诺货号匹配，站点没有这个入口（GAP-11）。删掉匹配，只留浏览。
  **定稿**：`Browse the products now. Adding to the solution draft is possible only after your account has been reviewed.`
- DE 初稿：`Sie können die Produkte durchsuchen und eine Artikelnummernliste abgleichen. Das Hinzufügen zum Lösungsentwurf ist erst nach der Kontoprüfung möglich.`
  评审：同一处承诺，且「Artikelnummernliste abgleichen」是从英文匹配句译过来的。独立写浏览，保留 Kontoprüfung 那句（与审批门同一事实，不是翻译腔）。
  **定稿**：`Durchsuchen Sie jetzt die Produkte. Das Hinzufügen zum Lösungsentwurf ist erst nach der Kontoprüfung möglich.`

标题与两个按钮沿用已定稿串，不新写：`Your solution draft is empty.` / `Ihr Lösungsentwurf ist leer.`；`Browse products` / `Zu den Produkten`；`Sign in or register` / `Anmelden oder registrieren`。

定稿落在 `Shortcodes.php` 的空态说明，以及 `linker-commerce.pot` 与 `linker-commerce-de_DE_formal.po`。
