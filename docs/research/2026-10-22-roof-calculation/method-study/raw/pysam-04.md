# Battery — NLR-PySAM 8.0.0 documentation

Detailed battery storage model

PySAM.Battery.default(_config_) → [Battery](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery "PySAM.Battery.Battery")[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.default "Link to this definition")

Load defaults for the configuration `config`. Available configurations are:

> *   _“CustomGenerationBatteryAllEquityPartnershipFlip”_
>     
> *   _“CustomGenerationBatteryCommercial”_
>     
> *   _“CustomGenerationBatteryHostDeveloper”_
>     
> *   _“CustomGenerationBatteryLeveragedPartnershipFlip”_
>     
> *   _“CustomGenerationBatteryMerchantPlant”_
>     
> *   _“CustomGenerationBatteryResidential”_
>     
> *   _“CustomGenerationBatterySaleLeaseback”_
>     
> *   _“CustomGenerationBatterySingleOwner”_
>     
> *   _“CustomGenerationBatteryThirdParty”_
>     
> *   _“CustomGenerationPVWattsWindFuelCellBatteryHybridHostDeveloper”_
>     
> *   _“CustomGenerationPVWattsWindFuelCellBatteryHybridSingleOwner”_
>     
> *   _“FuelCellCommercial”_
>     
> *   _“FuelCellSingleOwner”_
>     
> *   _“MEwaveBatterySingleOwner”_
>     
> *   _“PVWattsBatteryAllEquityPartnershipFlip”_
>     
> *   _“PVWattsBatteryCommercial”_
>     
> *   _“PVWattsBatteryHostDeveloper”_
>     
> *   _“PVWattsBatteryLeveragedPartnershipFlip”_
>     
> *   _“PVWattsBatteryMerchantPlant”_
>     
> *   _“PVWattsBatteryResidential”_
>     
> *   _“PVWattsBatterySaleLeaseback”_
>     
> *   _“PVWattsBatterySingleOwner”_
>     
> *   _“PVWattsBatteryThirdParty”_
>     
> *   _“PVWattsWindBatteryHybridHostDeveloper”_
>     
> *   _“PVWattsWindBatteryHybridSingleOwner”_
>     
> *   _“PVWattsWindFuelCellBatteryHybridHostDeveloper”_
>     
> *   _“PVWattsWindFuelCellBatteryHybridSingleOwner”_
>     
> *   _“PhotovoltaicWindBatteryHybridHostDeveloper”_
>     
> *   _“PhotovoltaicWindBatteryHybridSingleOwner”_
>     
> *   _“StandaloneBatteryAllEquityPartnershipFlip”_
>     
> *   _“StandaloneBatteryCommercial”_
>     
> *   _“StandaloneBatteryHostDeveloper”_
>     
> *   _“StandaloneBatteryLeveragedPartnershipFlip”_
>     
> *   _“StandaloneBatteryMerchantPlant”_
>     
> *   _“StandaloneBatteryResidential”_
>     
> *   _“StandaloneBatterySaleLeaseback”_
>     
> *   _“StandaloneBatterySingleOwner”_
>     
> *   _“StandaloneBatteryThirdParty”_
>     

Note

Some inputs do not have default values and may be assigned a value from the variable’s **Required** attribute. See variable attribute descriptions below.

PySAM.Battery.from\_existing(_data_, _optional config_) → [Battery](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery "PySAM.Battery.Battery")[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.from_existing "Link to this definition")

Share data with an existing PySAM class. If `optional config` is a valid configuration name, load the module’s defaults for that configuration.

PySAM.Battery.new() → [Battery](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery "PySAM.Battery.Battery")[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.new "Link to this definition")

PySAM.Battery.wrap(_ssc\_data\_t_) → [Battery](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery "PySAM.Battery.Battery")[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.wrap "Link to this definition")

Load data from a PySSC object.

Warning

Do not call PySSC.data\_free on the ssc\_data\_t provided to `wrap()`

Battery is a wrapper for the SSC compute module [cmod\_battery.cpp](https://github.com/natlabrockies/ssc/blob/develop/ssc/cmod_battery.cpp)

## Interdependent Variables[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#interdependent-variables "Link to this heading")

The variables listed below are interdependent with other variables. If you change the value of one of these variables, you may need to change values of other variables. The SAM user interface manages these interdependent variables, but in PySAM, it is up to you change the value of all interdependent variables so they are consistent. See [Interdependent Variables](https://nrel-pysam.readthedocs.io/en/main/interdependent-variables.html) for examples and details.

> *   LeadAcid\_q10\_computed
>     
> *   LeadAcid\_q20\_computed
>     
> *   LeadAcid\_qn\_computed
>     
> *   batt\_Qexp
>     
> *   batt\_Qfull
>     
> *   batt\_Qfull\_flow
>     
> *   batt\_Qnom
>     
> *   batt\_Vnom\_default
>     
> *   batt\_ac\_dc\_efficiency
>     
> *   batt\_ac\_or\_dc
>     
> *   batt\_chem
>     
> *   batt\_computed\_bank\_capacity
>     
> *   batt\_computed\_series
>     
> *   batt\_computed\_strings
>     
> *   batt\_current\_charge\_max
>     
> *   batt\_current\_choice
>     
> *   batt\_current\_discharge\_max
>     
> *   batt\_dc\_ac\_efficiency
>     
> *   batt\_dc\_dc\_efficiency
>     
> *   batt\_dispatch\_load\_forecast\_choice
>     
> *   batt\_load\_ac\_forecast
>     
> *   batt\_load\_ac\_forecast\_escalation
>     
> *   batt\_mass
>     
> *   batt\_power\_charge\_max\_kwac
>     
> *   batt\_power\_charge\_max\_kwdc
>     
> *   batt\_power\_discharge\_max\_kwac
>     
> *   batt\_power\_discharge\_max\_kwdc
>     
> *   batt\_room\_temperature\_celsius
>     
> *   batt\_surface\_area
>     
> *   dispatch\_manual\_discharge
>     
> *   dispatch\_manual\_gridcharge
>     
> *   dispatch\_manual\_percent\_discharge
>     
> *   dispatch\_manual\_percent\_gridcharge
>     
> *   grid\_curtailment
>     
> *   load\_escalation
>     

## Functions[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#functions "Link to this heading")

_class_ PySAM.Battery.Battery[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery "Link to this definition")

This class contains all the variable information for running a simulation. Variables are grouped together in the subclasses as properties. If property assignments are the wrong type, an error is thrown.

Reopt\_size\_standalone\_battery\_post()[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Reopt_size_standalone_battery_post "Link to this definition")

Given a PV system with Utilityrate5 parameters, get the optimal battery size. Maps SAM compute module inputs to those of the ReOpt API: Pvsamv1 model linked with Battery, Utilityrate5, with Cashloan optional.

For more information on which PySAM variables are used, see: [https://github.com/NatLabRockies/ssc/blob/develop/ssc/cmod\_battery\_eqns.h](https://github.com/NatLabRockies/ssc/blob/develop/ssc/cmod_battery_eqns.h)

For an example, see the ‘Examples’ readthedocs page.

Size\_battery()[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Size_battery "Link to this definition")

Helper function for battery\_model\_sizing. Modifies Battery model with new sizing. For BatteryStateful use size\_batterystateful. :param model: PySAM.Battery model :param float desired\_power: Desired battery power, kWAC if AC-connected, kWDC otherwise. :param float desired\_capacity: Desired battery capacity, kWhAC if AC-connected, kWhDC otherwise. :param float desired\_voltage: Desired battery voltage, V. :param bool,optional size\_by\_ac\_not\_dc: True sizes for power and capacity based on AC cpacities, False sizes for DC capacities. :param dict module\_dict: {capacity (float), surface\_area (float)} Battery module specs for scaling surface area.

> capacity: float
> 
> Capacity of a single battery module in kWhAC if AC-connected or kWhDC if DC-connected.
> 
> surface\_area: float
> 
> Surface area is of single battery module in m^2.

Returns:

Dictionary of of sizing parameters.

Return type:

dict

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.assign "Link to this definition")

Assign attributes from nested dictionary, except for Outputs

`nested_dict = { 'Simulation': { var: val, ...}, ...}`

execute(_int verbosity_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.execute "Link to this definition")

Execute simulation with verbosity level 0 (default) or 1

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.export "Link to this definition")

Export attributes into nested dictionary

get\_data\_ptr() → Pointer[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.get_data_ptr "Link to this definition")

Get ssc\_data\_t pointer

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.replace "Link to this definition")

Replace attributes from nested dictionary, except for Outputs. Unassigns all values in each Group then assigns from the input dict.

`nested_dict = { 'Simulation': { var: val, ...}, ...}`

unassign(_name_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.unassign "Link to this definition")

Unassign a value in any of the variable groups.

value(_name_, _optional value_) → None | float | dict | sequence | str[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.value "Link to this definition")

Get or set by name a value in any of the variable groups.

## Simulation Group[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#simulation-group "Link to this heading")

_class_ PySAM.Battery.Battery.Simulation[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Simulation "Link to this definition")

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Simulation.assign "Link to this definition")

Assign attributes from dictionary, overwriting but not removing values.

`Simulation_vals = { var: val, ...}`

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Simulation.export "Link to this definition")

Export attributes into dictionary.

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Simulation.replace "Link to this definition")

Replace attributes from dictionary, unassigning values not present in input `dict`.

`Simulation_vals = { var: val, ...}`

percent\_complete[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Simulation.percent_complete "Link to this definition")

Estimated simulation status \[%\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

timestep\_minutes[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Simulation.timestep_minutes "Link to this definition")

Simulation timestep \[minutes\]

**Info:** The number of minutes in each timestep

**Required:** Required if en\_standalone\_batt=1

Type:

_float_

## Lifetime Group[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#lifetime-group "Link to this heading")

_class_ PySAM.Battery.Battery.Lifetime[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Lifetime "Link to this definition")

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Lifetime.assign "Link to this definition")

Assign attributes from dictionary, overwriting but not removing values.

`Lifetime_vals = { var: val, ...}`

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Lifetime.export "Link to this definition")

Export attributes into dictionary.

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Lifetime.replace "Link to this definition")

Replace attributes from dictionary, unassigning values not present in input `dict`.

`Lifetime_vals = { var: val, ...}`

analysis\_period[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Lifetime.analysis_period "Link to this definition")

Lifetime analysis period \[years\]

**Info:** The number of years in the simulation

**Required:** Required if system\_use\_lifetime\_output=1

Type:

_float_

inflation\_rate[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Lifetime.inflation_rate "Link to this definition")

Inflation rate \[%\]

**Constraints:** MIN=-99

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

system\_use\_lifetime\_output[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Lifetime.system_use_lifetime_output "Link to this definition")

Lifetime simulation \[0/1\]

**Options:** 0=SingleYearRepeated,1=RunEveryYear

**Constraints:** BOOLEAN

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

## BatterySystem Group[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#batterysystem-group "Link to this heading")

_class_ PySAM.Battery.Battery.BatterySystem[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem "Link to this definition")

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.assign "Link to this definition")

Assign attributes from dictionary, overwriting but not removing values.

`BatterySystem_vals = { var: val, ...}`

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.export "Link to this definition")

Export attributes into dictionary.

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.replace "Link to this definition")

Replace attributes from dictionary, unassigning values not present in input `dict`.

`BatterySystem_vals = { var: val, ...}`

batt\_ac\_dc\_efficiency[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_ac_dc_efficiency "Link to this definition")

Inverter AC to battery DC efficiency

The value of the following variables depends on `batt_ac_dc_efficiency`:

> *   LeadAcid\_q10\_computed
>     
> *   LeadAcid\_q20\_computed
>     
> *   LeadAcid\_qn\_computed
>     
> *   batt\_Qexp
>     
> *   batt\_Qfull\_flow
>     
> *   batt\_Qnom
>     
> *   batt\_computed\_bank\_capacity
>     
> *   batt\_computed\_series
>     
> *   batt\_computed\_strings
>     
> *   batt\_current\_charge\_max
>     
> *   batt\_current\_discharge\_max
>     
> *   batt\_mass
>     
> *   batt\_power\_charge\_max\_kwac
>     
> *   batt\_power\_charge\_max\_kwdc
>     
> *   batt\_power\_discharge\_max\_kwac
>     
> *   batt\_power\_discharge\_max\_kwdc
>     
> *   batt\_surface\_area
>     

Type:

_float_

batt\_ac\_or\_dc[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_ac_or_dc "Link to this definition")

Battery interconnection (AC or DC)

**Options:** 0=DC\_Connected,1=AC\_Connected

The value of the following variables depends on `batt_ac_or_dc`:

> *   LeadAcid\_q10\_computed
>     
> *   LeadAcid\_q20\_computed
>     
> *   LeadAcid\_qn\_computed
>     
> *   batt\_Qexp
>     
> *   batt\_Qfull\_flow
>     
> *   batt\_Qnom
>     
> *   batt\_computed\_bank\_capacity
>     
> *   batt\_computed\_series
>     
> *   batt\_computed\_strings
>     
> *   batt\_current\_charge\_max
>     
> *   batt\_current\_discharge\_max
>     
> *   batt\_mass
>     
> *   batt\_power\_charge\_max\_kwac
>     
> *   batt\_power\_charge\_max\_kwdc
>     
> *   batt\_power\_discharge\_max\_kwac
>     
> *   batt\_power\_discharge\_max\_kwdc
>     
> *   batt\_surface\_area
>     

Type:

_float_

batt\_computed\_bank\_capacity[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_computed_bank_capacity "Link to this definition")

Battery computed bank capacity \[kWh\]

**INOUT:** This variable is both an input and an output to the compute module.

The value of the following variables depends on `batt_computed_bank_capacity`:

> *   batt\_Qexp
>     
> *   batt\_Qfull\_flow
>     
> *   batt\_Qnom
>     
> *   batt\_mass
>     
> *   batt\_surface\_area
>     

The value of `batt_computed_bank_capacity` depends on the following variables:

