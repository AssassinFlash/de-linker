# Unified planner: time and measurement contract

2026-10-22. Implements the time-input portion of the numerical contract in
`docs/research/2026-10-22-planning-implementation/NUMERICAL-MODELS.md` §§3, 8.
It is part of the same active full delivery, not an alternative product scope.

1. Interval bounds are explicit, half-open and UTC-aware, with strictly
   positive duration and ordered, non-overlapping samples. A gap remains a gap;
   no inferred zero, row-count year or guessed final duration is allowed.
2. Imports require named columns, physical measurement boundary, interval
   average kW versus interval energy kWh, timestamp start/end convention, fixed
   duration or explicit end, timezone, source origin, delimiter and decimal
   convention. Net import is distinct from gross load; its signed values do
   not become gross consumption. Negative gross/PV/aux values are rejected.
3. CSV uses UTF-8, unique headers and ungrouped finite numbers. Comma decimals
   are explicit. Missing, malformed, non-finite, overlapping or reversed rows
   fail rather than silently coercing, sorting or deduplicating data.
4. Explicit ISO offsets determine real instants. Naive local timestamps use
   the named IANA zone. A repeated autumn time requires a stated offset or
   fold 0/1; a nonexistent spring time is rejected. An offset and fold cannot
   silently override one another. Start/end folds are mapped separately.
5. The intake adapter captures the actual timezone TZif bytes. Parsing uses
   these immutable bytes and records their SHA-256, not whichever rules happen
   to be installed on a later worker. Bad keys, mismatched rules or bad TZif
   bytes fail. Raw source hash and complete import mapping are retained.
6. Real calendar boundaries determine 23/25-hour local days and 8784-hour
   UTC leap years. Temporal horizons are not hard-coded as 24 or 8760 hours.
7. Regridding integrates actual overlap of interval means and preserves energy
   on the same covered horizon. Missing coverage fails explicitly. Alignment
   covers the first input's entire horizon using all source boundaries.
8. Refinement is a piecewise-constant reconstruction, not a new observation.
   Source origin and maximum native interval duration survive regridding,
   along with each transformation's input document hash, target axis hash,
   input/output interval durations and exact-copy flag. The effective coarsest
   interval and reconstruction flag survive intermediate aggregation as well:
   quarter-hour → hour → quarter-hour cannot recover measured peaks. Later
   peak/forecast/evidence checks must consume this history, rather than treating
   finer bins or original raw resolution alone as current measured precision.
9. Source/mapping and transformed interval/measurement details can be serialized
   as finite JSON and pinned as run inputs. The numerical dispatch layer must
   only accept appropriate physical measurement types.

The source/mapping describes supplied data and the chosen interpretation; it
does not by itself certify that an uploaded file is a verified physical meter
record. Independent tests exercise units, DST, gap/collision rejection, leap
years, energy-preserving overlap and provenance. This is no claim of PV,
controller, equipment or full production acceptance.
