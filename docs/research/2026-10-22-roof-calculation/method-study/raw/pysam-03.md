# BatteryStateful — NLR-PySAM 8.0.0 documentation

BatteryStateful has two major differences from the Battery module: 1) it contains only the “physical” component models of the battery (thermal, voltage, capacity, lifetime) and none of the dispatch methods (peak shaving, etc) of the Battery module; 2) the Battery module runs annual or multi-year simulations in a single execution, whereas BatteryStateful is run one timestep at a time using control variables, current or power, and can be run at sub-minute timesteps.

PySAM.BatteryStateful.default(_config_) → [BatteryStateful](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful "PySAM.BatteryStateful.BatteryStateful")[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.default "Link to this definition")

Load defaults for the configuration `config`. Available configurations are:

> *   _“LFPGraphite”_
>     
> *   _“LMOLTO”_
>     
> *   _“LeadAcid”_
>     
> *   _“NMCGraphite”_
>     

Note

Some inputs do not have default values and may be assigned a value from the variable’s **Required** attribute. See variable attribute descriptions below.

PySAM.BatteryStateful.from\_existing(_data_, _optional config_) → [BatteryStateful](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful "PySAM.BatteryStateful.BatteryStateful")[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.from_existing "Link to this definition")

Share data with an existing PySAM class. If `optional config` is a valid configuration name, load the module’s defaults for that configuration.

PySAM.BatteryStateful.new() → [BatteryStateful](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful "PySAM.BatteryStateful.BatteryStateful")[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.new "Link to this definition")

PySAM.BatteryStateful.wrap(_ssc\_data\_t_) → [BatteryStateful](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful "PySAM.BatteryStateful.BatteryStateful")[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.wrap "Link to this definition")

Load data from a PySSC object.

Warning

Do not call PySSC.data\_free on the ssc\_data\_t provided to `wrap()`

BatteryStateful is a wrapper for the SSC compute module [cmod\_battery\_stateful.cpp](https://github.com/natlabrockies/ssc/blob/develop/ssc/cmod_battery_stateful.cpp)

## Interdependent Variables[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#interdependent-variables "Link to this heading")

The variables listed below are interdependent with other variables. If you change the value of one of these variables, you may need to change values of other variables. The SAM user interface manages these interdependent variables, but in PySAM, it is up to you change the value of all interdependent variables so they are consistent. See [Interdependent Variables](https://nrel-pysam.readthedocs.io/en/main/interdependent-variables.html) for examples and details.

*   None
    

## Functions[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#functions "Link to this heading")

_class_ PySAM.BatteryStateful.BatteryStateful[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful "Link to this definition")

This class contains all the variable information for running a simulation. Variables are grouped together in the subclasses as properties. If property assignments are the wrong type, an error is thrown.

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.assign "Link to this definition")

Assign attributes from nested dictionary, except for Outputs

`nested_dict = { 'Controls': { var: val, ...}, ...}`

execute(_int verbosity_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.execute "Link to this definition")

Execute simulation with verbosity level 0 (default) or 1

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.export "Link to this definition")

Export attributes into nested dictionary

get\_data\_ptr() → Pointer[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.get_data_ptr "Link to this definition")

Get ssc\_data\_t pointer

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.replace "Link to this definition")

Replace attributes from nested dictionary, except for Outputs. Unassigns all values in each Group then assigns from the input dict.

`nested_dict = { 'Controls': { var: val, ...}, ...}`

setup() → None[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.setup "Link to this definition")

Setup parameters in simulation

unassign(_name_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.unassign "Link to this definition")

Unassign a value in any of the variable groups.

value(_name_, _optional value_) → None | float | dict | sequence | str[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.value "Link to this definition")

Get or set by name a value in any of the variable groups.

## Controls Group[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#controls-group "Link to this heading")

_class_ PySAM.BatteryStateful.BatteryStateful.Controls[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.Controls "Link to this definition")

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.Controls.assign "Link to this definition")

Assign attributes from dictionary, overwriting but not removing values.