> *   batt\_Qfull
>     
> *   batt\_Vnom\_default
>     
> *   batt\_ac\_dc\_efficiency
>     
> *   batt\_ac\_or\_dc
>     
> *   batt\_chem
>     
> *   batt\_current\_choice
>     
> *   batt\_dc\_ac\_efficiency
>     
> *   batt\_dc\_dc\_efficiency
>     

Type:

_float_

batt\_computed\_series[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_computed_series "Link to this definition")

Battery number of cells in series

**INOUT:** This variable is both an input and an output to the compute module.

The value of `batt_computed_series` depends on the following variables:

> *   batt\_Qfull
>     
> *   batt\_Vnom\_default
>     
> *   batt\_ac\_dc\_efficiency
>     
> *   batt\_ac\_or\_dc
>     
> *   batt\_chem
>     
> *   batt\_current\_choice
>     
> *   batt\_dc\_ac\_efficiency
>     
> *   batt\_dc\_dc\_efficiency
>     

Type:

_float_

batt\_computed\_strings[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_computed_strings "Link to this definition")

Battery number of strings of cells

**INOUT:** This variable is both an input and an output to the compute module.

The value of the following variables depends on `batt_computed_strings`:

> *   LeadAcid\_q10\_computed
>     
> *   LeadAcid\_q20\_computed
>     
> *   LeadAcid\_qn\_computed
>     

The value of `batt_computed_strings` depends on the following variables:

> *   batt\_Qfull
>     
> *   batt\_Vnom\_default
>     
> *   batt\_ac\_dc\_efficiency
>     
> *   batt\_ac\_or\_dc
>     
> *   batt\_chem
>     
> *   batt\_current\_choice
>     
> *   batt\_dc\_ac\_efficiency
>     
> *   batt\_dc\_dc\_efficiency
>     

Type:

_float_

batt\_current\_charge\_max[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_current_charge_max "Link to this definition")

Battery maximum charge current \[A\]

**INOUT:** This variable is both an input and an output to the compute module.

The value of `batt_current_charge_max` depends on the following variables:

> *   batt\_Qfull
>     
> *   batt\_Vnom\_default
>     
> *   batt\_ac\_dc\_efficiency
>     
> *   batt\_ac\_or\_dc
>     
> *   batt\_chem
>     
> *   batt\_current\_choice
>     
> *   batt\_dc\_ac\_efficiency
>     
> *   batt\_dc\_dc\_efficiency
>     

Type:

_float_

batt\_current\_choice[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_current_choice "Link to this definition")

Limit cells by current or power

The value of the following variables depends on `batt_current_choice`:

> *   LeadAcid\_q10\_computed
>     
> *   LeadAcid\_q20\_computed
>     
> *   LeadAcid\_qn\_computed
>     
> *   batt\_Qexp
>     
> *   batt\_Qfull\_flow
>     
> *   batt\_Qnom
>     
> *   batt\_computed\_bank\_capacity
>     
> *   batt\_computed\_series
>     
> *   batt\_computed\_strings
>     
> *   batt\_current\_charge\_max
>     
> *   batt\_current\_discharge\_max
>     
> *   batt\_mass
>     
> *   batt\_power\_charge\_max\_kwac
>     
> *   batt\_power\_charge\_max\_kwdc
>     
> *   batt\_power\_discharge\_max\_kwac
>     
> *   batt\_power\_discharge\_max\_kwdc
>     
> *   batt\_surface\_area
>     

Type:

_float_

batt\_current\_discharge\_max[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_current_discharge_max "Link to this definition")

Battery maximum discharge current \[A\]

**INOUT:** This variable is both an input and an output to the compute module.

The value of `batt_current_discharge_max` depends on the following variables:

> *   batt\_Qfull
>     
> *   batt\_Vnom\_default
>     
> *   batt\_ac\_dc\_efficiency
>     
> *   batt\_ac\_or\_dc
>     
> *   batt\_chem
>     
> *   batt\_current\_choice
>     
> *   batt\_dc\_ac\_efficiency
>     
> *   batt\_dc\_dc\_efficiency
>     

Type:

_float_

batt\_dc\_ac\_efficiency[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_dc_ac_efficiency "Link to this definition")

Battery DC to AC efficiency

The value of the following variables depends on `batt_dc_ac_efficiency`:

> *   LeadAcid\_q10\_computed
>     
> *   LeadAcid\_q20\_computed
>     
> *   LeadAcid\_qn\_computed
>     
> *   batt\_Qexp
>     
> *   batt\_Qfull\_flow
>     
> *   batt\_Qnom
>     
> *   batt\_computed\_bank\_capacity
>     
> *   batt\_computed\_series
>     
> *   batt\_computed\_strings
>     
> *   batt\_current\_charge\_max
>     
> *   batt\_current\_discharge\_max
>     
> *   batt\_mass
>     
> *   batt\_power\_charge\_max\_kwac
>     
> *   batt\_power\_charge\_max\_kwdc
>     
> *   batt\_power\_discharge\_max\_kwac
>     
> *   batt\_power\_discharge\_max\_kwdc
>     
> *   batt\_surface\_area
>     

Type:

_float_

batt\_dc\_dc\_efficiency[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_dc_dc_efficiency "Link to this definition")

System DC to battery DC efficiency

The value of the following variables depends on `batt_dc_dc_efficiency`:

> *   LeadAcid\_q10\_computed
>     
> *   LeadAcid\_q20\_computed
>     
> *   LeadAcid\_qn\_computed
>     
> *   batt\_Qexp
>     
> *   batt\_Qfull\_flow
>     
> *   batt\_Qnom
>     
> *   batt\_computed\_bank\_capacity
>     
> *   batt\_computed\_series
>     
> *   batt\_computed\_strings
>     
> *   batt\_current\_charge\_max
>     
> *   batt\_current\_discharge\_max
>     
> *   batt\_mass
>     
> *   batt\_power\_charge\_max\_kwac
>     
> *   batt\_power\_charge\_max\_kwdc
>     
> *   batt\_power\_discharge\_max\_kwac
>     
> *   batt\_power\_discharge\_max\_kwdc
>     
> *   batt\_surface\_area
>     

Type:

_float_

batt\_inverter\_efficiency\_cutoff[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_inverter_efficiency_cutoff "Link to this definition")

Inverter efficiency at which to cut battery charge or discharge off \[%\]

Type:

_float_

batt\_loss\_choice[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_loss_choice "Link to this definition")

Loss power input option \[0/1\]

**Options:** 0=Monthly,1=TimeSeries

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

batt\_losses[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_losses "Link to this definition")

Battery system losses at each timestep (kW DC for DC connected, AC for AC connected) \[kW\]

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_sequence_

batt\_losses\_charging[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_losses_charging "Link to this definition")

Battery system losses when charging (kW DC for DC connected, AC for AC connected) \[kW\]

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_sequence_

batt\_losses\_discharging[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_losses_discharging "Link to this definition")

Battery system losses when discharging (kW DC for DC connected, AC for AC connected) \[kW\]

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_sequence_

batt\_losses\_idle[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_losses_idle "Link to this definition")

Battery system losses when idle (kW DC for DC connected, AC for AC connected) \[kW\]

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_sequence_

batt\_mass[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_mass "Link to this definition")

Battery mass \[kg\]

The value of `batt_mass` depends on the following variables:

> *   batt\_Qfull
>     
> *   batt\_Vnom\_default
>     
> *   batt\_ac\_dc\_efficiency
>     
> *   batt\_ac\_or\_dc
>     
> *   batt\_chem
>     
> *   batt\_computed\_bank\_capacity
>     
> *   batt\_current\_choice
>     
> *   batt\_dc\_ac\_efficiency
>     
> *   batt\_dc\_dc\_efficiency
>     

Type:

_float_

batt\_meter\_position[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_meter_position "Link to this definition")

Position of battery relative to electric meter

**Options:** 0=BehindTheMeter,1=FrontOfMeter

Type:

_float_

batt\_power\_charge\_max\_kwac[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_power_charge_max_kwac "Link to this definition")

Battery maximum charge power (AC) \[kWac\]

**INOUT:** This variable is both an input and an output to the compute module.

The value of `batt_power_charge_max_kwac` depends on the following variables:

> *   batt\_Qfull
>     
> *   batt\_Vnom\_default
>     
> *   batt\_ac\_dc\_efficiency
>     
> *   batt\_ac\_or\_dc
>     
> *   batt\_chem
>     
> *   batt\_current\_choice
>     
> *   batt\_dc\_ac\_efficiency
>     
> *   batt\_dc\_dc\_efficiency
>     

Type:

_float_

batt\_power\_charge\_max\_kwdc[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_power_charge_max_kwdc "Link to this definition")

Battery maximum charge power (DC) \[kWdc\]

**INOUT:** This variable is both an input and an output to the compute module.

The value of `batt_power_charge_max_kwdc` depends on the following variables:

> *   batt\_Qfull
>     
> *   batt\_Vnom\_default
>     
> *   batt\_ac\_dc\_efficiency
>     
> *   batt\_ac\_or\_dc
>     
> *   batt\_chem
>     
> *   batt\_current\_choice
>     
> *   batt\_dc\_ac\_efficiency
>     
> *   batt\_dc\_dc\_efficiency
>     

Type:

_float_

batt\_power\_discharge\_max\_kwac[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_power_discharge_max_kwac "Link to this definition")

Battery maximum discharge power (AC) \[kWac\]

**INOUT:** This variable is both an input and an output to the compute module.

The value of `batt_power_discharge_max_kwac` depends on the following variables:

> *   batt\_Qfull
>     
> *   batt\_Vnom\_default
>     
> *   batt\_ac\_dc\_efficiency
>     
> *   batt\_ac\_or\_dc
>     
> *   batt\_chem
>     
> *   batt\_current\_choice
>     
> *   batt\_dc\_ac\_efficiency
>     
> *   batt\_dc\_dc\_efficiency
>     

Type:

_float_

batt\_power\_discharge\_max\_kwdc[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_power_discharge_max_kwdc "Link to this definition")

Battery maximum discharge power (DC) \[kWdc\]

**INOUT:** This variable is both an input and an output to the compute module.

The value of `batt_power_discharge_max_kwdc` depends on the following variables:

> *   batt\_Qfull
>     
> *   batt\_Vnom\_default
>     
> *   batt\_ac\_dc\_efficiency
>     
> *   batt\_ac\_or\_dc
>     
> *   batt\_chem
>     
> *   batt\_current\_choice
>     
> *   batt\_dc\_ac\_efficiency
>     
> *   batt\_dc\_dc\_efficiency
>     

Type:

_float_

batt\_replacement\_capacity[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_replacement_capacity "Link to this definition")

Capacity degradation at which to replace battery \[%\]

Type:

_float_

batt\_replacement\_option[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_replacement_option "Link to this definition")

Enable battery replacement? \[0=none,1=capacity based,2=user schedule\]

**Constraints:** INTEGER,MIN=0,MAX=2

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

batt\_replacement\_schedule\_percent[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_replacement_schedule_percent "Link to this definition")

Percentage of battery capacity to replace in each year \[%\]

**Options:** length <= analysis\_period

**Required:** Required if batt\_replacement\_option=2

Type:

_sequence_

batt\_surface\_area[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.batt_surface_area "Link to this definition")

Battery surface area \[m^2\]

The value of `batt_surface_area` depends on the following variables:

> *   batt\_Qfull
>     
> *   batt\_Vnom\_default
>     
> *   batt\_ac\_dc\_efficiency
>     
> *   batt\_ac\_or\_dc
>     
> *   batt\_chem
>     
> *   batt\_computed\_bank\_capacity
>     
> *   batt\_current\_choice
>     
> *   batt\_dc\_ac\_efficiency
>     
> *   batt\_dc\_dc\_efficiency
>     

Type:

_float_

en\_batt[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.en_batt "Link to this definition")

Enable battery storage model \[0/1\]

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

en\_standalone\_batt[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.en_standalone_batt "Link to this definition")

Enable standalone battery storage model \[0/1\]

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

en\_wave\_batt[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.en_wave_batt "Link to this definition")

Enable wave battery storage model \[0/1\]

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

om\_replacement\_cost1[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatterySystem.om_replacement_cost1 "Link to this definition")

Cost to replace battery per kWh \[$/kWh\]

Type:

_sequence_

## SystemOutput Group[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#systemoutput-group "Link to this heading")

_class_ PySAM.Battery.Battery.SystemOutput[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.SystemOutput "Link to this definition")

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.SystemOutput.assign "Link to this definition")

Assign attributes from dictionary, overwriting but not removing values.

`SystemOutput_vals = { var: val, ...}`

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.SystemOutput.export "Link to this definition")

Export attributes into dictionary.

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.SystemOutput.replace "Link to this definition")

Replace attributes from dictionary, unassigning values not present in input `dict`.

`SystemOutput_vals = { var: val, ...}`

annual\_energy[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.SystemOutput.annual_energy "Link to this definition")

Annual AC energy in Year 1 \[kWh\]

**INOUT:** This variable is both an input and an output to the compute module.

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

capacity\_factor[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.SystemOutput.capacity_factor "Link to this definition")

Capacity factor \[%\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_float_

energy\_hourly\_kW[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.SystemOutput.energy_hourly_kW "Link to this definition")

Power output of array \[kW\]

**Info:** Lifetime system generation

**INOUT:** This variable is both an input and an output to the compute module.

**Required:** Required if en\_wave\_batt=1

Type:

_sequence_

gen[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.SystemOutput.gen "Link to this definition")

System power generated \[kW\]

**INOUT:** This variable is both an input and an output to the compute module.

Type:

_sequence_

## Load Group[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#load-group "Link to this heading")

_class_ PySAM.Battery.Battery.Load[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Load "Link to this definition")

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Load.assign "Link to this definition")

Assign attributes from dictionary, overwriting but not removing values.

`Load_vals = { var: val, ...}`

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Load.export "Link to this definition")

