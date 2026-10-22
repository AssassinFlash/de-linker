# Roof fixture synchronization exposed by exact-head CI

Exact source CI [39744230597](https://github.com/AssassinFlash/de-linker/actions/runs/39744230597), at service head8292661b, passed `just check` but failed `just test`: 1 of465 JavaScript cases failed in `RoofStep.test.tsx` at `pointer(map)` because `map` was undefined. The failure occurred before any drawing assertions. It is retained as a real failure, not skipped or retried into a success claim.

The service patch changes no frontend source, dependencies, Vitest setup, workflow or build. Both RoofStep and its test/fake engine are byte-identical to deployed dcd5560d. The existing test was introduced with the finishing-click regression coverage in ecf49bea (PR492), whose real browser acceptance remains in `docs/acceptance/2026-10-21/484-485/`.

## Cause and controlled reproduction

`engine.place()` resolves asynchronously. Its callback sets `place` and the ready status together. The ready sentence becomes visible in a React commit; MapLibre construction happens in the passive effect that depends on `place`. `mount()` waited only for the ready sentence and immediately read `harness.maps[-1]`. The MutationObserver-based text waiter can resolve before the map effect runs, so that read can return undefined. This is test setup synchronization, not an observed customer interaction regression or a changed service contract.

The untouched test passed12/12 single-file runs locally with Node22.23.3; this is not claimed as a natural deterministic reproduction. To test the proposed ordering directly, a temporary25ms wrapper delayed passive-effect callbacks in the test only:

```tsx
vi.mock( '@wordpress/element', async ( importOriginal ) => {
    const actual = await importOriginal< typeof import( '@wordpress/element' ) >();
    return {
        ...actual,
        useEffect: ( callback: () => void | ( () => void ), deps: unknown[] ) =>
            actual.useEffect( () => {
                let cleanup: void | ( () => void );
                const timer = setTimeout( () => { cleanup = callback(); }, 25 );
                return () => { clearTimeout( timer ); cleanup?.(); };
            }, deps ),
    };
} );
```

Under the same controlled scheduling:

- Original helper: 2/2 failed; first reproduced `map.canvas` undefined, second exposed unready TerraDraw.
- Corrected helper: 2/2 passed, including all finishing-click, next-click, counts, time-window and refusal assertions.

The diagnostic wrapper was removed before commit. There is no hook mocking or added sleep in the final test. The sole test change is seven added lines: keep the ready-text assertion, then use the existing `waitFor` to require a canvas inside the mounted application before reading the fake map or dispatching pointer events. No assertion is removed, timeout increased, case skipped or product behavior changed.

## Final validation and scope

With the diagnostic removed, full Linker Tools unit suite: **54 files /465 tests PASS** (13.58s), using Node22.23.3. `lint:js` (zero warnings), `lint:types`, and Prettier check passed. No application/build/dependency file changes, no inclusion of the unrelated PR532, no production write, mail or model request.

This correction is a separate commit after8292661b so Spec/Standards can review only its incremental test and evidence delta. A new exact-head workflow_dispatch is required; the prior failed exact-source run is not reclassified as green.