`Controls_vals = { var: val, ...}`

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.Controls.export "Link to this definition")

Export attributes into dictionary.

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.Controls.replace "Link to this definition")

Replace attributes from dictionary, unassigning values not present in input `dict`.

`Controls_vals = { var: val, ...}`

control\_mode[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.Controls.control_mode "Link to this definition")

Control using current (0) or power (1) \[0/1\]

**Required:** True

Type:

_float_

dt\_hr[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.Controls.dt_hr "Link to this definition")

Time step in hours \[hr\]

**Required:** True

Type:

_float_

input\_current[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.Controls.input_current "Link to this definition")

Current at which to run battery \[A\]

**Required:** Required if control\_mode=0

Type:

_float_

input\_power[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.Controls.input_power "Link to this definition")

Power at which to run battery \[kW\]

**Required:** Required if control\_mode=1

Type:

_float_

## ParamsCell Group[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#paramscell-group "Link to this heading")

_class_ PySAM.BatteryStateful.BatteryStateful.ParamsCell[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell "Link to this definition")

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.assign "Link to this definition")

Assign attributes from dictionary, overwriting but not removing values.

`ParamsCell_vals = { var: val, ...}`

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.export "Link to this definition")

Export attributes into dictionary.

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.replace "Link to this definition")

Replace attributes from dictionary, unassigning values not present in input `dict`.

`ParamsCell_vals = { var: val, ...}`

C\_rate[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.C_rate "Link to this definition")

Rate at which voltage vs. capacity curve input

**Required:** Required if voltage\_choice=0&chem~2

Type:

_float_

Qexp[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.Qexp "Link to this definition")

Cell capacity at end of exponential zone \[Ah\]

**Required:** Required if voltage\_choice=0&chem~2

Type:

_float_

Qfull[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.Qfull "Link to this definition")

Fully charged cell capacity \[Ah\]

**Required:** True

Type:

_float_

Qfull\_flow[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.Qfull_flow "Link to this definition")

Fully charged flow battery capacity \[Ah\]

**Required:** Required if voltage\_choice=0&chem=3

Type:

_float_

Qnom[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.Qnom "Link to this definition")

Cell capacity at end of nominal zone \[Ah\]

**Required:** Required if voltage\_choice=0&chem~2

Type:

_float_

Vcut[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.Vcut "Link to this definition")

Cell cutoff voltage \[V\]

**Required:** Required if voltage\_choice=0&chem~2

Type:

_float_

Vexp[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.Vexp "Link to this definition")

Cell voltage at end of exponential zone \[V\]

**Required:** Required if voltage\_choice=0&chem~2

Type:

_float_

Vfull[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.Vfull "Link to this definition")

Fully charged cell voltage \[V\]

**Required:** Required if voltage\_choice=0&chem~2

Type:

_float_

Vnom[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.Vnom "Link to this definition")

Cell voltage at end of nominal zone \[V\]

**Required:** Required if voltage\_choice=0&chem~2

Type:

_float_

Vnom\_default[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.Vnom_default "Link to this definition")

Default nominal cell voltage \[V\]

**Required:** True

Type:

_float_

calendar\_a[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.calendar_a "Link to this definition")

Calendar life model coefficient \[1/sqrt(day)\]

**Required:** Required if life\_model=0&calendar\_choice=1

Type:

_float_

calendar\_b[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.calendar_b "Link to this definition")

Calendar life model coefficient \[K\]

**Required:** Required if life\_model=0&calendar\_choice=1

Type:

_float_

calendar\_c[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.calendar_c "Link to this definition")

Calendar life model coefficient \[K\]

**Required:** Required if life\_model=0&calendar\_choice=1

Type:

_float_

calendar\_choice[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.calendar_choice "Link to this definition")

Calendar life degradation input option \[0/1/2\]

**Options:** 0=None,1=LithiumIonModel,2=InputLossTable

**Required:** Required if life\_model=0

Type:

_float_

calendar\_matrix[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.calendar_matrix "Link to this definition")

Table with Day # and Capacity % columns \[\[\[#, %\]\]\]

