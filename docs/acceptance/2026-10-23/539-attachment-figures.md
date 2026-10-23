# Genie attachment figures after grounding

Base: `d84a5a77e23e8bcc3d0e348c99593f34f67038e8` (same tree as the
published `95f6cbe6` source). This fixes Genie answer sealing only. It does
not change the Solution Configurator, the engine, model routes, prompts,
budgets, authentication, attachment parsing or the WordPress proxy.

## Real failure and offline reproduction

A fresh guest uploaded an existing synthetic residential design report and
asked for its creation timestamp, annual consumption, PV array size, grid
connection, filename and page. The native reading contained all three pages,
including `2026-10-23 10:31:13 UTC`, `4,500 kWh`, `10 kWp` and page one. The
final answer retained the filename and `three-phase`, but its numeric values
and page numbers were empty. The stream still reported grounded, one attempt
and no fallback.

The original provider draft was not captured. The regression fixture keeps
the actual synthetic report reading and question, without conversation,
operation, account or credential identifiers. Tests construct a **synthetic
correct draft** using that reading's actual figure IDs. The real
`attachments.record → ground.check → hydrate → template.seal → cycle.run`
path accepts its grounding and hydrates every requested value, then the old
generic seal removes those values. A private replay of that draft reproduces
the captured final prose exactly. This proves the destructive sealing path;
it does not claim that the synthetic draft is the unseen provider draft.

The actual route was `model`. On a generic page, the old final numeric strip
licensed only digits printed in the question, even after a valid attachment
placeholder had been hydrated. The question named the fields without their
values. Unknown placeholders are not an alternative explanation: the native
hydrator leaves them visible and grounding rejects them. The actual reading
also rules out missing PDF text as the source of these missing values.

## Narrow repair and controls

Only the generic numeric-strip branch changes. For each text block, its own
`attN` reference licenses figure facts from that reading; an `attN.nK`
reference licenses only that figure. Both the reading and the figure must
exist with the native `read-attachment` source and the existing figure-ID
shape. Filename digits, raw reading text, unrelated files and other text
blocks add no allowance. Handoff summaries retain the question-only rule.

The earlier grounding check still requires placeholders for model-written
numbers, rejects unknown facts and forbids amounts of money from an
attachment. Clearance and documents branches, saved-solution handling and
all nonattachment behavior keep their existing rules. No blanket exemption
for a turn containing an attachment is introduced.

The new focused suite has **16 cases**. With the corrected fixture on the
original runtime it reports **8 failures / 8 passes**; with the repair all
16 pass. EN/DE and default/explicit generic page cases use the real cycle.
Other controls cover individual figure references, different or missing
readings, block isolation, filename and source isolation, handoff isolation,
unknown facts, invented bare numbers, attachment money, clearance,
documents and no-reading behavior.

```sh
cd services/genie
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_attachment_seal.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m ruff check src/linker_genie/template.py tests/test_attachment_seal.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m ruff format --check src/linker_genie/template.py tests/test_attachment_seal.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m mypy src/linker_genie/template.py tests/test_attachment_seal.py
```

Private raw capture, original red replay, differential controls and test logs
remain in the task's `attachment-diagnosis-539` evidence directory. The
initial test-writing run included two invalid `page_context.type=None`
fixture cases; that setup error is preserved separately and is not counted
as a runtime defect. The corrected cases omit the page context to use the
native default instead.

Related sealing, attachment, hydration, grounding, cycle, saved-solution and
campaign suites report **382 passed, 1 existing skipped, 6 existing xfailed,
26 deselected**. Ruff lint/format and strict mypy of both changed Python
files pass.

The default full suite is **not all green**: **2131 passed, 1 failed, 1
skipped, 6 xfailed, 195 deselected**. Its sole failure is the unchanged
`test_late_cancellation_resistant_escalation_cannot_allow_sending`: with a
20 ms deadline, it still returned the required `unknown/deadline`, but
reported zero escalation attempts where the fixture expected one. The same
case passes separately against both the original and repaired template;
its entire unchanged verdict test file passes **53/53**. The classifier has
no call into this sealing path and neither classifier source nor its tests
were changed. There is no clock trace proving why that full-run window
expired before escalation. The original failure and both controls are
retained; those controls do not turn the original full run into a pass.

No new model request, network, email or production write was used for this
repair. Independent reviews, exact CI and the coordinator's controlled Genie
service publication and live readback remain separate gates. The local
offline result does not pre-sign those gates or a new live provider answer.
