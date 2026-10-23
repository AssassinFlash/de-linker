# Create roof features in the shared map workspace

Continuation of the full active workbench goal, base `81524ca9`. Reuse the
accepted map drawing/recovery controller, geographic-to-roof projection, domain
commands and native project journal. No new library, geometry approximation,
provider request or separate scene is needed.

- Explicitly choose a roof and a new opening, obstacle or keep-out area. The
  original whole geometry and parent roof plane stay fixed. New object IDs are
  independent of the local journal ID, including a separate recovery copy.
  The selected roof and feature type remain visible while collecting corners
  and after restoring an unfinished drawing, before the properties form opens.
- Record an arbitrary open prefix, continue after pause/reload, remove the last
  corner, explicitly close/review, edit via the existing controller and continue
  adding corners. Partial work does not change the project or its undo history.
- Openings use the roof's source. Obstacles and keep-outs explicitly show a
  selectable existing source, name and respectively height/extrusion direction
  or reason. Heights are metres along the chosen axis, greater than zero. No
  default height/direction, changed source rights, assumed precision or provider
  licence promotion. Confirm that the recorded source covers the new feature.
- The strict v3 local payload retains kind, parent, source, fields, original
  numeric locale, vertices and stable object ID. v1 roof and v2 ring records
  remain readable in the same bounded CAS store; uncertain writes and native
  identity/recovery grants retain their current protections. Prepared results
  are accepted only when identical to the derived command result.
- Every shape/field/source edit invalidates prepared output and confirmation.
  Whole-frame changes refuse stale application. Explicit Apply checks the
  actual geometry service and refuses invalid target/parent, numerical limits,
  incomplete or truncated reports. Other layout conflicts remain reviewable.
- Persist prepared exact geometry before one grouped project command. Common
  undo/redo, plan/map/3D and Save/reopen consume it. Retire raw data only after
  exact native server acknowledgement. No renderer helpers enter domain data.
- Use the existing A/Journal controls, tokens and WindPress pipeline. New source
  and field feedback must be visible/focused on desktop and phone. The public
  property fragment restores design/Map. EN and independently composed formal
  DE receive adversarial copy review. Domain, actual React/journal/controller,
  true-engine counterexamples, Spec/Standards and native consumer proof remain
  separate gates. This increment does not close the full goal or its remaining
  engineering, country, report, site-consumer or production obligations.