**Required:** Required if life\_model=0&calendar\_choice=2

Type:

_sequence\[sequence\]_

calendar\_q0[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.calendar_q0 "Link to this definition")

Calendar life model initial capacity cofficient

**Required:** Required if life\_model=0&calendar\_choice=1

Type:

_float_

chem[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.chem "Link to this definition")

Lead Acid (0), Li Ion (1), Vanadium Redox (2), Iron Flow (3) \[0/1/2/3\]

**Required:** True

Type:

_float_

cycling\_matrix[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.cycling_matrix "Link to this definition")

Table with DOD %, Cycle #, and Capacity % columns \[\[\[%, #, %\]\]\]

**Required:** Required if life\_model=0

Type:

_sequence\[sequence\]_

initial\_SOC[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.initial_SOC "Link to this definition")

Initial state-of-charge \[%\]

**Required:** True

Type:

_float_

leadacid\_q10[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.leadacid_q10 "Link to this definition")

Capacity at 10-hour discharge rate \[Ah\]

**Required:** Required if chem=0

Type:

_float_

leadacid\_q20[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.leadacid_q20 "Link to this definition")

Capacity at 20-hour discharge rate \[Ah\]

**Required:** Required if chem=0

Type:

_float_

leadacid\_qn[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.leadacid_qn "Link to this definition")

Capacity at discharge rate for n-hour rate \[Ah\]

**Required:** Required if chem=0

Type:

_float_

leadacid\_tn[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.leadacid_tn "Link to this definition")

Hours to discharge for qn rate \[h\]

**Required:** Required if chem=0

Type:

_float_

life\_model[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.life_model "Link to this definition")

Battery life model specifier \[0/1/2\]

**Options:** 0=calendar/cycle,1=NMC,2=LMO/LTO

**Required:** True

Type:

_float_

maximum\_SOC[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.maximum_SOC "Link to this definition")

Maximum allowed state-of-charge \[%\]

**Required:** True

Type:

_float_

minimum\_SOC[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.minimum_SOC "Link to this definition")

Minimum allowed state-of-charge \[%\]

**Required:** True

Type:

_float_

resistance[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.resistance "Link to this definition")

Internal resistance \[Ohm\]

**Required:** True

Type:

_float_

voltage\_choice[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.voltage_choice "Link to this definition")

Battery voltage input option \[0/1\]

**Options:** 0=Model,1=Table

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

voltage\_matrix[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsCell.voltage_matrix "Link to this definition")

Table with depth-of-discharge % and Voltage as columns \[\[\[%, V\]\]\]

**Required:** Required if voltage\_choice=1

Type:

_sequence\[sequence\]_

## ParamsPack Group[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#paramspack-group "Link to this heading")

_class_ PySAM.BatteryStateful.BatteryStateful.ParamsPack[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsPack "Link to this definition")

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsPack.assign "Link to this definition")

Assign attributes from dictionary, overwriting but not removing values.

`ParamsPack_vals = { var: val, ...}`

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsPack.export "Link to this definition")

Export attributes into dictionary.

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsPack.replace "Link to this definition")

Replace attributes from dictionary, unassigning values not present in input `dict`.

`ParamsPack_vals = { var: val, ...}`

Cp[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsPack.Cp "Link to this definition")

Battery specific heat capacity \[J/KgK\]

**Required:** True

Type:

_float_

T\_room\_init[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsPack.T_room_init "Link to this definition")

Temperature of storage room \[C\]

**Required:** True

Type:

_float_

availabilty\_loss[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsPack.availabilty_loss "Link to this definition")

Battery availability losses at each timestep \[\[%\]\]

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_sequence_

cap\_vs\_temp[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsPack.cap_vs_temp "Link to this definition")

Table with Temperature and Capacity % as columns \[\[\[C,%\]\]\]

**Required:** Required if life\_model=0

Type:

_sequence\[sequence\]_

h[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsPack.h "Link to this definition")

Heat transfer between battery and environment \[W/m2K\]

**Required:** True

Type:

_float_

