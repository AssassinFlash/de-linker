**Spec review: 0 findings.**

Reviewed exact diff `b5b89ee387fb55d85ad57ae7b4a0b9f8de65ea03...cbadc6198a9e0025c3eb5f949a1dac15e28dc292` against `docs/specs/548-pv-generation.md`, supported by `NUMERICAL-MODELS.md` §4.2 and the retained TMY/model evidence.

The implementation satisfies this backend increment’s requirements:

- It derives included module IDs, STC totals and composed ENU orientation from validated project geometry, verifies the weather anchor, and partitions actual active arrays into shared conversion groups.
- It keeps irradiance/weather units explicit, preserves original selected-year solar dates plus the reported offset, and separately declares the synthetic energy axis and representative-output reconstruction.
- It applies optical/DC factors once, combines DC before shared conversion and clipping, and retains intermediate witnesses. Nonzero invalid model output remains an error; the exact all-zero-irradiance branch precedes Perez evaluation.
- It binds owned source/model assets to the saved roof and parameter inputs, checks actual model-bundle contents, rejects stale references for new calculations, and reproduces historical runs using frozen dependencies.
- Equipment, country and near-shading limitations remain explicit. No public intake or live-runtime acceptance is claimed.

Independent focused verification: **57 tests passed in 9.92 seconds**, covering generation, actual full-year TMY intake and owned-profile/managed-worker integration, including an already queued run completing historically after a roof edit.

No source, instance, service, database, browser or tracker changes made.