Export attributes into dictionary.

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Load.replace "Link to this definition")

Replace attributes from dictionary, unassigning values not present in input `dict`.

`Load_vals = { var: val, ...}`

crit\_load[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Load.crit_load "Link to this definition")

Critical electricity load (year 1) \[kW\]

Type:

_sequence_

crit\_load\_escalation[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Load.crit_load_escalation "Link to this definition")

Annual critical load escalation \[%/year\]

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_sequence_

grid\_outage[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Load.grid_outage "Link to this definition")

Grid outage in this time step \[0/1\]

**Options:** 0=GridAvailable,1=GridUnavailable,Length=load

Type:

_sequence_

load[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Load.load "Link to this definition")

Electricity load (year 1) \[kW\]

The value of the following variables depends on `load`:

> *   batt\_room\_temperature\_celsius
>     

Type:

_sequence_

load\_escalation[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Load.load_escalation "Link to this definition")

Annual load escalation \[%/year\]

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

The value of the following variables depends on `load_escalation`:

> *   batt\_load\_ac\_forecast\_escalation
>     

Type:

_sequence_

run\_resiliency\_calcs[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Load.run_resiliency_calcs "Link to this definition")

Enable resilence calculations for every timestep \[0/1\]

**Options:** 0=DisableCalcs,1=EnableCalcs

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

## BatteryCell Group[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#batterycell-group "Link to this heading")

_class_ PySAM.Battery.Battery.BatteryCell[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell "Link to this definition")

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.assign "Link to this definition")

Assign attributes from dictionary, overwriting but not removing values.

`BatteryCell_vals = { var: val, ...}`

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.export "Link to this definition")

Export attributes into dictionary.

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.replace "Link to this definition")

Replace attributes from dictionary, unassigning values not present in input `dict`.

`BatteryCell_vals = { var: val, ...}`

LeadAcid\_q10\_computed[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.LeadAcid_q10_computed "Link to this definition")

Capacity at 10-hour discharge rate \[Ah\]

The value of `LeadAcid_q10_computed` depends on the following variables:

> *   batt\_Qfull
>     
> *   batt\_Vnom\_default
>     
> *   batt\_ac\_dc\_efficiency
>     
> *   batt\_ac\_or\_dc
>     
> *   batt\_chem
>     
> *   batt\_computed\_strings
>     
> *   batt\_current\_choice
>     
> *   batt\_dc\_ac\_efficiency
>     
> *   batt\_dc\_dc\_efficiency
>     

Type:

_float_

LeadAcid\_q20\_computed[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.LeadAcid_q20_computed "Link to this definition")

Capacity at 20-hour discharge rate \[Ah\]

The value of `LeadAcid_q20_computed` depends on the following variables:

> *   batt\_Qfull
>     
> *   batt\_Vnom\_default
>     
> *   batt\_ac\_dc\_efficiency
>     
> *   batt\_ac\_or\_dc
>     
> *   batt\_chem
>     
> *   batt\_computed\_strings
>     
> *   batt\_current\_choice
>     
> *   batt\_dc\_ac\_efficiency
>     
> *   batt\_dc\_dc\_efficiency
>     

Type:

_float_

LeadAcid\_qn\_computed[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.LeadAcid_qn_computed "Link to this definition")

Capacity at discharge rate for n-hour rate \[Ah\]

The value of `LeadAcid_qn_computed` depends on the following variables:

> *   batt\_Qfull
>     
> *   batt\_Vnom\_default
>     
> *   batt\_ac\_dc\_efficiency
>     
> *   batt\_ac\_or\_dc
>     
> *   batt\_chem
>     
> *   batt\_computed\_strings
>     
> *   batt\_current\_choice
>     
> *   batt\_dc\_ac\_efficiency
>     
> *   batt\_dc\_dc\_efficiency
>     

Type:

_float_

LeadAcid\_tn[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.LeadAcid_tn "Link to this definition")

Time to discharge \[h\]

Type:

_float_

batt\_C\_rate[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_C_rate "Link to this definition")

Rate at which voltage vs. capacity curve input

Type:

_float_

batt\_Cp[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_Cp "Link to this definition")

Battery specific heat capacity \[J/KgK\]

Type:

_float_

batt\_Qexp[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_Qexp "Link to this definition")

Cell capacity at end of exponential zone \[Ah\]

The value of `batt_Qexp` depends on the following variables:

> *   batt\_Qfull
>     
> *   batt\_Vnom\_default
>     
> *   batt\_ac\_dc\_efficiency
>     
> *   batt\_ac\_or\_dc
>     
> *   batt\_chem
>     
> *   batt\_computed\_bank\_capacity
>     
> *   batt\_current\_choice
>     
> *   batt\_dc\_ac\_efficiency
>     
> *   batt\_dc\_dc\_efficiency
>     

Type:

_float_

batt\_Qfull[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_Qfull "Link to this definition")

Fully charged cell capacity \[Ah\]

The value of the following variables depends on `batt_Qfull`:

> *   LeadAcid\_q10\_computed
>     
> *   LeadAcid\_q20\_computed
>     
> *   LeadAcid\_qn\_computed
>     
> *   batt\_Qexp
>     
> *   batt\_Qfull\_flow
>     
> *   batt\_Qnom
>     
> *   batt\_computed\_bank\_capacity
>     
> *   batt\_computed\_series
>     
> *   batt\_computed\_strings
>     
> *   batt\_current\_charge\_max
>     
> *   batt\_current\_discharge\_max
>     
> *   batt\_mass
>     
> *   batt\_power\_charge\_max\_kwac
>     
> *   batt\_power\_charge\_max\_kwdc
>     
> *   batt\_power\_discharge\_max\_kwac
>     
> *   batt\_power\_discharge\_max\_kwdc
>     
> *   batt\_surface\_area
>     

Type:

_float_

batt\_Qfull\_flow[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_Qfull_flow "Link to this definition")

Fully charged flow battery capacity \[Ah\]

The value of `batt_Qfull_flow` depends on the following variables:

> *   batt\_Qfull
>     
> *   batt\_Vnom\_default
>     
> *   batt\_ac\_dc\_efficiency
>     
> *   batt\_ac\_or\_dc
>     
> *   batt\_chem
>     
> *   batt\_computed\_bank\_capacity
>     
> *   batt\_current\_choice
>     
> *   batt\_dc\_ac\_efficiency
>     
> *   batt\_dc\_dc\_efficiency
>     

Type:

_float_

batt\_Qnom[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_Qnom "Link to this definition")

Cell capacity at end of nominal zone \[Ah\]

The value of `batt_Qnom` depends on the following variables:

> *   batt\_Qfull
>     
> *   batt\_Vnom\_default
>     
> *   batt\_ac\_dc\_efficiency
>     
> *   batt\_ac\_or\_dc
>     
> *   batt\_chem
>     
> *   batt\_computed\_bank\_capacity
>     
> *   batt\_current\_choice
>     
> *   batt\_dc\_ac\_efficiency
>     
> *   batt\_dc\_dc\_efficiency
>     

Type:

_float_

batt\_Vcut[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_Vcut "Link to this definition")

Cutoff voltage for battery rated capacity \[V\]

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

batt\_Vexp[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_Vexp "Link to this definition")

Cell voltage at end of exponential zone \[V\]

Type:

_float_

batt\_Vfull[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_Vfull "Link to this definition")

Fully charged cell voltage \[V\]

Type:

_float_

batt\_Vnom[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_Vnom "Link to this definition")

Cell voltage at end of nominal zone \[V\]

Type:

_float_

batt\_Vnom\_default[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_Vnom_default "Link to this definition")

Default nominal cell voltage \[V\]

The value of the following variables depends on `batt_Vnom_default`:

> *   LeadAcid\_q10\_computed
>     
> *   LeadAcid\_q20\_computed
>     
> *   LeadAcid\_qn\_computed
>     
> *   batt\_Qexp
>     
> *   batt\_Qfull\_flow
>     
> *   batt\_Qnom
>     
> *   batt\_computed\_bank\_capacity
>     
> *   batt\_computed\_series
>     
> *   batt\_computed\_strings
>     
> *   batt\_current\_charge\_max
>     
> *   batt\_current\_discharge\_max
>     
> *   batt\_mass
>     
> *   batt\_power\_charge\_max\_kwac
>     
> *   batt\_power\_charge\_max\_kwdc
>     
> *   batt\_power\_discharge\_max\_kwac
>     
> *   batt\_power\_discharge\_max\_kwdc
>     
> *   batt\_surface\_area
>     

Type:

_float_

batt\_calendar\_a[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_calendar_a "Link to this definition")

Calendar life model coefficient \[1/sqrt(day)\]

**Required:** Required if en\_batt=1&batt\_life\_model=0&batt\_calendar\_choice=1

Type:

_float_

batt\_calendar\_b[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_calendar_b "Link to this definition")

Calendar life model coefficient \[K\]

**Required:** Required if en\_batt=1&batt\_life\_model=0&batt\_calendar\_choice=1

Type:

_float_

batt\_calendar\_c[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_calendar_c "Link to this definition")

Calendar life model coefficient \[K\]

**Required:** Required if en\_batt=1&batt\_life\_model=0&batt\_calendar\_choice=1

Type:

_float_

batt\_calendar\_choice[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_calendar_choice "Link to this definition")

Calendar life degradation input option \[0/1/2\]

**Options:** 0=NoCalendarDegradation,1=LithiomIonModel,2=InputLossTable

**Required:** Required if en\_batt=1&batt\_life\_model=0

Type:

_float_

batt\_calendar\_lifetime\_matrix[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_calendar_lifetime_matrix "Link to this definition")

Days vs capacity

**Required:** Required if en\_batt=1&batt\_life\_model=0&batt\_calendar\_choice=2

Type:

_sequence\[sequence\]_

batt\_calendar\_q0[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_calendar_q0 "Link to this definition")

Calendar life model initial capacity cofficient

**Required:** Required if en\_batt=1&batt\_life\_model=0&batt\_calendar\_choice=1

Type:

_float_

batt\_chem[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_chem "Link to this definition")

Battery chemistry

**Options:** 0=LeadAcid,1=LiIon

The value of the following variables depends on `batt_chem`:

> *   LeadAcid\_q10\_computed
>     
> *   LeadAcid\_q20\_computed
>     
> *   LeadAcid\_qn\_computed
>     
> *   batt\_Qexp
>     
> *   batt\_Qfull\_flow
>     
> *   batt\_Qnom
>     
> *   batt\_computed\_bank\_capacity
>     
> *   batt\_computed\_series
>     
> *   batt\_computed\_strings
>     
> *   batt\_current\_charge\_max
>     
> *   batt\_current\_discharge\_max
>     
> *   batt\_mass
>     
> *   batt\_power\_charge\_max\_kwac
>     
> *   batt\_power\_charge\_max\_kwdc
>     
> *   batt\_power\_discharge\_max\_kwac
>     
> *   batt\_power\_discharge\_max\_kwdc
>     
> *   batt\_surface\_area
>     

Type:

_float_

batt\_h\_to\_ambient[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_h_to_ambient "Link to this definition")

Heat transfer between battery and environment \[W/m2K\]

Type:

_float_

batt\_initial\_SOC[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_initial_SOC "Link to this definition")

Initial state-of-charge \[%\]

Type:

_float_

batt\_life\_model[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_life_model "Link to this definition")

Battery life model specifier \[0/1/2\]

**Options:** 0=calendar/cycle,1=NMC,2=LMO/LTO

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

batt\_lifetime\_matrix[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_lifetime_matrix "Link to this definition")

Cycles vs capacity at different depths-of-discharge

**Required:** Required if en\_batt=1&batt\_life\_model=0

Type:

_sequence\[sequence\]_

batt\_maximum\_SOC[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_maximum_SOC "Link to this definition")

Maximum allowed state-of-charge \[%\]

Type:

_float_

batt\_minimum\_SOC[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_minimum_SOC "Link to this definition")

Minimum allowed state-of-charge during nominal operation \[%\]

Type:

_float_

batt\_minimum\_modetime[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_minimum_modetime "Link to this definition")

Minimum time at charge state \[min\]

Type:

_float_

batt\_minimum\_outage\_SOC[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_minimum_outage_SOC "Link to this definition")

Minimum allowed state-of-charge during an outage \[%\]

Type:

_float_

batt\_resistance[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_resistance "Link to this definition")

Internal resistance \[Ohm\]

Type:

_float_

batt\_room\_temperature\_celsius[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_room_temperature_celsius "Link to this definition")

Temperature of storage room \[C\]

**Options:** length=1 for fixed, # of weatherfile records otherwise

The value of `batt_room_temperature_celsius` depends on the following variables:

> *   grid\_curtailment
>     

Type:

_sequence_

batt\_voltage\_choice[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_voltage_choice "Link to this definition")

Battery voltage input option \[0/1\]

**Options:** 0=UseVoltageModel,1=InputVoltageTable

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

batt\_voltage\_matrix[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.batt_voltage_matrix "Link to this definition")

Battery voltage vs. depth-of-discharge

Type:

_sequence\[sequence\]_

cap\_vs\_temp[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryCell.cap_vs_temp "Link to this definition")

Effective capacity as function of temperature \[C,%\]

Type:

_sequence\[sequence\]_

## Inverter Group[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#inverter-group "Link to this heading")

_class_ PySAM.Battery.Battery.Inverter[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Inverter "Link to this definition")

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Inverter.assign "Link to this definition")

Assign attributes from dictionary, overwriting but not removing values.

`Inverter_vals = { var: val, ...}`

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Inverter.export "Link to this definition")

Export attributes into dictionary.

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Inverter.replace "Link to this definition")

Replace attributes from dictionary, unassigning values not present in input `dict`.

`Inverter_vals = { var: val, ...}`

inv\_cec\_cg\_eff\_cec[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Inverter.inv_cec_cg_eff_cec "Link to this definition")

Inverter Coefficient Generator CEC Efficiency \[%\]

The value of the following variables depends on `inv_cec_cg_eff_cec`:

