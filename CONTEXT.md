# CONTEXT

The repo's domain in one page. Consumer rules: engineering skills read this before
designing anything; ADRs under `docs/adr/` record decisions that changed it.

## What this is

de-linker.com — the B2B photovoltaic-and-storage **inquiry** site of Linker
Technology GmbH. WordPress + WooCommerce, English and German as equals
(`de_DE_formal`, Sie-form). Customers are installers, EPC contractors and
distributors. The only funnel: product categories and products → inquiry
(presented as a Proforma invoice) → everything afterwards is offline. There is
no checkout-payment-shipping chain; WooCommerce's checkout endpoint serves the
Proforma request page. Orders were repositioned as inquiries (owner, 2026-10-09).

## The two customer-facing tools

- **Genie** ("Genie – der KI-Assistent von Linker"; never "Linker Genie", no
  trademark): the platform AI assistant, embedded across products, inquiry and
  account. First message states it is an AI system.
- **Solution Configurator / Lösungskonfigurator**: input → whole-system
  proposal (addable to a solution draft) → design report (self-consumption,
  self-sufficiency, yield, sizing rationale, compatibility release, bill of
  materials; PDF with logo; no payback period). Roof drawing is one optional step.

## Vocabulary (binding)

Product / Produkt, product category / Produktkategorie — never catalogue or
article. Customer's working list: solution draft / Lösungsentwurf. List inside
a proposal: bill of materials / Stückliste. Inquiry statuses: Inquiry received /
Anfrage eingegangen · Proforma invoice issued / Proformarechnung ausgestellt ·
Completed / Abgeschlossen · Cancelled / Storniert. German cart words
(Warenkorb …) are banned; stock tells status only, never amounts.

## Architecture in one breath

React+TS on WordPress's own React for the existing plugin entries; the unified
planner is being built with an isolated modern runtime (see
`docs/adr/0002-isolated-planner-runtime.md`).
PHP 8.3 Composer PSR-4, PHPUnit/WP-Mock, PHPStan L8, WPCS+Woo sniffs;
FastAPI services on the VPS (engine: sizing/PVGIS/LoD2/report; genie:
grounded deepseek-flash chat over a hosted-PDF index, FTS5+sqlite-vec);
Polylang free + our narrow i18n companion plugin; presentation layer =
LiveCanvas dynamic templates + WindPress pipeline (plugins carry zero CSS for
site pages); production writes over SSH with backup-then-read-back; every
model call on one of the four owner-ruled channels (Genie=deepseek-flash
direct, Jev=OpenRouter systemone, gemini-embedding-2=OpenRouter, Jev-scorer=
deepseek-flash direct).

## Where the rules live

`AGENTS.md` is the binding rulebook (owner rulings by date, delivery gates,
model routing). This file summarises; AGENTS.md decides.