loss\_choice[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsPack.loss_choice "Link to this definition")

Loss power input option \[0/1\]

**Options:** 0=Monthly,1=TimeSeries

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

mass[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsPack.mass "Link to this definition")

Battery mass \[kg\]

**Required:** True

Type:

_float_

monthly\_charge\_loss[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsPack.monthly_charge_loss "Link to this definition")

Battery system losses when charging \[\[kW\]\]

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_sequence_

monthly\_discharge\_loss[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsPack.monthly_discharge_loss "Link to this definition")

Battery system losses when discharging \[\[kW\]\]

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_sequence_

monthly\_idle\_loss[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsPack.monthly_idle_loss "Link to this definition")

Battery system losses when idle \[\[kW\]\]

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_sequence_

nominal\_energy[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsPack.nominal_energy "Link to this definition")

Nominal installed energy \[kWh\]

**INOUT:** This variable is both an input and an output to the compute module.

**Required:** True

Type:

_float_

nominal\_voltage[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsPack.nominal_voltage "Link to this definition")

Nominal DC voltage \[V\]

**INOUT:** This variable is both an input and an output to the compute module.

**Required:** True

Type:

_float_

replacement\_capacity[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsPack.replacement_capacity "Link to this definition")

Capacity degradation at which to replace battery \[%\]

**Required:** Required if replacement\_option=1

Type:

_float_

replacement\_option[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsPack.replacement_option "Link to this definition")

none (0), by capacity (1), or schedule (2) \[0=none,1=capacity limit,2=yearly schedule\]

**Constraints:** INTEGER,MIN=0,MAX=2

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

Type:

Replacements

replacement\_schedule\_percent[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsPack.replacement_schedule_percent "Link to this definition")

Percentage of battery capacity to replace in each year \[\[%/year\]\]

**Options:** length <= analysis\_period

**Required:** Required if replacement\_option=2

Type:

_sequence_

schedule\_loss[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsPack.schedule_loss "Link to this definition")

Battery system losses at each timestep \[\[kW\]\]

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_sequence_

surface\_area[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.ParamsPack.surface_area "Link to this definition")

Battery surface area \[m^2\]

**Required:** True

Type:

_float_

## StatePack Group[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#statepack-group "Link to this heading")

_class_ PySAM.BatteryStateful.BatteryStateful.StatePack[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StatePack "Link to this definition")

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StatePack.assign "Link to this definition")

Assign attributes from dictionary, overwriting but not removing values.

`StatePack_vals = { var: val, ...}`

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StatePack.export "Link to this definition")

Export attributes into dictionary.

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StatePack.replace "Link to this definition")

Replace attributes from dictionary, unassigning values not present in input `dict`.

`StatePack_vals = { var: val, ...}`

I[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StatePack.I "Link to this definition")