> *   LeadAcid\_q10\_computed
>     
> *   LeadAcid\_q20\_computed
>     
> *   LeadAcid\_qn\_computed
>     
> *   batt\_Qexp
>     
> *   batt\_Qfull\_flow
>     
> *   batt\_Qnom
>     
> *   batt\_computed\_bank\_capacity
>     
> *   batt\_computed\_series
>     
> *   batt\_computed\_strings
>     
> *   batt\_current\_charge\_max
>     
> *   batt\_current\_discharge\_max
>     
> *   batt\_mass
>     
> *   batt\_power\_charge\_max\_kwac
>     
> *   batt\_power\_charge\_max\_kwdc
>     
> *   batt\_power\_discharge\_max\_kwac
>     
> *   batt\_power\_discharge\_max\_kwdc
>     
> *   batt\_surface\_area
>     

Type:

_float_

inv\_cec\_cg\_paco[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Inverter.inv_cec_cg_paco "Link to this definition")

Inverter Coefficient Generator Max AC Power \[Wac\]

Type:

_float_

inv\_ds\_eff[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Inverter.inv_ds_eff "Link to this definition")

Inverter Datasheet Efficiency \[%\]

The value of the following variables depends on `inv_ds_eff`:

> *   LeadAcid\_q10\_computed
>     
> *   LeadAcid\_q20\_computed
>     
> *   LeadAcid\_qn\_computed
>     
> *   batt\_Qexp
>     
> *   batt\_Qfull\_flow
>     
> *   batt\_Qnom
>     
> *   batt\_computed\_bank\_capacity
>     
> *   batt\_computed\_series
>     
> *   batt\_computed\_strings
>     
> *   batt\_current\_charge\_max
>     
> *   batt\_current\_discharge\_max
>     
> *   batt\_mass
>     
> *   batt\_power\_charge\_max\_kwac
>     
> *   batt\_power\_charge\_max\_kwdc
>     
> *   batt\_power\_discharge\_max\_kwac
>     
> *   batt\_power\_discharge\_max\_kwdc
>     
> *   batt\_surface\_area
>     

Type:

_float_

inv\_ds\_paco[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Inverter.inv_ds_paco "Link to this definition")

Inverter Datasheet Maximum AC Power \[Wac\]

Type:

_float_

inv\_pd\_eff[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Inverter.inv_pd_eff "Link to this definition")

Inverter Partload Efficiency \[%\]

The value of the following variables depends on `inv_pd_eff`:

> *   LeadAcid\_q10\_computed
>     
> *   LeadAcid\_q20\_computed
>     
> *   LeadAcid\_qn\_computed
>     
> *   batt\_Qexp
>     
> *   batt\_Qfull\_flow
>     
> *   batt\_Qnom
>     
> *   batt\_computed\_bank\_capacity
>     
> *   batt\_computed\_series
>     
> *   batt\_computed\_strings
>     
> *   batt\_current\_charge\_max
>     
> *   batt\_current\_discharge\_max
>     
> *   batt\_mass
>     
> *   batt\_power\_charge\_max\_kwac
>     
> *   batt\_power\_charge\_max\_kwdc
>     
> *   batt\_power\_discharge\_max\_kwac
>     
> *   batt\_power\_discharge\_max\_kwdc
>     
> *   batt\_surface\_area
>     

Type:

_float_

inv\_pd\_paco[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Inverter.inv_pd_paco "Link to this definition")

Inverter Partload Maximum AC Power \[Wac\]

Type:

_float_

inv\_snl\_eff\_cec[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Inverter.inv_snl_eff_cec "Link to this definition")

Inverter Sandia CEC Efficiency \[%\]

The value of the following variables depends on `inv_snl_eff_cec`:

> *   LeadAcid\_q10\_computed
>     
> *   LeadAcid\_q20\_computed
>     
> *   LeadAcid\_qn\_computed
>     
> *   batt\_Qexp
>     
> *   batt\_Qfull\_flow
>     
> *   batt\_Qnom
>     
> *   batt\_computed\_bank\_capacity
>     
> *   batt\_computed\_series
>     
> *   batt\_computed\_strings
>     
> *   batt\_current\_charge\_max
>     
> *   batt\_current\_discharge\_max
>     
> *   batt\_mass
>     
> *   batt\_power\_charge\_max\_kwac
>     
> *   batt\_power\_charge\_max\_kwdc
>     
> *   batt\_power\_discharge\_max\_kwac
>     
> *   batt\_power\_discharge\_max\_kwdc
>     
> *   batt\_surface\_area
>     

Type:

_float_

inv\_snl\_paco[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Inverter.inv_snl_paco "Link to this definition")

Inverter Sandia Maximum AC Power \[Wac\]

Type:

_float_

inverter\_count[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Inverter.inverter_count "Link to this definition")

Number of inverters

Type:

_float_

inverter\_model[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Inverter.inverter_model "Link to this definition")

Inverter model specifier

**Options:** 0=cec,1=datasheet,2=partload,3=coefficientgenerator,4=generic

**Constraints:** INTEGER,MIN=0,MAX=4

**Required:** False. Automatically set to 4 if not assigned explicitly or loaded from defaults.

The value of the following variables depends on `inverter_model`:

> *   LeadAcid\_q10\_computed
>     
> *   LeadAcid\_q20\_computed
>     
> *   LeadAcid\_qn\_computed
>     
> *   batt\_Qexp
>     
> *   batt\_Qfull\_flow
>     
> *   batt\_Qnom
>     
> *   batt\_computed\_bank\_capacity
>     
> *   batt\_computed\_series
>     
> *   batt\_computed\_strings
>     
> *   batt\_current\_charge\_max
>     
> *   batt\_current\_discharge\_max
>     
> *   batt\_mass
>     
> *   batt\_power\_charge\_max\_kwac
>     
> *   batt\_power\_charge\_max\_kwdc
>     
> *   batt\_power\_discharge\_max\_kwac
>     
> *   batt\_power\_discharge\_max\_kwdc
>     
> *   batt\_surface\_area
>     

Type:

_float_

## Losses Group[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#losses-group "Link to this heading")

_class_ PySAM.Battery.Battery.Losses[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Losses "Link to this definition")

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Losses.assign "Link to this definition")

Assign attributes from dictionary, overwriting but not removing values.

`Losses_vals = { var: val, ...}`

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Losses.export "Link to this definition")

Export attributes into dictionary.

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Losses.replace "Link to this definition")

Replace attributes from dictionary, unassigning values not present in input `dict`.

`Losses_vals = { var: val, ...}`

dcoptimizer\_loss[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Losses.dcoptimizer_loss "Link to this definition")

DC optimizer loss

Type:

_float_

## BatteryDispatch Group[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#batterydispatch-group "Link to this heading")

_class_ PySAM.Battery.Battery.BatteryDispatch[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch "Link to this definition")

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.assign "Link to this definition")

Assign attributes from dictionary, overwriting but not removing values.

`BatteryDispatch_vals = { var: val, ...}`

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.export "Link to this definition")

Export attributes into dictionary.

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.replace "Link to this definition")

Replace attributes from dictionary, unassigning values not present in input `dict`.

`BatteryDispatch_vals = { var: val, ...}`

batt\_custom\_dispatch[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_custom_dispatch "Link to this definition")

Custom battery power for every time step \[kW\]

**Info:** kWAC if AC-connected, else kWDC

**Required:** Required if en\_batt=1&en\_standalone\_batt=0&batt\_dispatch\_choice=2

Type:

_sequence_

batt\_cycle\_cost[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_cycle_cost "Link to this definition")

Input battery cycle degradaton penalty per year \[$/cycle-kWh\]

**Info:** length 1 or analysis\_period, length 1 will be extended using inflation

**Required:** Required if batt\_cycle\_cost\_choice=1

Type:

_sequence_

batt\_cycle\_cost\_choice[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_cycle_cost_choice "Link to this definition")

Use SAM cost model for degradaton penalty or input custom via batt\_cycle\_cost \[0/1\]

**Options:** 0=UseCostModel,1=InputCost

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

batt\_dispatch\_auto\_btm\_can\_discharge\_to\_grid[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_auto_btm_can_discharge_to_grid "Link to this definition")

Behind the meter battery can discharge to grid? \[0/1\]

Type:

_float_

batt\_dispatch\_auto\_can\_charge[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_auto_can_charge "Link to this definition")

System charging allowed for automated dispatch? \[0/1\]

Type:

_float_

batt\_dispatch\_auto\_can\_clipcharge[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_auto_can_clipcharge "Link to this definition")

Battery can charge from clipped power? \[0/1\]

Type:

_float_

batt\_dispatch\_auto\_can\_curtailcharge[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_auto_can_curtailcharge "Link to this definition")

Battery can charge from grid-limited system power? \[0/1\]

Type:

_float_

batt\_dispatch\_auto\_can\_fuelcellcharge[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_auto_can_fuelcellcharge "Link to this definition")

Charging from fuel cell allowed for automated dispatch? \[0/1\]

Type:

_float_

batt\_dispatch\_auto\_can\_gridcharge[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_auto_can_gridcharge "Link to this definition")

Grid charging allowed for automated dispatch? \[0/1\]

Type:

_float_

batt\_dispatch\_charge\_only\_system\_exceeds\_load[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_charge_only_system_exceeds_load "Link to this definition")

Battery can charge from system only when system output exceeds load \[0/1\]

**Required:** Required if en\_batt=1&en\_standalone\_batt=0&batt\_meter\_position=0

Type:

_float_

batt\_dispatch\_choice[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_choice "Link to this definition")

Battery dispatch algorithm \[0/1/2/3/4/5\]

**Options:** If behind the meter: 0=PeakShaving,1=InputGridTarget,2=InputBatteryPower,3=ManualDispatch,4=RetailRateDispatch,5=SelfConsumption if front of meter: 0=AutomatedEconomic,1=PV\_Smoothing,2=InputBatteryPower,3=ManualDispatch

**Required:** Required if en\_batt=1

Type:

_float_

batt\_dispatch\_discharge\_only\_load\_exceeds\_system[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_discharge_only_load_exceeds_system "Link to this definition")

Battery can discharge battery only when load exceeds system output \[0/1\]

**Required:** Required if en\_batt=1&en\_standalone\_batt=0&batt\_meter\_position=0

Type:

_float_

batt\_dispatch\_load\_forecast\_choice[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_load_forecast_choice "Link to this definition")

Load forecast choice for automatic dispatch \[0/1/2\]

**Options:** 0=LookAhead,1=LookBehind,2=InputForecast

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

The value of the following variables depends on `batt_dispatch_load_forecast_choice`:

> *   batt\_load\_ac\_forecast
>     
> *   batt\_load\_ac\_forecast\_escalation
>     

Type:

_float_

batt\_dispatch\_pvs\_ac\_lb[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_pvs_ac_lb "Link to this definition")

AC lower bound \[fraction of nameplate\]

**Required:** Required if en\_batt=1&en\_standalone\_batt=0&batt\_meter\_position=1&batt\_dispatch\_choice=1

Type:

_float_

batt\_dispatch\_pvs\_ac\_lb\_enable[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_pvs_ac_lb_enable "Link to this definition")

Enable AC lower bound \[0/1\]

**Required:** Required if en\_batt=1&en\_standalone\_batt=0&batt\_meter\_position=1&batt\_dispatch\_choice=1

Type:

_float_

batt\_dispatch\_pvs\_ac\_ub[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_pvs_ac_ub "Link to this definition")

AC upper bound \[fraction of nameplate\]

**Required:** Required if en\_batt=1&en\_standalone\_batt=0&batt\_meter\_position=1&batt\_dispatch\_choice=1

Type:

_float_

batt\_dispatch\_pvs\_ac\_ub\_enable[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_pvs_ac_ub_enable "Link to this definition")

Enable AC upper bound \[0/1\]

**Required:** Required if en\_batt=1&en\_standalone\_batt=0&batt\_meter\_position=1&batt\_dispatch\_choice=1

Type:

_float_

batt\_dispatch\_pvs\_curtail\_as\_control[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_pvs_curtail_as_control "Link to this definition")

Correct up-ramp violations \[0/1\]

**Required:** Required if en\_batt=1&en\_standalone\_batt=0&batt\_meter\_position=1&batt\_dispatch\_choice=1

Type:

_float_

batt\_dispatch\_pvs\_curtail\_if\_violation[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_pvs_curtail_if_violation "Link to this definition")

Curtail violations \[0/1\]

**Required:** Required if en\_batt=1&en\_standalone\_batt=0&batt\_meter\_position=1&batt\_dispatch\_choice=1

Type:

_float_

batt\_dispatch\_pvs\_forecast\_shift\_periods[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_pvs_forecast_shift_periods "Link to this definition")

Forecasting window \[periods of ramp intervals\]

**Required:** Required if en\_batt=1&en\_standalone\_batt=0&batt\_meter\_position=1&batt\_dispatch\_choice=1

Type:

_float_

batt\_dispatch\_pvs\_kf[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_pvs_kf "Link to this definition")

Forecast accumulation error multiplier (kf)

**Required:** Required if en\_batt=1&en\_standalone\_batt=0&batt\_meter\_position=1&batt\_dispatch\_choice=1

Type:

_float_

batt\_dispatch\_pvs\_ki[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_pvs_ki "Link to this definition")

Return to rest SOC multiplier (ki)

**Required:** Required if en\_batt=1&en\_standalone\_batt=0&batt\_meter\_position=1&batt\_dispatch\_choice=1

Type:

_float_

batt\_dispatch\_pvs\_kp[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_pvs_kp "Link to this definition")

Track PV power multiplier (kp)

**Required:** Required if en\_batt=1&en\_standalone\_batt=0&batt\_meter\_position=1&batt\_dispatch\_choice=1

Type:

_float_

batt\_dispatch\_pvs\_max\_ramp[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_pvs_max_ramp "Link to this definition")

Maximum ramp rate \[% of nameplate per ramp interval\]

