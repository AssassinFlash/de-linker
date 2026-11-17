# CONTEXT

The repo's domain in one page. Consumer rules: engineering skills read this before
designing anything; ADRs under `docs/adr/` record decisions that changed it.

## What this is

de-linker.com — the B2B photovoltaic-and-storage **inquiry** site of Linker
Technology GmbH. WordPress + WooCommerce, English and German as equals
(`de_DE_formal`, Sie-form). Customers are installers, EPC contractors and
distributors. The customer flow is products or a system proposal → inquiry →
Quotation / Angebot → offline confirmation and subsequent transactions. The
website issues quotations without bank details or payment instructions; invoicing,
payment and shipping stay offline (owner, 2026-11-08). Guests may submit inquiries
without accounts; the retained checkout endpoint is an inquiry entry, not a
payment flow. Historical Proforma URLs and stored identifiers do not define the
current customer-facing terminology.

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
Anfrage eingegangen · Quotation in preparation / Angebot in Vorbereitung ·
Completed / Abgeschlossen · Cancelled / Storniert. Customer-facing commerce
terms are maintained in `tools/checks/commerce-terms.txt`; stock tells status
only, never amounts.

Planning terms: a **weather source** is a retained original with its provenance
and declared time interpretation. **Weather acquisition** obtains that source;
selection into a project is a separate saved choice. **Remote cleanup** records
the external provider's completion or stop status for a cancelled acquisition.
**Weather reconciliation** verifies an issued external operation or retains its
original data; it does not select a source or complete the original evaluation.

## Architecture in one breath

React+TS on WordPress's own React for the classic plugin entries; the unified
planner has an isolated React/Vite runtime (see
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

Product and document publication has one business authority: WooCommerce. A
public document association is a document's current permission to serve a
published product; shared file bytes do not grant another product permission.
A historical snapshot records the customer's earlier result, rather than the
current product facts. The confirmed rules and acceptance cases are in
`docs/specs/609-product-publication.md`.

`AGENTS.md` is the binding rulebook for business constraints and delivery gates.
This file summarises; AGENTS.md and the user's latest explicit rulings decide.
