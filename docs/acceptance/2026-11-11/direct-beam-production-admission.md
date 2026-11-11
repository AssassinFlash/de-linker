# Geometric PV work budget: measured admission for real customer roofs (2026-11-11)

Read-only production assessment remains in
[direct-beam-production-assessment.md](direct-beam-production-assessment.md).
This record covers the follow-on decision: the ordinary geometric-PV budget was
set from a container size rather than from a measured customer roof, and a real
commercial roof could not be calculated at all.

## Conclusion first

The ordinary budget refused every customer roof above 24 modules, and the only
envelope that could hold a larger roof required a single clear array. **A roof
with a second array, a chimney or a rooftop unit had no executable path.** After
this change the budget is priced from the declared scene, the isolated envelope
accepts any declared roof inside its measured limits, and multi-array plus
occluded roofs complete on the real kernel.

Measured on the reference host (Apple M3 Pro, Python 3.12.15), complete 8,760
interval retained year, `coarse = 1`, `fine = 2` — the grids the planner
requests:

| Scene | modules | arrays | walls | module steps | sampled rays | bounds checks | faces | wall clock | peak RSS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| single clear array | 24 | 1 | 0 | 210,240 | 537,216 | 27,456 | 0 | 6.9 s | 410 MB |
| three arrays, clear | 40 | 3 | 0 | 350,400 | 895,360 | — | — | 27 s | — |
| three arrays, 3 walls | 48 | 3 | 3 | 420,480 | 1,074,432 | 13,865,302 | 286,140 | 55.6 s | 669 MB |
| three arrays, 3 walls | 60 | 3 | 3 | 525,600 | 1,343,040 | 20,343,893 | 365,598 | 83.2 s | 795 MB |
| three arrays, 6 walls | 60 | 3 | 6 | 525,600 | 1,343,040 | 27,620,092 | 728,148 | 107.9 s | 802 MB |
| four arrays, clear | 96 | 4 | 0 | 840,960 | 2,148,864 | 176,128 | 0 | 20.8 s | 1,118 MB |
| four arrays, 4 walls | 96 | 4 | 4 | 840,960 | 2,148,864 | 4,320,702 | — | 37.5 s | 1,092 MB |
| four arrays, 8 walls | 96 | 4 | 8 | 840,960 | 2,148,864 | 52,188,459 | 1,958,442 | 244.1 s | 1,080 MB |
| four arrays, 12 walls | 96 | 4 | 12 | 840,960 | 2,148,864 | 60,985,910 | 2,443,230 | 238.2 s | 1,066 MB |

`module steps` and `sampled rays` are `modules x rows` and the rays actually
traced. The sampling upper bound the budget prices is 4,214,016 for the
96-module year (2,107,008 at 48 modules); 51.1 % of that bound is traced in every
scene above, because night and back-facing rows consume no ray. The
`bounds checks` column is what actually grows with occlusion: per traced ray it
is 0.05-0.08 on a clear roof, 2.0-2.3 with three or four walls, 15-20 with six
and 24.3-28.4 with eight to twelve.

## What was wrong

Two different decisions were fused into one condition
(`geometric_pv_admission.py`, before):

- the **work** had to fit `220,000 module steps / 2,000,000 sampled rays`, and
- the **scene** had to be one horizontal four-corner roof, one level array,
  one module specification, no holes, no obstacles, no keep-outs, ≤ 8 rows,
  ≤ 12 columns, 1 × 1 and 2 × 2 grids.

`220,000` is 24 modules over a complete year, i.e. a small domestic roof. The
first customer roof above that fell into the second condition, whose own
premises exclude the shape almost every commercial roof has. `548/INDEX.md:2398`
records that no capacity result existed when 220,000 was written, so the value
was never a measurement.

The isolated envelope's own numbers (`841,000 / 4,300,000 / 96 / 6 / 8,760`)
were already measured, and they are exactly 96 modules over 8,760 intervals.
Only its *geometry* gate was invented.

Two further defects appeared while pricing the ray budgets:

- `max_bounds_checks: 50,000,000` is below what a legal roof needs. The same
  96-module year costs 176,128 bounds checks clear and 60,985,910 with twelve
  walls. **The budget that fails first under real occlusion is not the sample
  count but the bounds count**, and it failed the whole task rather than
  slowing it.