**Required:** Required if en\_batt=1&en\_standalone\_batt=0&batt\_meter\_position=1&batt\_dispatch\_choice=1

Type:

_float_

batt\_dispatch\_pvs\_nameplate\_ac[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_pvs_nameplate_ac "Link to this definition")

Nameplate for pv smoothing \[kWac\]

**Required:** Required if en\_batt=1&en\_standalone\_batt=0&batt\_meter\_position=1&batt\_dispatch\_choice=1

Type:

_float_

batt\_dispatch\_pvs\_short\_forecast\_enable[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_pvs_short_forecast_enable "Link to this definition")

Enable short term power forecast \[0/1\]

**Required:** Required if en\_batt=1&en\_standalone\_batt=0&batt\_meter\_position=1&batt\_dispatch\_choice=1

Type:

_float_

batt\_dispatch\_pvs\_soc\_rest[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_pvs_soc_rest "Link to this definition")

Battery resting SOC \[%\]

**Required:** Required if en\_batt=1&en\_standalone\_batt=0&batt\_meter\_position=1&batt\_dispatch\_choice=1

Type:

_float_

batt\_dispatch\_pvs\_timestep\_multiplier[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_pvs_timestep_multiplier "Link to this definition")

Ramp timestep multiplier

**Required:** Required if en\_batt=1&en\_standalone\_batt=0&batt\_meter\_position=1&batt\_dispatch\_choice=1

Type:

_float_

batt\_dispatch\_update\_frequency\_hours[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_update_frequency_hours "Link to this definition")

Frequency to update the look-ahead dispatch \[hours\]

Type:

_float_

batt\_dispatch\_wf\_forecast\_choice[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_dispatch_wf_forecast_choice "Link to this definition")

Weather forecast choice for automatic dispatch \[0/1/2\]

**Options:** 0=LookAhead,1=LookBehind,2=InputForecast

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

batt\_load\_ac\_forecast[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_load_ac_forecast "Link to this definition")

Load ac power forecast \[kW\]

**Info:** Length either 8760 or 8760 \* steps per hour

The value of `batt_load_ac_forecast` depends on the following variables:

> *   batt\_dispatch\_load\_forecast\_choice
>     

Type:

_sequence_

batt\_load\_ac\_forecast\_escalation[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_load_ac_forecast_escalation "Link to this definition")

Annual load escalation for ac power forecast \[kW\]

**Options:** length <= analysis\_period

The value of `batt_load_ac_forecast_escalation` depends on the following variables:

> *   batt\_dispatch\_load\_forecast\_choice
>     
> *   load\_escalation
>     

Type:

_sequence_

batt\_look\_ahead\_hours[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_look_ahead_hours "Link to this definition")

Hours to look ahead in automated dispatch \[hours\]

**Constraints:** MIN=1

Type:

_float_

batt\_pv\_ac\_forecast[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_pv_ac_forecast "Link to this definition")

PV ac power forecast \[kW\]

**Info:** Length either 8760 \* steps per hour (values repeat each year) or 8760 \* steps per hour \* analysis period

Type:

_sequence_

batt\_pv\_clipping\_forecast[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_pv_clipping_forecast "Link to this definition")

PV clipping forecast \[kW\]

**Info:** Length either 8760 \* steps per hour (values repeat each year) or 8760 \* steps per hour \* analysis period

Type:

_sequence_

batt\_target\_choice[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_target_choice "Link to this definition")

Target power input option \[0/1\]

**Options:** 0=InputMonthlyTarget,1=InputFullTimeSeries

**Required:** Required if en\_batt=1&en\_standalone\_batt=0&batt\_meter\_position=0&batt\_dispatch\_choice=1

Type:

_float_

batt\_target\_power[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_target_power "Link to this definition")

Grid target power for every time step \[kW\]

**Required:** Required if en\_batt=1&batt\_meter\_position=0&batt\_dispatch\_choice=1

Type:

_sequence_

batt\_target\_power\_monthly[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.batt_target_power_monthly "Link to this definition")

Grid target power on monthly basis \[kW\]

**Required:** Required if en\_batt=1&batt\_meter\_position=0&batt\_dispatch\_choice=1

Type:

_sequence_

dispatch\_manual\_btm\_discharge\_to\_grid[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.dispatch_manual_btm_discharge_to_grid "Link to this definition")

Periods 1-6 behind the meter discharging to grid allowed?

**Required:** Required if en\_batt=1&batt\_dispatch\_choice=3&batt\_meter\_position=0

Type:

_sequence_

dispatch\_manual\_charge[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.dispatch_manual_charge "Link to this definition")

Periods 1-6 charging from system allowed?

**Required:** Required if en\_batt=1&en\_standalone\_batt=0&batt\_dispatch\_choice=3

Type:

_sequence_

dispatch\_manual\_discharge[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.dispatch_manual_discharge "Link to this definition")

Periods 1-6 discharging allowed?

**Required:** Required if en\_batt=1&batt\_dispatch\_choice=3

The value of the following variables depends on `dispatch_manual_discharge`:

> *   dispatch\_manual\_percent\_discharge
>     

Type:

_sequence_

dispatch\_manual\_fuelcellcharge[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.dispatch_manual_fuelcellcharge "Link to this definition")

Periods 1-6 charging from fuel cell allowed?

Type:

_sequence_

dispatch\_manual\_gridcharge[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.dispatch_manual_gridcharge "Link to this definition")

Periods 1-6 grid charging allowed?

**Required:** Required if en\_batt=1&batt\_dispatch\_choice=3

The value of the following variables depends on `dispatch_manual_gridcharge`:

> *   dispatch\_manual\_percent\_gridcharge
>     

Type:

_sequence_

dispatch\_manual\_percent\_discharge[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.dispatch_manual_percent_discharge "Link to this definition")

Periods 1-6 discharge percent \[%\]

**Required:** Required if en\_batt=1&batt\_dispatch\_choice=3

The value of `dispatch_manual_percent_discharge` depends on the following variables:

> *   dispatch\_manual\_discharge
>     

Type:

_sequence_

dispatch\_manual\_percent\_gridcharge[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.dispatch_manual_percent_gridcharge "Link to this definition")

Periods 1-6 gridcharge percent \[%\]

**Required:** Required if en\_batt=1&batt\_dispatch\_choice=3

The value of `dispatch_manual_percent_gridcharge` depends on the following variables:

> *   dispatch\_manual\_gridcharge
>     

Type:

_sequence_

dispatch\_manual\_sched[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.dispatch_manual_sched "Link to this definition")

Battery dispatch schedule for weekday

**Required:** Required if en\_batt=1&batt\_dispatch\_choice=3

Type:

_sequence\[sequence\]_

dispatch\_manual\_sched\_weekend[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.dispatch_manual_sched_weekend "Link to this definition")

Battery dispatch schedule for weekend

**Required:** Required if en\_batt=1&batt\_dispatch\_choice=3

Type:

_sequence\[sequence\]_

dispatch\_manual\_system\_charge\_first[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.dispatch_manual_system_charge_first "Link to this definition")

System charges battery before meeting load \[0/1\]

**Options:** 0=LoadFirst,1=ChargeFirst

**Required:** Required if en\_batt=1&en\_standalone\_batt=0&batt\_meter\_position=0&batt\_dispatch\_choice=3&batt\_dispatch\_charge\_only\_system\_exceeds\_load=0

Type:

_float_

start\_day\_of\_year[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.BatteryDispatch.start_day_of_year "Link to this definition")

Start day of year for TOD periods \[0..6\]

**Options:** 0=Monday, 6=Sunday

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

## SystemCosts Group[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#systemcosts-group "Link to this heading")

_class_ PySAM.Battery.Battery.SystemCosts[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.SystemCosts "Link to this definition")

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.SystemCosts.assign "Link to this definition")

Assign attributes from dictionary, overwriting but not removing values.

`SystemCosts_vals = { var: val, ...}`

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.SystemCosts.export "Link to this definition")

Export attributes into dictionary.

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.SystemCosts.replace "Link to this definition")

Replace attributes from dictionary, unassigning values not present in input `dict`.

`SystemCosts_vals = { var: val, ...}`

om\_batt\_replacement\_cost[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.SystemCosts.om_batt_replacement_cost "Link to this definition")

Replacement cost 1 \[$/kWh\]

**Required:** False. Automatically set to 0.0 if not assigned explicitly or loaded from defaults.

Type:

_sequence_

om\_batt\_variable\_cost[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.SystemCosts.om_batt_variable_cost "Link to this definition")

Battery production-based System Costs amount \[$/MWh\]

**Required:** False. Automatically set to 0.0 if not assigned explicitly or loaded from defaults.

Type:

_sequence_

om\_production\_escal[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.SystemCosts.om_production_escal "Link to this definition")

Production-based O&M escalation \[%/year\]

**Required:** False. Automatically set to 0.0 if not assigned explicitly or loaded from defaults.

Type:

_float_

om\_replacement\_cost\_escal[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.SystemCosts.om_replacement_cost_escal "Link to this definition")

Replacement cost escalation \[%/year\]

**Required:** False. Automatically set to 0.0 if not assigned explicitly or loaded from defaults.

Type:

_float_

## FuelCell Group[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#fuelcell-group "Link to this heading")

_class_ PySAM.Battery.Battery.FuelCell[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.FuelCell "Link to this definition")

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.FuelCell.assign "Link to this definition")

Assign attributes from dictionary, overwriting but not removing values.

`FuelCell_vals = { var: val, ...}`

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.FuelCell.export "Link to this definition")

Export attributes into dictionary.

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.FuelCell.replace "Link to this definition")

Replace attributes from dictionary, unassigning values not present in input `dict`.

`FuelCell_vals = { var: val, ...}`

fuelcell\_power[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.FuelCell.fuelcell_power "Link to this definition")

Electricity from fuel cell AC \[kW\]

Type:

_sequence_

## PriceSignal Group[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#pricesignal-group "Link to this heading")

_class_ PySAM.Battery.Battery.PriceSignal[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.PriceSignal "Link to this definition")

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.PriceSignal.assign "Link to this definition")

Assign attributes from dictionary, overwriting but not removing values.

`PriceSignal_vals = { var: val, ...}`

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.PriceSignal.export "Link to this definition")

Export attributes into dictionary.

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.PriceSignal.replace "Link to this definition")

Replace attributes from dictionary, unassigning values not present in input `dict`.

`PriceSignal_vals = { var: val, ...}`

dispatch\_factors\_ts[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.PriceSignal.dispatch_factors_ts "Link to this definition")

Dispatch payment factor time step

**Required:** Required if forecast\_price\_signal\_model=0&en\_batt=1&batt\_meter\_position=1&ppa\_multiplier\_model=1

Type:

_sequence_

dispatch\_sched\_weekday[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.PriceSignal.dispatch_sched_weekday "Link to this definition")

Diurnal weekday TOD periods \[1..9\]

**Info:** 12 x 24 matrix

**Required:** Required if en\_batt=1&batt\_meter\_position=1&forecast\_price\_signal\_model=0&ppa\_multiplier\_model=0

Type:

_sequence\[sequence\]_

dispatch\_sched\_weekend[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.PriceSignal.dispatch_sched_weekend "Link to this definition")

Diurnal weekend TOD periods \[1..9\]

**Info:** 12 x 24 matrix

**Required:** Required if en\_batt=1&batt\_meter\_position=1&forecast\_price\_signal\_model=0&ppa\_multiplier\_model=0

Type:

_sequence\[sequence\]_

dispatch\_tod\_factors[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.PriceSignal.dispatch_tod_factors "Link to this definition")

TOD factors for periods 1-9

**Required:** Required if en\_batt=1&batt\_meter\_position=1&forecast\_price\_signal\_model=0&ppa\_multiplier\_model=0

Type:

_sequence_

forecast\_price\_signal\_model[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.PriceSignal.forecast_price_signal_model "Link to this definition")

Forecast price signal model selected \[0/1\]

**Options:** 0=PPA based,1=Merchant Plant

**Constraints:** INTEGER,MIN=0,MAX=1

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

mp\_ancserv1\_revenue[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.PriceSignal.mp_ancserv1_revenue "Link to this definition")

Ancillary services 1 revenue input \[ \[MW, $/MW\]\]

**Required:** Required if en\_batt=1&batt\_meter\_position=1&forecast\_price\_signal\_model=1

Type:

_sequence\[sequence\]_

mp\_ancserv2\_revenue[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.PriceSignal.mp_ancserv2_revenue "Link to this definition")

Ancillary services 2 revenue input \[ \[MW, $/MW\]\]

**Required:** Required if en\_batt=1&batt\_meter\_position=1&forecast\_price\_signal\_model=1

Type:

_sequence\[sequence\]_

mp\_ancserv3\_revenue[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.PriceSignal.mp_ancserv3_revenue "Link to this definition")

Ancillary services 3 revenue input \[ \[MW, $/MW\]\]

**Required:** Required if en\_batt=1&batt\_meter\_position=1&forecast\_price\_signal\_model=1

Type:

_sequence\[sequence\]_

mp\_ancserv4\_revenue[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.PriceSignal.mp_ancserv4_revenue "Link to this definition")

Ancillary services 4 revenue input \[ \[MW, $/MW\]\]

**Required:** Required if en\_batt=1&batt\_meter\_position=1&forecast\_price\_signal\_model=1

Type:

_sequence\[sequence\]_

mp\_enable\_ancserv1[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.PriceSignal.mp_enable_ancserv1 "Link to this definition")

Enable ancillary services 1 revenue \[0/1\]

**Constraints:** INTEGER,MIN=0,MAX=1

**Required:** Required if forecast\_price\_signal\_model=1

Type:

_float_

mp\_enable\_ancserv2[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.PriceSignal.mp_enable_ancserv2 "Link to this definition")

Enable ancillary services 2 revenue \[0/1\]

**Constraints:** INTEGER,MIN=0,MAX=1

**Required:** Required if forecast\_price\_signal\_model=1

Type:

_float_

mp\_enable\_ancserv3[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.PriceSignal.mp_enable_ancserv3 "Link to this definition")

