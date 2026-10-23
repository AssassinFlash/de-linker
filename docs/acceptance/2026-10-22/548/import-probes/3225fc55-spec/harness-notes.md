# Independent harness corrections

Attempt1 had13 passes and one harness failure. The CSV recovery control automatically opens its retained original during hydration; the probe incorrectly waited for a closed-form entry button. The corrected probe waits for the actually rendered explicit retry control. No production source changed. Its original probe bytes, log and SHA metadata remain retained.

Background IDB completions also emitted React act warnings during attempt1. Added act-wrapped waiting for recovery hydration after dismissal and three controlled event-loop ticks before fixture disposal. These are harness scheduling changes, not changes to the expected behavior.

Attempt2 preserved13 passes and one harness transport failure: the real CSV route is `profiles/csv`; the independent stub mistakenly matched `profiles/import`. Corrected that route without changing product expectations, and act-wrapped direct IndexedDB observations so background hook completion remains inside the test action. Attempt2 source and logs are retained.

Final response-origin challenge uses `invalid_input` for the positive identified422 pair; generic `invalid_json_object` is deliberately excluded from positive guarantees because local response readers also emit it. Separate real-client200/502 non-object response counterexamples challenge that ambiguity. The initial matrix versions remain preserved with their original hashes.
