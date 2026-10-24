# Saved solar source and model settings

This increment continues the complete unified Solution Configurator goal. The
whole-system Linker identity in `548-product-identity.md` remains the product
direction. A usable connected workflow must support that explanation; no source
form or dependency list is a substitute for the full equipment/report/inquiry
delivery.

The calculation workspace gains a weather-source view. Its actual form edits a
versioned `solar_setup` draft without automatically starting provider work.
Weather, scenario and history views retain their mounted controls so switching
views cannot discard unfinished numeric input. Incomplete numeric syntax blocks
native saving and dispatch; explicit roof-coordinate replacement may replace
unfinished coordinate text. Existing decimal fields retain their behavior;
calendar-year fields use whole-number input and validation.

Coordinates are explicit WGS 84 degrees or explicitly copied from the current
roof reference point. No postcode-derived location, Germany default, assumed
source period, terrain setting or synthetic year is inserted. Source years are
whole ordered calendar years. The expected radiation database checks the
provider's actual response; it is not a TMY database switch. Meteorology is ERA5.
The interpretation preserves original selected dates and the reported irradiance
offset, and uses an explicitly chosen non-leap synthetic UTC calculation year.
Provider availability is not inferred from the one retained Berlin response.

Preparation validates against the unmodified exported backend JSON schema and
semantic year checks, then writes `weather_acquisition` in the open project
draft. When replacing the effective source request, this explicit preparation
also clears the previous selected-weather binding and invalidates the prepared
energy replay. It retains saved assets/results, profile selections, entered
scenario/model parameters and unrelated edits. Unchanged preparation retains a
matching selection. Ordinary field edits alone do not remove or adopt a source.
Native Save project must confirm the input revision before the request
button enables. Dispatch uses the existing common planning-operation hook,
atomic durable intent, exact revision/key command and task history. No browser
provider credentials, actor choice, resource controls or arbitrary URL are sent.
The start handler rechecks saved/current equality, scope, syntax, outstanding
requests and project conflicts. Its late response is fenced by project/session
lifetime. Result selection remains the existing explicit source-selection step.

`solar_setup` also supports incomplete PV module/array/conversion drafts, read
from an existing accepted `pv_generation` when no draft exists. Its untouched
backend schema remains the final compiler contract. PV preparation checks the
current nonempty active layout, exact module set, a non-overlapping complete
partition into conversion groups, referenced north/location and complete safe
module-source references. Changing PV settings invalidates compiled generation
and prepared energy, while unrelated edits and the explicit historical weather
selection remain. No default losses, temperature coefficient or inverter
efficiency is invented.

The PV generation view now edits that same draft through module, array-model
and power-conversion sections. All remain mounted across view changes, including
unfinished signed and locale-specific numeric text. An explicit layout update
retains matching parameters, adds incomplete entries for new active arrays and
module specifications, and prunes obsolete entries. It never assigns numerical
values or converter membership. Each active array must belong to exactly one
conversion group. The UI prevents assigning an already assigned array to a
second group; the compiler independently validates the complete partition.

Module temperature coefficients are displayed in percent per degree Celsius
and converted once to 1/degree Celsius. Array transmission factors are retained
percentages, not loss percentages. Ground albedo is a reflected fraction. SAPM
a/b/deltaT and their mounting/source note remain explicit; b uses s/m and deltaT
is defined at reference irradiance 1000 W/m². Conversion groups have explicit
PVWatts DC reference W and nominal/reference efficiencies. A shared conversion
curve acts after summed array DC; independent already-clipped AC values are not
substituted. Bounds mirror the exported actual service schema. Document-reference
controls record an unverified reference; they do not acquire a datasheet or
establish its scientific/equipment authority. A novice model/source selection
workflow remains part of the full product delivery.

Prepare PV model compiles the current active geometry/model into the open draft.
Save project must confirm geometry, model and the selected owned weather before
the shared controller can send the minimal saved-revision PV command. The start
handler rechecks model equality, source selection, any declared effective weather
request's exact coordinates, syntax, scope, conflicts and outstanding intents.
The service independently validates the owned source and frozen model. Dispatch
and recovery use the same durable operation/history path as weather and energy.
The actual browser-to-ASGI contract executes the prepared model through the real
worker registry using retained full-year TMY. This proves the local saved-model
boundary; it does not establish an installed paired native runtime or live source
acquisition.

Independent form review reproduced percentage display artifacts (57 became a
long binary-derived decimal) and a related parent-echo loss of a typed decimal
separator. Percent/fraction presentation now shifts the declared decimal
exponent rather than multiplying/dividing binary values; it does not impose
an arbitrary precision cutoff. The shared numeric control preserves locally
emitted text while its parent echoes that value. External value or locale
changes still reformat, and explicit roof-coordinate replacement still resets
the fields. The same percentage boundary is applied to storage-efficiency
controls and their saved-basis display. Regression evidence includes actual
German PV controls for 57%, 56%, negative coefficients, a trailing comma,
conversion/storage efficiency and external restore/locale behavior.

The retained actual worker-produced fixture is shared by browser and service
contract tests. It contains real retained TMY bytes with explicitly synthetic
roof/model inputs and simulated provider transport. Isolated browser checks use
the actual form, shared controller and reviewed EN/DE catalogs at 1440/390. They
do not establish a native paired runtime install, live acquisition, weather
availability throughout Europe, engineering/country release or production
acceptance. Those remain full-goal gates, together with novice source discovery,
complete model entry, equipment compatibility, complete BOM/report/PDF and all
site/commerce consumers.
