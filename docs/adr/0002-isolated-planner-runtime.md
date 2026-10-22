# Isolate the modern planner runtime from the site's React

Date: 2026-10-23. Status: accepted for implementation; runtime and production
acceptance remain pending.

The owner explicitly authorised new libraries and architecture for a modern,
correctly implemented unified planner, while requiring the existing site to
keep working. The planner therefore owns a separate React 19 module graph in
`apps/planner`, built with Vite and loaded by a dedicated WordPress module
entry; the site's React 18, Genie and classic scripts retain their existing
runtime. This makes the current stable React Three Fiber 9 / Drei 10 / Three.js
stack available without changing `wp.element` or mixing incompatible React
roots.

This is the runtime for the complete project application: intake, editing,
calculation control, comparison, evidence and delivery. 3D is one lazy-loaded
workspace, not the architecture's scope. Server-query state, editable domain
state and acknowledged immutable revisions have separate responsibilities;
the complete capability mapping is
[`CAPABILITY-MAP.md`](../research/2026-10-23-modern-workbench/CAPABILITY-MAP.md).

WordPress/WooCommerce still own identity, products and inquiries; the Python
workspace still owns immutable project revisions, jobs and results. Map, 2D
and 3D are views of those same domain objects, rather than separately saved
scenes. Three scene objects and GPU resources are disposable render state.

Vite produces static, hashed modules, not a production Node server. The app
uses the existing site tokens and WindPress stylesheet pipeline; there is no
second Tailwind compiler. Its deployment manifest and source hashes must be
checked alongside the plugin builds, including dynamically imported 3D chunks.
React types, JSX runtime and DOM root are private to this package. The PHP
mount supplies data and module URLs, with layout and styling kept in the app
and WindPress.

The implementation tests WebGPU-first through Three's WebGPURenderer and its
WebGL 2 backend against the same geometry, controls and selection behaviour.
Browser recovery, resource disposal and an accessible 2D path are explicit
application responsibilities. A renderer's shadows do not establish a solar
loss calculation, structural release or electrical compatibility.

Official package metadata, renderer constraints, coordinate conventions and
Apify provenance are recorded in
[`STACK-EVIDENCE.md`](../research/2026-10-23-3d-workspace/STACK-EVIDENCE.md).
Exact installed versions belong in the package lock. A passing package build
does not establish browser, site-consumer or production acceptance.