Enable ancillary services 3 revenue \[0/1\]

**Constraints:** INTEGER,MIN=0,MAX=1

**Required:** Required if forecast\_price\_signal\_model=1

Type:

_float_

mp\_enable\_ancserv4[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.PriceSignal.mp_enable_ancserv4 "Link to this definition")

Enable ancillary services 4 revenue \[0/1\]

**Constraints:** INTEGER,MIN=0,MAX=1

**Required:** Required if forecast\_price\_signal\_model=1

Type:

_float_

mp\_enable\_energy\_market\_revenue[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.PriceSignal.mp_enable_energy_market_revenue "Link to this definition")

Enable energy market revenue \[0/1\]

**Options:** 0=false,1=true

**Constraints:** INTEGER,MIN=0,MAX=1

**Required:** Required if en\_batt=1&batt\_meter\_position=1&forecast\_price\_signal\_model=1

Type:

_float_

mp\_energy\_market\_revenue[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.PriceSignal.mp_energy_market_revenue "Link to this definition")

Energy market revenue input \[ \[MW, $/MW\]\]

**Required:** Required if en\_batt=1&batt\_meter\_position=1&forecast\_price\_signal\_model=1

Type:

_sequence\[sequence\]_

ppa\_escalation[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.PriceSignal.ppa_escalation "Link to this definition")

PPA escalation rate \[%/year\]

**Required:** Required if forecast\_price\_signal\_model=0&en\_batt=1&batt\_meter\_position=1

Type:

_float_

ppa\_multiplier\_model[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.PriceSignal.ppa_multiplier_model "Link to this definition")

PPA multiplier model \[0/1\]

**Options:** 0=diurnal,1=timestep

**Constraints:** INTEGER,MIN=0

**Required:** Required if forecast\_price\_signal\_model=0&en\_batt=1&batt\_meter\_position=1

Type:

_float_

ppa\_price\_input[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.PriceSignal.ppa_price_input "Link to this definition")

PPA Price Input \[$/kWh\]

**Required:** Required if forecast\_price\_signal\_model=0&en\_batt=1&batt\_meter\_position=1

Type:

_sequence_

## Revenue Group[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#revenue-group "Link to this heading")

_class_ PySAM.Battery.Battery.Revenue[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Revenue "Link to this definition")

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Revenue.assign "Link to this definition")

Assign attributes from dictionary, overwriting but not removing values.

`Revenue_vals = { var: val, ...}`

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Revenue.export "Link to this definition")

Export attributes into dictionary.

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Revenue.replace "Link to this definition")

Replace attributes from dictionary, unassigning values not present in input `dict`.

`Revenue_vals = { var: val, ...}`

mp\_ancserv1\_percent\_gen[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Revenue.mp_ancserv1_percent_gen "Link to this definition")

Percent of demand to copy to cleared capacity array \[%\]

**Constraints:** MIN=0,MAX=100

**Required:** Required if forecast\_price\_signal\_model=1&mp\_enable\_ancserv1\_percent\_gen=1

Type:

_float_

mp\_ancserv1\_revenue\_single[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Revenue.mp_ancserv1_revenue_single "Link to this definition")

Ancillary services 1 revenue input

**Info:** Lifetime x 1\[Price($/MWh)\]

**Required:** Required if forecast\_price\_signal\_model=1&mp\_enable\_ancserv1\_percent\_gen=1

Type:

_sequence\[sequence\]_

mp\_ancserv2\_percent\_gen[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Revenue.mp_ancserv2_percent_gen "Link to this definition")

Percent of demand to copy to cleared capacity array \[%\]

**Constraints:** MIN=0,MAX=100

**Required:** Required if forecast\_price\_signal\_model=1&mp\_enable\_ancserv2\_percent\_gen=1

Type:

_float_

mp\_ancserv2\_revenue\_single[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Revenue.mp_ancserv2_revenue_single "Link to this definition")

Ancillary services 2 revenue input

**Info:** Lifetime x 1\[Price($/MWh)\]

**Required:** Required if forecast\_price\_signal\_model=1&mp\_enable\_ancserv2\_percent\_gen=1

Type:

_sequence\[sequence\]_

mp\_ancserv3\_percent\_gen[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Revenue.mp_ancserv3_percent_gen "Link to this definition")

Percent of demand to copy to cleared capacity array \[%\]

**Constraints:** MIN=0,MAX=100

**Required:** Required if forecast\_price\_signal\_model=1&mp\_enable\_ancserv3\_percent\_gen=1

Type:

_float_

mp\_ancserv3\_revenue\_single[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Revenue.mp_ancserv3_revenue_single "Link to this definition")

Ancillary services 3 revenue input

**Info:** Lifetime x 1\[Price($/MWh)\]

**Required:** Required if forecast\_price\_signal\_model=1&mp\_enable\_ancserv3\_percent\_gen=1

Type:

_sequence\[sequence\]_

mp\_ancserv4\_percent\_gen[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Revenue.mp_ancserv4_percent_gen "Link to this definition")

Percent of demand to copy to cleared capacity array \[%\]

**Constraints:** MIN=0,MAX=100

**Required:** Required if forecast\_price\_signal\_model=1&mp\_enable\_ancserv4\_percent\_gen=1

Type:

_float_

mp\_ancserv4\_revenue\_single[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Revenue.mp_ancserv4_revenue_single "Link to this definition")

Ancillary services 4 revenue input

**Info:** Lifetime x 1\[Price($/MWh)\]

**Required:** Required if forecast\_price\_signal\_model=1&mp\_enable\_ancserv4\_percent\_gen=1

Type:

_sequence\[sequence\]_

mp\_enable\_ancserv1\_percent\_gen[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Revenue.mp_enable_ancserv1_percent_gen "Link to this definition")

Enable percent demand cleared capacity option for ancillary service 1 \[0/1\]

**Constraints:** INTEGER,MIN=0,MAX=1

**Required:** Required if forecast\_price\_signal\_model=1

Type:

_float_

mp\_enable\_ancserv2\_percent\_gen[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Revenue.mp_enable_ancserv2_percent_gen "Link to this definition")

Enable percent demand cleared capacity option for ancillary service 2 \[0/1\]

**Constraints:** INTEGER,MIN=0,MAX=1

**Required:** Required if forecast\_price\_signal\_model=1

Type:

_float_

mp\_enable\_ancserv3\_percent\_gen[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Revenue.mp_enable_ancserv3_percent_gen "Link to this definition")

Enable percent demand cleared capacity option for ancillary service 3 \[0/1\]

**Constraints:** INTEGER,MIN=0,MAX=1

**Required:** Required if forecast\_price\_signal\_model=1

Type:

_float_

mp\_enable\_ancserv4\_percent\_gen[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Revenue.mp_enable_ancserv4_percent_gen "Link to this definition")

Enable percent demand cleared capacity option for ancillary service 4 \[0/1\]

**Constraints:** INTEGER,MIN=0,MAX=1

**Required:** Required if forecast\_price\_signal\_model=1

Type:

_float_

mp\_enable\_market\_percent\_gen[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Revenue.mp_enable_market_percent_gen "Link to this definition")

Enable percent demand cleared capacity option for market revenue \[0/1\]

**Constraints:** INTEGER,MIN=0,MAX=1

**Required:** Required if forecast\_price\_signal\_model=1

Type:

_float_

mp\_energy\_market\_revenue\_single[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Revenue.mp_energy_market_revenue_single "Link to this definition")

Energy market revenue input

**Info:** Lifetime x 1 \[Price($/MWh)\]

**Required:** Required if forecast\_price\_signal\_model=1&mp\_enable\_market\_percent\_gen=1

Type:

_sequence\[sequence\]_

mp\_market\_percent\_gen[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Revenue.mp_market_percent_gen "Link to this definition")

Percent of demand to copy to cleared capacity array \[%\]

**Constraints:** MIN=0,MAX=100

**Required:** Required if forecast\_price\_signal\_model=1&mp\_enable\_market\_percent\_gen=1

Type:

_float_

## AdjustmentFactors Group[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#adjustmentfactors-group "Link to this heading")

_class_ PySAM.Battery.Battery.AdjustmentFactors[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.AdjustmentFactors "Link to this definition")

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.AdjustmentFactors.assign "Link to this definition")

Assign attributes from dictionary, overwriting but not removing values.

`AdjustmentFactors_vals = { var: val, ...}`

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.AdjustmentFactors.export "Link to this definition")

Export attributes into dictionary.

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.AdjustmentFactors.replace "Link to this definition")

Replace attributes from dictionary, unassigning values not present in input `dict`.

`AdjustmentFactors_vals = { var: val, ...}`

batt\_adjust\_constant[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.AdjustmentFactors.batt_adjust_constant "Link to this definition")

Battery Constant loss adjustment \[%\]

**Constraints:** MAX=100

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

batt\_adjust\_en\_periods[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.AdjustmentFactors.batt_adjust_en_periods "Link to this definition")

Enable battery period-based adjustment factors \[0/1\]

**Constraints:** BOOLEAN

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

batt\_adjust\_en\_timeindex[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.AdjustmentFactors.batt_adjust_en_timeindex "Link to this definition")

Enable battery lifetime adjustment factors \[0/1\]

**Constraints:** BOOLEAN

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

batt\_adjust\_periods[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.AdjustmentFactors.batt_adjust_periods "Link to this definition")

Battery Period-based Adjustment Factors \[%\]

**Info:** n x 3 matrix \[ start, end, loss \]

**Constraints:** COLS=3

**Required:** Required if batt\_adjust\_en\_periods=1

Type:

_sequence\[sequence\]_

batt\_adjust\_timeindex[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.AdjustmentFactors.batt_adjust_timeindex "Link to this definition")

Battery Lifetime Adjustment Factors \[%\]

**Required:** Required if batt\_adjust\_en\_timeindex=1

Type:

_sequence_

## ElectricityRates Group[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#electricityrates-group "Link to this heading")

_class_ PySAM.Battery.Battery.ElectricityRates[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates "Link to this definition")

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.assign "Link to this definition")

Assign attributes from dictionary, overwriting but not removing values.

`ElectricityRates_vals = { var: val, ...}`

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.export "Link to this definition")

Export attributes into dictionary.

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.replace "Link to this definition")

Replace attributes from dictionary, unassigning values not present in input `dict`.

`ElectricityRates_vals = { var: val, ...}`

en\_electricity\_rates[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.en_electricity_rates "Link to this definition")

Optionally enable/disable electricity\_rate \[years\]

**Constraints:** INTEGER,MIN=0,MAX=1

Type:

_float_

rate\_escalation[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.rate_escalation "Link to this definition")

Annual electricity rate escalation \[%/year\]

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_sequence_

start\_day\_of\_year[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.start_day_of_year "Link to this definition")

Start day of year for TOD periods \[0..6\]

**Options:** 0=Monday, 6=Sunday

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

ur\_annual\_min\_charge[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_annual_min_charge "Link to this definition")

Annual minimum charge \[$\]

**Required:** False. Automatically set to 0.0 if not assigned explicitly or loaded from defaults.

Type:

_float_

ur\_billing\_demand\_lookback\_percentages[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_billing_demand_lookback_percentages "Link to this definition")

Billing demand lookback percentages by month and consider actual peak demand \[%\]

**Info:** 12x2

**Required:** Required if ur\_enable\_billing\_demand=1

Type:

_sequence\[sequence\]_

ur\_billing\_demand\_lookback\_period[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_billing_demand_lookback_period "Link to this definition")

Billing demand lookback period \[mn\]

**Constraints:** INTEGER,MIN=0,MAX=12

**Required:** Required if ur\_enable\_billing\_demand=1

Type:

_float_

ur\_billing\_demand\_minimum[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_billing_demand_minimum "Link to this definition")

Minimum billing demand \[kW\]

**Required:** Required if ur\_enable\_billing\_demand=1

Type:

_float_

ur\_dc\_billing\_demand\_periods[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_dc_billing_demand_periods "Link to this definition")

Billing demand applicability to a given demand charge time of use period

**Required:** Required if ur\_enable\_billing\_demand=1

Type:

_sequence\[sequence\]_

ur\_dc\_enable[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_dc_enable "Link to this definition")

Enable demand charge \[0/1\]

**Options:** 0=disable,1=enable

**Constraints:** BOOLEAN

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

ur\_dc\_flat\_mat[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_dc_flat_mat "Link to this definition")

Demand rates (flat) table \[col 0=month, col 1=tier no, col 2=tier peak (kW), col 3=charge ($/kW)\]

**Info:** nx4

**Required:** Required if ur\_dc\_enable=1

Type:

_sequence\[sequence\]_

ur\_dc\_sched\_weekday[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_dc_sched_weekday "Link to this definition")

Demand charge weekday schedule \[Periods defined in ur\_dc\_tou\_mat\]

**Info:** 12x24

Type:

_sequence\[sequence\]_

ur\_dc\_sched\_weekend[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_dc_sched_weekend "Link to this definition")

Demand charge weekend schedule \[Periods defined in ur\_dc\_tou\_mat\]

**Info:** 12x24

Type:

_sequence\[sequence\]_

ur\_dc\_tou\_mat[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_dc_tou_mat "Link to this definition")

Demand rates (TOU) table \[col 0=period no, col 1=tier no, col 2=tier peak (kW), col 3=charge ($/kW)\]

**Info:** nx4

**Required:** Required if ur\_dc\_enable=1

Type:

_sequence\[sequence\]_

ur\_ec\_sched\_weekday[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_ec_sched_weekday "Link to this definition")

Energy charge weekday schedule \[Periods defined in ur\_ec\_tou\_mat\]

**Info:** 12x24

Type:

_sequence\[sequence\]_

ur\_ec\_sched\_weekend[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_ec_sched_weekend "Link to this definition")

Energy charge weekend schedule \[Periods defined in ur\_ec\_tou\_mat\]

**Info:** 12x24

Type:

_sequence\[sequence\]_

