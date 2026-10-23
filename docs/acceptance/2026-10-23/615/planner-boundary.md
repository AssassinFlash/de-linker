# Genie publication repair and the unified planner boundary

Read-only inspection on 2026-10-23 of the other worktree's `e0fa5557` source.
The planning contract is `docs/specs/548-workbench-application.md`, especially
clauses 8, 11 and 13–14. No files, running processes or configuration in that
worktree were changed by this ticket.

The planner owns versioned projects, input revisions, calculation runs,
candidates, historical artifacts and engineering handoffs. Its current
`planning/schema.py` has handoff fields for project, run, revision, candidate
and frozen snapshot SHA. That schema establishes identifiers, not proof that
all transfer and Genie reader paths already operate end to end.

The current publication repair can be reused at the consuming boundary:

- `Publication` owns current Woo product and document permission, stable
  revisions and immediate withdrawal. The planner's richer engineering graph
  still needs to depend on that authority rather than curate another SKU set.
- A signed Genie artifact is a product list, `kind=genie`, with immutable
  `selected.lines` labels and complete publication dependencies. It does not
  manufacture a residential input or a calculated yield/storage result.
- `AtomicSolutionDraft` accepts a trusted complete list and current dependency
  set. A future planner adapter can supply its frozen, owner-authorized
  candidate/BOM after checking the project/run/candidate identities; it must
  retain the planner's durable intent/receipt semantics rather than replace
  those with a second project store.
- The existing saved-solution adapter is retained for existing site actions
  and historical records. It is not the long-term project/revision model.
  Genie readers of planner results must use the planner's owning permission
  checks and explicitly distinguish selected historical runs from current
  results. Old snapshots cannot mint new current-product action tokens.

The generic publication dependency tuple does not encode user ownership,
input/run freshness, numerical applicability, stock or account price access.
Those remain required checks in the owning planner and Woo action boundary.
The signed token therefore cannot be reused as planner project authorization.
