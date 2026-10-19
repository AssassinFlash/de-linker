# #263 copy review

Ticket #263 changes link targets, not customer-visible wording. No new English
or German sentence is introduced. The visible labels the changed surfaces
print already exist and were reviewed in earlier tickets:

| Surface | Visible words | Source |
|---|---|---|
| Product category breadcrumb (DE) | `STARTSEITE`, `PRODUKTE`, and the German category names (`GEWERBESPEICHER`, `WECHSELRICHTER`, `HEIMSPEICHER`, …) | `_x( 'Home', 'breadcrumb', 'linker-commerce' )` and `__( 'Products', … )` in `plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po`; category names are the German term data reviewed for #254 (`plugins/linker-i18n/content/german-titles.json`). |
| Footer language switch | `English` / `Englisch`, `Deutsch` | `esc_html__('English')` is the existing `linker-commerce` catalog entry (`English` → `Englisch`); `Deutsch` is the language's own name and is printed as a proper noun in both languages, as the live footer does. |
| Product page button | `Produkt anfragen` | existing catalog entry, unchanged. |
| Compare breadcrumb | `Startseite`, `Home` | existing `linker-commerce` catalog entries and the repository LC templates, unchanged words. |
| Legal pages, blog posts, `/de/danke/` | no wording change; only the href of existing links | stored content, unchanged. |

Review result: no new copy to arbitrate. The German surfaces stay in Sie form
and use the §3 vocabulary (`Produkt`, `Produktkategorie`, `Lösungsentwurf`);
no banned word is added. Because no msgid or template word changed, no `.po`
regeneration is needed for this ticket.