ur\_ec\_tou\_mat[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_ec_tou_mat "Link to this definition")

Energy rates table \[col 0=period no, col 1=tier no, col 2=max usage, col 3=max usage units (0=kWh, 1=kWh/kW, 2=kWh daily, 3=kWh/kW daily), col 4=buy rate ($/kWh), col 5=sell rate ($/kWh)\]

**Info:** nx6

Type:

_sequence\[sequence\]_

ur\_en\_ts\_buy\_rate[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_en_ts_buy_rate "Link to this definition")

Enable time step buy rates \[0/1\]

**Options:** 0=disable,1=enable

**Constraints:** BOOLEAN

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

ur\_en\_ts\_sell\_rate[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_en_ts_sell_rate "Link to this definition")

Enable time step sell rates \[0/1\]

**Options:** 0=disable,1=enable

**Constraints:** BOOLEAN

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

ur\_enable\_billing\_demand[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_enable_billing_demand "Link to this definition")

Enable billing demand ratchets \[0/1\]

**Options:** 0=disable,1=enable

**Constraints:** INTEGER,MIN=0,MAX=1

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

ur\_metering\_option[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_metering_option "Link to this definition")

Metering options \[0=net energy metering,1=net energy metering with $ credits,2=net billing,3=net billing with carryover to next month,4=buy all - sell all\]

**Info:** Net metering monthly excess

**Constraints:** INTEGER,MIN=0,MAX=4

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

ur\_monthly\_fixed\_charge[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_monthly_fixed_charge "Link to this definition")

Monthly fixed charge \[$\]

**Required:** False. Automatically set to 0.0 if not assigned explicitly or loaded from defaults.

Type:

_float_

ur\_monthly\_min\_charge[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_monthly_min_charge "Link to this definition")

Monthly minimum charge \[$\]

**Required:** False. Automatically set to 0.0 if not assigned explicitly or loaded from defaults.

Type:

_float_

ur\_nb\_apply\_credit\_current\_month[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_nb_apply_credit_current_month "Link to this definition")

Apply earned credits to balance before rolling over excess \[0/1\]

**Options:** 0=disable,1=enable

**Constraints:** INTEGER,MIN=0,MAX=1

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

ur\_nb\_credit\_expire[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_nb_credit_expire "Link to this definition")

Credit is lost upon end of year \[0/1\]

**Options:** 0=disable,1=enable

**Constraints:** INTEGER,MIN=0,MAX=1

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

ur\_nm\_credit\_month[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_nm_credit_month "Link to this definition")

Month of year end payout (true-up) \[mn\]

**Constraints:** INTEGER,MIN=0,MAX=11

**Required:** False. Automatically set to 11 if not assigned explicitly or loaded from defaults.

Type:

_float_

ur\_nm\_credit\_rollover[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_nm_credit_rollover "Link to this definition")

Apply net metering true-up credits to future bills \[0/1\]

**Options:** 0=disable,1=enable

**Constraints:** INTEGER,MIN=0,MAX=1

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

ur\_nm\_yearend\_sell\_rate[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_nm_yearend_sell_rate "Link to this definition")

Net metering true-up credit sell rate \[$/kWh\]

**Required:** False. Automatically set to 0.0 if not assigned explicitly or loaded from defaults.

Type:

_float_

ur\_sell\_eq\_buy[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_sell_eq_buy "Link to this definition")

Set sell rate equal to buy rate \[0/1\]

**Info:** Optional override

**Constraints:** BOOLEAN

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

ur\_ts\_buy\_rate[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_ts_buy_rate "Link to this definition")

Time step buy rates \[$/kWh\]

Type:

_sequence_

ur\_ts\_sell\_rate[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_ts_sell_rate "Link to this definition")

Time step sell rates \[$/kWh\]

Type:

_sequence_

ur\_yearzero\_usage\_peaks[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.ElectricityRates.ur_yearzero_usage_peaks "Link to this definition")

Peak usage by month for year zero \[kW\]

**Info:** 12

**Required:** Required if ur\_enable\_billing\_demand=1

Type:

_sequence_

## GridLimits Group[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#gridlimits-group "Link to this heading")

_class_ PySAM.Battery.Battery.GridLimits[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.GridLimits "Link to this definition")

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.GridLimits.assign "Link to this definition")

Assign attributes from dictionary, overwriting but not removing values.

`GridLimits_vals = { var: val, ...}`

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.GridLimits.export "Link to this definition")

Export attributes into dictionary.

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.GridLimits.replace "Link to this definition")

Replace attributes from dictionary, unassigning values not present in input `dict`.

`GridLimits_vals = { var: val, ...}`

enable\_interconnection\_limit[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.GridLimits.enable_interconnection_limit "Link to this definition")

Enable grid interconnection limit \[0/1\]

**Info:** Enable a grid interconnection limit

Type:

_float_

grid\_curtailment[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.GridLimits.grid_curtailment "Link to this definition")

Grid curtailment as energy delivery limit (first year) \[MW\]

**Required:** False for configuration with default inputs. May be required if a variable dependent on its value changes. Example: For the Detailed PV - Single Owner configuration, only Subarray 1 is enabled in the configuration defaults, so Subarray 2 inputs would not be required; if Subarray 2 is enabled, then Subarray 2 inputs is required.

The value of the following variables depends on `grid_curtailment`:

> *   batt\_room\_temperature\_celsius
>     

Type:

_sequence_

grid\_interconnection\_limit\_kwac[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.GridLimits.grid_interconnection_limit_kwac "Link to this definition")

Grid interconnection limit \[kWac\]

Type:

_float_

## HybridCosts Group[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#hybridcosts-group "Link to this heading")

_class_ PySAM.Battery.Battery.HybridCosts[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.HybridCosts "Link to this definition")

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.HybridCosts.assign "Link to this definition")

Assign attributes from dictionary, overwriting but not removing values.

`HybridCosts_vals = { var: val, ...}`

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.HybridCosts.export "Link to this definition")

Export attributes into dictionary.

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.HybridCosts.replace "Link to this definition")

Replace attributes from dictionary, unassigning values not present in input `dict`.

`HybridCosts_vals = { var: val, ...}`

add\_om\_num\_types[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.HybridCosts.add_om_num_types "Link to this definition")

Number of O and M types

**Info:** battery,fuelcell

**Constraints:** INTEGER,MIN=0,MAX=2

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

degradation[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.HybridCosts.degradation "Link to this definition")

Annual AC degradation \[%\]

**Required:** False. Automatically set to 0.0 if not assigned explicitly or loaded from defaults.

Type:

_sequence_

land\_area[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.HybridCosts.land_area "Link to this definition")

Total land area \[acres\]

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

om\_batt\_capacity\_cost[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.HybridCosts.om_batt_capacity_cost "Link to this definition")

Battery capacity-based System Costs amount \[$/kWcap\]

**Info:** battery

**Required:** False. Automatically set to 0.0 if not assigned explicitly or loaded from defaults.

Type:

_sequence_

om\_batt\_fixed\_cost[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.HybridCosts.om_batt_fixed_cost "Link to this definition")

Battery fixed System Costs annual amount \[$/year\]

**Info:** battery

**Required:** False. Automatically set to 0.0 if not assigned explicitly or loaded from defaults.

Type:

_sequence_

om\_batt\_nameplate[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.HybridCosts.om_batt_nameplate "Link to this definition")

Battery capacity for System Costs values \[kW\]

**Info:** battery

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

The value of `om_batt_nameplate` depends on the following variables:

> *   batt\_Qfull
>     
> *   batt\_Vnom\_default
>     
> *   batt\_ac\_dc\_efficiency
>     
> *   batt\_ac\_or\_dc
>     
> *   batt\_chem
>     
> *   batt\_computed\_bank\_capacity
>     
> *   batt\_current\_choice
>     
> *   batt\_dc\_ac\_efficiency
>     
> *   batt\_dc\_dc\_efficiency
>     

Type:

_float_

om\_capacity\_escal[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.HybridCosts.om_capacity_escal "Link to this definition")

Capacity-based O&M escalation \[%/year\]

**Required:** False. Automatically set to 0.0 if not assigned explicitly or loaded from defaults.

Type:

_float_

om\_fixed\_escal[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.HybridCosts.om_fixed_escal "Link to this definition")

Fixed O&M escalation \[%/year\]

**Required:** False. Automatically set to 0.0 if not assigned explicitly or loaded from defaults.

Type:

_float_

om\_land\_lease[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.HybridCosts.om_land_lease "Link to this definition")

Land lease cost \[$/acre\]

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_sequence_

om\_land\_lease\_escal[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.HybridCosts.om_land_lease_escal "Link to this definition")

Land lease cost escalation \[%/yr\]

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_float_

om\_production1\_values[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.HybridCosts.om_production1_values "Link to this definition")

Battery production for System Costs values \[kWh\]

**Info:** battery

**Required:** False. Automatically set to 0 if not assigned explicitly or loaded from defaults.

Type:

_sequence_

total\_installed\_cost[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.HybridCosts.total_installed_cost "Link to this definition")

Total installed cost \[$\]

**Required:** True

The value of `total_installed_cost` depends on the following variables:

> *   batt\_Qfull
>     
> *   batt\_Vnom\_default
>     
> *   batt\_ac\_dc\_efficiency
>     
> *   batt\_ac\_or\_dc
>     
> *   batt\_chem
>     
> *   batt\_computed\_bank\_capacity
>     
> *   batt\_current\_choice
>     
> *   batt\_dc\_ac\_efficiency
>     
> *   batt\_dc\_dc\_efficiency
>     
> *   batt\_power\_discharge\_max\_kwac
>     
> *   batt\_power\_discharge\_max\_kwdc
>     

Type:

_float_

## Outputs Group[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#outputs-group "Link to this heading")

_class_ PySAM.Battery.Battery.Outputs[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs "Link to this definition")

assign(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.assign "Link to this definition")

Assign attributes from dictionary, overwriting but not removing values.

`Outputs_vals = { var: val, ...}`

export() → dict[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.export "Link to this definition")

Export attributes into dictionary.

replace(_dict_) → None[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.replace "Link to this definition")

Replace attributes from dictionary, unassigning values not present in input `dict`.

`Outputs_vals = { var: val, ...}`

annual\_crit\_load[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.annual_crit_load "Link to this definition")

Critical load energy (year 1) \[kWh\]

Type:

_float_

annual\_crit\_load\_unmet[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.annual_crit_load_unmet "Link to this definition")

Critical load energy unmet (year 1) \[kWh\]

Type:

_float_

annual\_crit\_load\_unmet\_percentage[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.annual_crit_load_unmet_percentage "Link to this definition")

Critical load unmet percentage (year 1) \[%\]

Type:

_float_

annual\_export\_to\_grid\_energy[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.annual_export_to_grid_energy "Link to this definition")

Annual energy exported to grid \[kWh\]

Type:

_sequence_

annual\_import\_to\_grid\_energy[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.annual_import_to_grid_energy "Link to this definition")

Annual energy imported from grid \[kWh\]

Type:

_sequence_

annual\_outage\_losses\_unmet[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.annual_outage_losses_unmet "Link to this definition")

Battery and system losses unmet energy (year 1) \[kWh\]

Type:

_float_

average\_battery\_conversion\_efficiency[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.average_battery_conversion_efficiency "Link to this definition")

Battery average cycle conversion efficiency \[%\]

Type:

_float_

average\_battery\_roundtrip\_efficiency[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.average_battery_roundtrip_efficiency "Link to this definition")

Battery average roundtrip efficiency \[%\]

Type:

_float_

avg\_critical\_load[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.avg_critical_load "Link to this definition")

Hours of autonomy during grid outage critical load met \[kWh\]

Type:

_float_

batt\_DOD[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_DOD "Link to this definition")

Battery cycle depth of discharge \[%\]

Type:

_sequence_

batt\_DOD\_cycle\_average[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_DOD_cycle_average "Link to this definition")

Battery average cycle DOD

Type:

_sequence_

batt\_I[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_I "Link to this definition")

Battery current \[A\]

Type:

_sequence_

batt\_SOC[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_SOC "Link to this definition")

Battery state of charge \[%\]

Type:

_sequence_

batt\_annual\_charge\_energy[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_annual_charge_energy "Link to this definition")

Battery annual energy charged \[kWh\]

Type:

_sequence_

batt\_annual\_charge\_from\_grid[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_annual_charge_from_grid "Link to this definition")

Battery annual energy charged from grid \[kWh\]

Type:

_sequence_

batt\_annual\_charge\_from\_system[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_annual_charge_from_system "Link to this definition")

Battery annual energy charged from system \[kWh\]

Type:

_sequence_

batt\_annual\_discharge\_energy[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_annual_discharge_energy "Link to this definition")

Battery annual energy discharged \[kWh\]

Type:

_sequence_

batt\_annual\_energy\_loss[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_annual_energy_loss "Link to this definition")

Battery annual energy loss \[kWh\]

Type:

_sequence_

batt\_annual\_energy\_system\_loss[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_annual_energy_system_loss "Link to this definition")

Battery annual system energy loss \[kWh\]

Type:

_sequence_

batt\_availability\_loss[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_availability_loss "Link to this definition")

Battery availability loss \[%\]

Type:

_sequence_

batt\_bank\_installed\_capacity[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_bank_installed_capacity "Link to this definition")

Battery bank installed capacity \[kWh\]

Type:

_float_

batt\_bank\_replacement[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_bank_replacement "Link to this definition")

Battery bank replacements per year \[number/year\]

Type:

_sequence_

batt\_capacity\_percent[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_capacity_percent "Link to this definition")

Battery relative capacity to nameplate \[%\]

Type:

_sequence_

batt\_capacity\_percent\_calendar[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_capacity_percent_calendar "Link to this definition")

Battery relative capacity to nameplate (calendar) \[%\]

Type:

_sequence_

batt\_capacity\_percent\_cycle[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_capacity_percent_cycle "Link to this definition")

Battery relative capacity to nameplate (cycling) \[%\]

Type:

_sequence_