Current \[A\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

I\_chargeable[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StatePack.I_chargeable "Link to this definition")

Estimated max chargeable current \[A\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

I\_dischargeable[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StatePack.I_dischargeable "Link to this definition")

Estimated max dischargeable current \[A\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

P[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StatePack.P "Link to this definition")

Power \[kW\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

P\_chargeable[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StatePack.P_chargeable "Link to this definition")

Estimated max chargeable power \[kW\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

P\_dischargeable[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StatePack.P_dischargeable "Link to this definition")

Estimated max dischargeable power \[kW\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

Q[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StatePack.Q "Link to this definition")

Capacity \[Ah\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

Q\_max[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StatePack.Q_max "Link to this definition")

Max Capacity \[Ah\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

SOC[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StatePack.SOC "Link to this definition")

State of Charge \[%\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

T\_batt[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StatePack.T_batt "Link to this definition")

Battery temperature averaged over time step \[C\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

T\_room[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StatePack.T_room "Link to this definition")

Room temperature \[C\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

V[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StatePack.V "Link to this definition")

Voltage \[V\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

heat\_dissipated[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StatePack.heat_dissipated "Link to this definition")

Heat dissipated due to flux \[kW\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

indices\_replaced[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StatePack.indices_replaced "Link to this definition")

Lifetime indices of replacement occurrences

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_sequence_

last\_idx[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StatePack.last_idx "Link to this definition")

Last index (lifetime)

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

loss\_kw[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StatePack.loss_kw "Link to this definition")

Ancillary power loss (kW DC for DC connected, AC for AC connected) \[kW\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

n\_replacements[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StatePack.n_replacements "Link to this definition")

Number of replacements at current year

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

## StateCell Group[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#statecell-group "Link to this heading")

_class_ PySAM.BatteryStateful.BatteryStateful.StateCell[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell "Link to this definition")

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.assign "Link to this definition")

Assign attributes from dictionary, overwriting but not removing values.

`StateCell_vals = { var: val, ...}`

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.export "Link to this definition")

Export attributes into dictionary.

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.replace "Link to this definition")

Replace attributes from dictionary, unassigning values not present in input `dict`.

`StateCell_vals = { var: val, ...}`

DOD\_max[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.DOD_max "Link to this definition")

Max DOD of battery for current day \[%\]

**Info:** Cycles for Life Model

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

DOD\_min[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.DOD_min "Link to this definition")

Min DOD of battery for current day \[%\]

**Info:** Cycles for Life Model

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

EFC[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.EFC "Link to this definition")

Total Equivalent Full Cycles \[1\]

**Info:** LMO/LTO Life Model

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

EFC\_dt[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.EFC_dt "Link to this definition")

Equivalent Full Cycles cumulated for current day \[1\]

**Info:** LMO/LTO Life Model

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

I\_loss[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.I_loss "Link to this definition")

Lifetime and thermal losses \[A\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

SOC\_prev[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.SOC_prev "Link to this definition")

State of Charge of last time step \[%\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

T\_batt\_prev[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.T_batt_prev "Link to this definition")

Battery temperature at end of last time step \[C\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

average\_range[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.average_range "Link to this definition")

Average cycle cycle\_range \[%\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

b1\_dt[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.b1_dt "Link to this definition")

b1 coefficient cumulated for current day \[day^-0.5\]

**Info:** NMC Life Model

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

b2\_dt[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.b2_dt "Link to this definition")

b2 coefficient cumulated for current day \[1/cycle\]

**Info:** NMC Life Model

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

b3\_dt[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.b3_dt "Link to this definition")

b3 coefficient cumulated for current day \[1\]

**Info:** NMC Life Model

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

c0\_dt[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.c0_dt "Link to this definition")

c0 coefficient cumulated for current day \[Ah\]

**Info:** NMC Life Model

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

c2\_dt[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.c2_dt "Link to this definition")

c2 coefficient cumulated for current day \[1/cycle\]

**Info:** NMC Life Model

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

cell\_current[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.cell_current "Link to this definition")

Cell current \[A\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

cell\_voltage[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.cell_voltage "Link to this definition")

Cell voltage \[V\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

chargeChange[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.chargeChange "Link to this definition")

Whether Charge mode changed since last step \[0/1\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

charge\_mode[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.charge_mode "Link to this definition")

Charge (0), Idle (1), Discharge (2) \[0/1/2\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

cum\_dt[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.cum_dt "Link to this definition")

Elapsed time for current day \[day\]

**Info:** Cycles for Life Model

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

cycle\_DOD[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.cycle_DOD "Link to this definition")

cycle\_DOD of last cycle \[%\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

cycle\_DOD\_max[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.cycle_DOD_max "Link to this definition")

Max DODs of cycles concluded in current day \[%\]

**Info:** Cycles for Life Model

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_sequence_

cycle\_counts[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.cycle_counts "Link to this definition")

Counts of cycles by DOD \[\[%, cycles\]\]

**Options:** If life\_model=0, counts all cycles in simulation; else, cycles per day

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_sequence\[sequence\]_

cycle\_range[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.cycle_range "Link to this definition")

Range of last cycle \[%\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

day\_age\_of\_battery[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.day_age_of_battery "Link to this definition")

Day age of battery \[day\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

dq\_relative\_cal[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.dq_relative_cal "Link to this definition")

Cumulative capacity change from calendar degradation \[%\]

**Info:** LMO/LTO Life Model

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

dq\_relative\_calendar\_old[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.dq_relative_calendar_old "Link to this definition")

Change in capacity of last time step \[%\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

dq\_relative\_cyc[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.dq_relative_cyc "Link to this definition")

Cumulative capacity change from cycling degradation \[%\]

**Info:** LMO/LTO Life Model

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

dq\_relative\_li1[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.dq_relative_li1 "Link to this definition")

Cumulative capacity change from time-dependent Li loss \[1\]

**Info:** NMC Life Model

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

dq\_relative\_li2[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.dq_relative_li2 "Link to this definition")

Cumulative capacity change from cycle-dependent Li loss \[1\]

**Info:** NMC Life Model

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

dq\_relative\_li3[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.dq_relative_li3 "Link to this definition")

Cumulative capacity change from BOL Li loss \[1\]

**Info:** NMC Life Model

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

dq\_relative\_neg[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.dq_relative_neg "Link to this definition")

Cumulative capacity change from negative electrode \[1\]

**Info:** NMC Life Model

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

n\_cycles[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.n_cycles "Link to this definition")

Number of cycles

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

percent\_unavailable[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.percent_unavailable "Link to this definition")

Percent of system that is down \[%\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

percent\_unavailable\_prev[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.percent_unavailable_prev "Link to this definition")

Percent of system that was down last step \[%\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

prev\_charge[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.prev_charge "Link to this definition")

Charge mode of last time step \[0/1/2\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

q0[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.q0 "Link to this definition")

Cell capacity at timestep \[Ah\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

q1\_0[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.q1_0 "Link to this definition")

Lead acid - Cell charge available \[Ah\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

q2[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.q2 "Link to this definition")

Lead acid - Cell capacity at 10-hr discharge rate \[Ah\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

q2\_0[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.q2_0 "Link to this definition")

Lead acid - Cell charge bound \[Ah\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

q\_relative[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.q_relative "Link to this definition")

Overall relative capacity due to lifetime effects \[%\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

q\_relative\_calendar[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.q_relative_calendar "Link to this definition")

Relative capacity due to calendar effects \[%\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

q\_relative\_cycle[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.q_relative_cycle "Link to this definition")

Relative capacity due to cycling effects \[%\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

q\_relative\_li[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.q_relative_li "Link to this definition")

Relative capacity due to loss of lithium inventory \[%\]

**Info:** NMC Life Model

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

q\_relative\_neg[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.q_relative_neg "Link to this definition")

Relative capacity due to loss of anode material \[%\]

**Info:** NMC Life Model

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

q\_relative\_thermal[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.q_relative_thermal "Link to this definition")

Relative capacity due to thermal effects \[%\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

qmax\_lifetime[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.qmax_lifetime "Link to this definition")

Maximum possible cell capacity \[Ah\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

qmax\_thermal[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.qmax_thermal "Link to this definition")

Maximum cell capacity adjusted for temperature effects \[Ah\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

qn[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.qn "Link to this definition")

Lead acid - Cell capacity at n-hr discharge rate \[Ah\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

rainflow\_Xlt[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.rainflow_Xlt "Link to this definition")

Rainflow cycle\_range of second to last half cycle \[%\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

rainflow\_Ylt[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.rainflow_Ylt "Link to this definition")

Rainflow cycle\_range of last half cycle \[%\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

rainflow\_jlt[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.rainflow_jlt "Link to this definition")

Rainflow number of turning points

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

rainflow\_peaks[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.rainflow_peaks "Link to this definition")

Rainflow peaks of cycle\_DOD \[\[%\]\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_sequence_

temp\_avg[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.temp_avg "Link to this definition")

Average temperature for current day \[K\]

**Info:** LMO/LTO Life Model

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

temp\_dt[](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#PySAM.BatteryStateful.BatteryStateful.StateCell.temp_dt "Link to this definition")

Temperature cumulated for current day \[K\]

**Info:** NMC Life Model

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_