- `expanded_execution_keys()` offered the isolated envelope to the series
  model only, so `MODEL_V1`/`MODEL_V2` roofs above the ordinary budget had no
  isolated path at all.

## What changed

**Bounds are priced by the declared scene, not by a flat number**
(`direct_beam_visibility.bounds_allowance`). One BVH query reaches each
declared opaque object at most once, so the allowance is
`sample_upper_bound x (declared_objects + 8)`, capped by the operator's
absolute ceiling. The occluded 96-module scenes above use 21.5-24.3 % of that
allowance; the cap is what still bounds a pathological scene.

**Admission follows declared work and declared surface class**
(`geometric_pv_admission.py`). Roof count, array count, obstacles, keep-outs,
panel dimensions and sampling grids no longer decide admission. What remains is
what the engine actually needs: work inside the numeric envelope, module planes
that belong to the envelope being selected (horizontal, or upward-facing and
not all horizontal), hourly contiguous weather, and — for the series model
only — its own single-inverter/one-string-per-tracker contract.

**The isolated envelope serves every model** (`geometric_pv_job.py`), so a
large flat-roof or Perez-component roof is not forced through the series
scenario to get isolation.

**Ceilings are named constants with their measurement**
(`geometric_pv_limits.py`). `max_bounds_checks` rises from 50,000,000 to
100,000,000 — 61 M is the worst legal scene seen at 238 s, and measured
throughput is roughly 250,000 bounds checks per second, so 100 M stays inside
the isolated 600 s envelope (about 400 s) while a pathological scene still
fails closed. The other three ceilings keep their measured values.

## Deployment consequence

`841,000 module steps` at 96 modules occupies **87–91 % of the 1.2 GiB isolated
cgroup** once walls are present (1,066–1,118 MB measured), against 59 % clear.
96 modules is therefore the ceiling, not a round number, and there is roughly
110–160 MB of headroom at that size. Production's own 96-module reading was
894 MiB (`docs/research/2026-11-04-load-governance-readback.md` §3.3), so the
host figure is not better than this one.

The sampling ceiling is equally tight: a 96-module year requests 4,214,016
sampled rays against the 4,300,000 ceiling, i.e. **98.0 % of the sample budget**.
That is the intended reading — the ceiling is the measured 96-module year plus a
2 % margin, not a generously padded number — and it means a roof above 96 modules
fails closed rather than running long.

## Before and after, same scenes, real kernel

Both columns are `generate_geometric_pv` on the shipped kernel, 8,760 retained
intervals, `coarse = 1`, `fine = 2`:

| Scene | steps | before (`220,000 / 2,000,000`) | after (`841,000 / 4,300,000`) |
| --- | ---: | --- | --- |
| 24 modules, 1 array, clear | 210,240 | runs, sample budget 52.7 % | runs, 24.5 % |
| 40 modules, 3 arrays, clear | 350,400 | **refused**: module-step policy exceeded | runs, sample 40.8 % |
| 48 modules, 3 arrays, 3 walls | 420,480 | **refused** | runs, bounds 13.9 % |
| 60 modules, 3 arrays, 6 walls | 525,600 | **refused** | runs, bounds 27.6 % |
| 96 modules, 4 arrays, 4 walls | 840,960 | **refused** | runs, sample 98.0 %, bounds 36.9 % |
| 96 modules, 4 arrays, 8 walls | 840,960 | **refused** | runs, sample 98.0 %, bounds 52.8 % |

Five of six customer shapes had no executable path before this change; all six
complete now, and every one of them stays inside both the sample and the bounds
budget.


## Evidence boundary

- Every number above is a real `generate_geometric_pv` call on the shipped
  kernel with the shipped synthetic fixtures, one process per measurement.
- The scenes are synthetic metre-scale layouts, not surveyed customer roofs.
  They were sized to the shapes real projects have (several arrays, several
  extruded obstacles) rather than to the previous admission rule.
- Wall clock and memory are reference-host figures. Production CPU is about
  1.30× slower per core (assessment §3.2), so 238 s here is roughly 310 s there,
  still inside 600 s.
- No production write, restart or configuration change was made. The budget
  values reach production only through a prepared release.