batt\_capacity\_thermal\_percent[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_capacity_thermal_percent "Link to this definition")

Battery capacity percent for temperature \[%\]

Type:

_sequence_

batt\_conversion\_loss[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_conversion_loss "Link to this definition")

Battery loss from power electronics \[kW\]

Type:

_sequence_

batt\_cost\_to\_cycle[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_cost_to_cycle "Link to this definition")

Battery computed cycle degradation penalty \[$/cycle-kWh\]

Type:

_sequence_

batt\_cycles[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_cycles "Link to this definition")

Battery number of cycles

Type:

_sequence_

batt\_dispatch\_period[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_dispatch_period "Link to this definition")

Battery manual dispatch period in this timestep

Type:

_sequence_

batt\_dispatch\_sched[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_dispatch_sched "Link to this definition")

Battery dispatch schedule

Type:

_sequence\[sequence\]_

batt\_grid\_charge\_percent[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_grid_charge_percent "Link to this definition")

Battery charge energy charged from grid \[%\]

Type:

_float_

batt\_power[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_power "Link to this definition")

Electricity to/from battery AC \[kW\]

Type:

_sequence_

batt\_power\_dc[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_power_dc "Link to this definition")

Electricity to/from battery DC \[kW\]

Type:

_sequence_

batt\_power\_target[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_power_target "Link to this definition")

Electricity battery power target for automated dispatch \[kW\]

Type:

_sequence_

batt\_pvs\_PV\_ramp\_interval[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_pvs_PV_ramp_interval "Link to this definition")

PV smoothing PV power sampled \[kW\]

Type:

_sequence_

batt\_pvs\_P\_pv\_ac[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_pvs_P_pv_ac "Link to this definition")

PV smoothing PV power before smoothing \[kW\]

Type:

_sequence_

batt\_pvs\_battpower[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_pvs_battpower "Link to this definition")

PV smoothing battpower \[kW\]

Type:

_sequence_

batt\_pvs\_battsoc[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_pvs_battsoc "Link to this definition")

PV smoothing battery SOC \[%\]

Type:

_sequence_

batt\_pvs\_curtail[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_pvs_curtail "Link to this definition")

PV smoothing curtailed power \[kW\]

Type:

_sequence_

batt\_pvs\_energy\_to\_grid\_percent[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_pvs_energy_to_grid_percent "Link to this definition")

PV smoothing energy to grid percent (loss due to curtail and battery loss) \[%\]

Type:

_float_

batt\_pvs\_energy\_to\_grid\_percent\_sam[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_pvs_energy_to_grid_percent_sam "Link to this definition")

PV smoothing energy to grid percent actual (loss due to curtail and battery loss) \[%\]

Type:

_float_

batt\_pvs\_forecast\_pv\_energy[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_pvs_forecast_pv_energy "Link to this definition")

PV smoothing PV power forecast \[kW\]

Type:

_sequence_

batt\_pvs\_outpower[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_pvs_outpower "Link to this definition")

PV smoothing outpower \[kW\]

Type:

_sequence_

batt\_pvs\_violation\_count[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_pvs_violation_count "Link to this definition")

PV smoothing violation count

Type:

_float_

batt\_pvs\_violation\_list[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_pvs_violation_list "Link to this definition")

PV smoothing violation

Type:

_sequence_

batt\_pvs\_violation\_percent[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_pvs_violation_percent "Link to this definition")

PV smoothing violation percent (of all intervals-including nighttime) \[%\]

Type:

_float_

batt\_q0[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_q0 "Link to this definition")

Battery total charge \[Ah\]

Type:

_sequence_

batt\_q1[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_q1 "Link to this definition")

Battery available charge \[Ah\]

Type:

_sequence_

batt\_q2[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_q2 "Link to this definition")

Battery bound charge \[Ah\]

Type:

_sequence_

batt\_qmax[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_qmax "Link to this definition")

Battery maximum charge with degradation \[Ah\]

Type:

_sequence_

batt\_qmaxI[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_qmaxI "Link to this definition")

Battery maximum capacity at current \[Ah\]

Type:

_sequence_

batt\_qmax\_thermal[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_qmax_thermal "Link to this definition")

Battery maximum charge at temperature \[Ah\]

Type:

_sequence_

batt\_revenue\_charge[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_revenue_charge "Link to this definition")

Revenue to charge from system \[$/kWh\]

Type:

_sequence_

batt\_revenue\_clipcharge[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_revenue_clipcharge "Link to this definition")

Revenue to charge from clipped \[$/kWh\]

Type:

_sequence_

batt\_revenue\_discharge[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_revenue_discharge "Link to this definition")

Revenue to discharge \[$/kWh\]

Type:

_sequence_

batt\_revenue\_gridcharge[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_revenue_gridcharge "Link to this definition")

Revenue to charge from grid \[$/kWh\]

Type:

_sequence_

batt\_system\_charge\_percent[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_system_charge_percent "Link to this definition")

Battery charge energy charged from system \[%\]

Type:

_float_

batt\_system\_loss[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_system_loss "Link to this definition")

Battery loss from ancillary equipment \[kW\]

Type:

_sequence_

batt\_temperature[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_temperature "Link to this definition")

Battery temperature \[C\]

Type:

_sequence_

batt\_to\_grid[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_to_grid "Link to this definition")

Electricity to grid from battery AC \[kW\]

Type:

_sequence_

batt\_to\_inverter\_dc[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_to_inverter_dc "Link to this definition")

Electricity to inverter from battery DC \[kW\]

Type:

_sequence_

batt\_to\_load[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_to_load "Link to this definition")

Electricity to load from battery AC \[kW\]

Type:

_sequence_

batt\_to\_system\_load[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_to_system_load "Link to this definition")

Electricity to system loads from battery AC \[kW\]

Type:

_sequence_

batt\_voltage[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_voltage "Link to this definition")

Battery voltage \[V\]

Type:

_sequence_

batt\_voltage\_cell[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_voltage_cell "Link to this definition")

Battery cell voltage \[V\]

Type:

_sequence_

batt\_year1\_charge\_from\_grid[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_year1_charge_from_grid "Link to this definition")

Battery annual energy charged from grid (year 1) \[kWh\]

Type:

_float_

batt\_year1\_charge\_from\_system[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.batt_year1_charge_from_system "Link to this definition")

Battery annual energy charged from system (year 1) \[kWh\]

Type:

_float_

capacity\_factor\_sales[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.capacity_factor_sales "Link to this definition")

Capacity factor based on AC electricity to grid \[%\]

Type:

_float_

cdf\_of\_surviving[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.cdf_of_surviving "Link to this definition")

Hours of autonomy during grid outage cumulative probabilities

Type:

_sequence_

cf\_battery\_replacement\_cost\_schedule[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.cf_battery_replacement_cost_schedule "Link to this definition")

replacement O&M costs \[$\]

Type:

_sequence_

cf\_energy\_net[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.cf_energy_net "Link to this definition")

annual energy \[kWh\]

Type:

_sequence_

cf\_fuelcell\_replacement\_cost\_schedule[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.cf_fuelcell_replacement_cost_schedule "Link to this definition")

replacement O&M costs \[$\]

Type:

_sequence_

cf\_land\_lease\_expense[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.cf_land_lease_expense "Link to this definition")

Land lease expense \[$\]

Type:

_sequence_

cf\_om\_capacity[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.cf_om_capacity "Link to this definition")

capacity O&M costs \[$\]

Type:

_sequence_

cf\_om\_fixed[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.cf_om_fixed "Link to this definition")

fixed O&M costs \[$\]

Type:

_sequence_

cf\_om\_fuel\_cost[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.cf_om_fuel_cost "Link to this definition")

fossil fuel O&M costs \[$\]

Type:

_sequence_

cf\_om\_land\_lease[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.cf_om_land_lease "Link to this definition")

land lease O&M costs \[$\]

Type:

_sequence_

cf\_om\_production[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.cf_om_production "Link to this definition")

production O&M costs \[$\]

Type:

_sequence_

crit\_load[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.crit_load "Link to this definition")

Critical load in this timestep \[kW\]

Type:

_sequence_

crit\_load\_unmet[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.crit_load_unmet "Link to this definition")

Critical load unmet in this timestep \[kW\]

Type:

_sequence_

fuelcell\_to\_batt[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.fuelcell_to_batt "Link to this definition")

Electricity to battery from fuel cell AC \[kW\]

Type:

_sequence_

gen\_without\_battery[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.gen_without_battery "Link to this definition")

Power produced without the battery or curtailment \[kW\]

Type:

_sequence_

grid\_power[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.grid_power "Link to this definition")

Electricity to/from grid AC \[kW\]

Type:

_sequence_

grid\_power\_target[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.grid_power_target "Link to this definition")

Electricity grid power target for automated dispatch \[kW\]

Type:

_sequence_

grid\_to\_batt[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.grid_to_batt "Link to this definition")

Electricity to battery from grid AC \[kW\]

Type:

_sequence_

grid\_to\_load[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.grid_to_load "Link to this definition")

Electricity to load from grid AC \[kW\]

Type:

_sequence_

interconnection\_loss[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.interconnection_loss "Link to this definition")

Electricity loss due to curtailment interconnection outage \[kW\]

Type:

_sequence_

market\_sell\_rate\_series\_yr1[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.market_sell_rate_series_yr1 "Link to this definition")

Power price for battery dispatch \[$/MWh\]

Type:

_sequence_

monthly\_batt\_to\_grid[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.monthly_batt_to_grid "Link to this definition")

Energy to grid from battery \[kWh\]

Type:

_sequence_

monthly\_batt\_to\_load[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.monthly_batt_to_load "Link to this definition")

Energy to load from battery \[kWh\]

Type:

_sequence_

monthly\_batt\_to\_system\_load[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.monthly_batt_to_system_load "Link to this definition")

Energy to system loads from battery \[kWh\]

Type:

_sequence_

monthly\_crit\_load[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.monthly_crit_load "Link to this definition")

Critical load energy \[kWh\]

Type:

_sequence_

monthly\_crit\_load\_unmet[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.monthly_crit_load_unmet "Link to this definition")

Critical load energy unmet \[kWh\]

Type:

_sequence_

monthly\_crit\_load\_unmet\_percentage[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.monthly_crit_load_unmet_percentage "Link to this definition")

Critical load unmet percentage \[%\]

Type:

_sequence_

monthly\_grid\_to\_batt[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.monthly_grid_to_batt "Link to this definition")

Energy to battery from grid \[kWh\]

Type:

_sequence_

monthly\_grid\_to\_load[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.monthly_grid_to_load "Link to this definition")

Energy to load from grid \[kWh\]

Type:

_sequence_

monthly\_interconnection\_loss[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.monthly_interconnection_loss "Link to this definition")

Energy loss due to curtailment, interconnection, or outage \[kWh\]

Type:

_sequence_

monthly\_outage\_losses\_unmet[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.monthly_outage_losses_unmet "Link to this definition")

Battery and system losses unmet energy \[kWh\]

Type:

_sequence_

monthly\_system\_to\_batt[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.monthly_system_to_batt "Link to this definition")

Energy to battery from system \[kWh\]

Type:

_sequence_

monthly\_system\_to\_grid[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.monthly_system_to_grid "Link to this definition")

Energy to grid from system \[kWh\]

Type:

_sequence_

monthly\_system\_to\_load[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.monthly_system_to_load "Link to this definition")

Energy to load from system \[kWh\]

Type:

_sequence_

num\_ts\_load\_met\_by\_system\_lifetime[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.num_ts_load_met_by_system_lifetime "Link to this definition")

Number of timesteps electric load met by system (lifetime)

Type:

_float_

num\_ts\_load\_met\_by\_system\_yr1[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.num_ts_load_met_by_system_yr1 "Link to this definition")

Number of timesteps electric load met by system (year 1)

Type:

_float_

outage\_durations[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.outage_durations "Link to this definition")

Hours of autonomy during grid outage hour list from min to max \[hr\]

Type:

_sequence_

outage\_losses\_unmet[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.outage_losses_unmet "Link to this definition")

Battery and system losses unmet in this timestep \[kW\]

Type:

_sequence_

pdf\_of\_surviving[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.pdf_of_surviving "Link to this definition")

Hours of autonomy during grid outage probabilities

Type:

_sequence_

percent\_ts\_load\_met\_by\_system\_lifetime[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.percent_ts_load_met_by_system_lifetime "Link to this definition")

Percent of timesteps electric load met by system (lifetime)

Type:

_float_

percent\_ts\_load\_met\_by\_system\_yr1[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.percent_ts_load_met_by_system_yr1 "Link to this definition")

Percent of timesteps electric load met by system (year 1)

Type:

_float_

resilience\_hrs[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.resilience_hrs "Link to this definition")

Hours of autonomy during grid outage at each timestep \[hr\]

Type:

_sequence_

resilience\_hrs\_avg[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.resilience_hrs_avg "Link to this definition")

Hours of autonomy during grid outage average \[hr\]

Type:

_float_

resilience\_hrs\_max[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.resilience_hrs_max "Link to this definition")

Hours of autonomy during grid outage maximum \[hr\]

Type:

_float_

resilience\_hrs\_min[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.resilience_hrs_min "Link to this definition")

Hours of autonomy during grid outage minimum \[hr\]

Type:

_float_

survival\_function[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.survival_function "Link to this definition")

Hours of autonomy during grid outage survival function

Type:

_sequence_

system\_to\_batt[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.system_to_batt "Link to this definition")

Electricity to battery from system AC \[kW\]

Type:

_sequence_

system\_to\_batt\_dc[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.system_to_batt_dc "Link to this definition")

Electricity to battery from system DC \[kW\]

Type:

_sequence_

system\_to\_grid[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.system_to_grid "Link to this definition")

Electricity to grid from system AC \[kW\]

Type:

_sequence_

system\_to\_load[](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html#PySAM.Battery.Battery.Outputs.system_to_load "Link to this definition")

Electricity to load from system AC \[kW\]

Type:

_sequence_