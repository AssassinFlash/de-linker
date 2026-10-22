# Battery Dispatch BTM

The Battery Dispatch page for behind-the-meter (BTM) batteries displays inputs for controlling the timing of battery charging and discharging. For inputs that describe the battery's performance characteristics, see the [Battery Cell and System](https://samrepo.nlr.gov/help/battery_storage_btm.html) page.

### Charge Limits and Priority

The Charge Limits and Priority inputs are constraints on the battery dispatch calculations.

The limits on minimum and maximum state of charge affect both the amount of energy available for battery dispatch calculations, and the depth of charge-discharge cycles for battery life calculations. Choose values appropriate for the type of battery you are modeling. The default values state of charge range of 15% to 95% is reasonable for most Li-ion battery types.

Minimum state of charge, %

A limit on the quantity of energy that can be drained from the battery as a percentage of available capacity. For example, a value of 15% would prevent the battery from discharging below 15% of the battery's available capacity in a given time step.

Note. The minimum and maximum state of charge are both as a percentage of available battery capacity, which changes over time as the batteries degrade and are replaced. The available capacity in a given time step is likely to be less than the battery's nominal capacity shown on the Battery Cell and System page.

Maximum state of charge, %

A limit on the quantity of energy that can be sent to the battery as a percentage of available capacity. For example a value of 95% would prevent the battery from charging above 95% state of charge.

Initial state of charge, %

The state of charge of the battery at the beginning of the simulation. A value of 100% would be for a fully charged battery, 0% would be for a fully discharged battery.

Minimum time at charge state, min

There may be periods of time where the photovoltaic or other power system output varies above and below the load causing rapid cycling of the battery. Rapid cycling may also result for dispatch options that respond to power prices when prices change rapidly from time step to time step. This kind of cycling, especially if the cycles are deep, may degrade battery performance over time. The minimum time at charge state prevents the battery from changing between charging and discharging within the number of minutes that you specify.

Note. The minimum time at charge state only applies when the simulation time step is smaller than the minimum time at charge state. For example, the default value of 10 minutes would only apply for 5-minute or 1-minute simulation time steps; It has no effect for hourly simulations.

### Behind-the-meter (BTM) Storage Dispatch Options

The battery dispatch options determine when the battery charges and discharges. The charge options determine any limits on how the battery can charge or discharge.

#### Dispatch Options

Choose the dispatch option that most closely represents when you want the battery to charge and discharge.

Notes.  
   
The list below provides a brief description of each option. To see a detailed description of each heading, click the appropriate grey and blue heading below to expand the detailed description.  
   
If you are modeling [grid outages](https://samrepo.nlr.gov/help/grid_outage.html) to calculate resiliency metrics, during an outage the battery switches to a special dispatch mode that prioritizes meeting the load, regardless of the dispatch option you choose.

Peak shaving

Dispatch the battery to reduce peak demand. Use this option when the electricity rate structure includes energy rates with kWh/kW units or demand charges and you want to use the battery to reduce billing demand.

Input grid power targets

Dispatch the battery in response to time series grid power target data you provide to ensure the power from the grid is at or below the target power levels.

Input battery power targets

Dispatch the battery according to time series charge and discharge power values you provide. Use this option when you know exactly how you want the battery to charge and discharge.

Manual dispatch

Dispatch the battery based on month-by-hour weekday and weekend schedules you provide. Use this option to dispatch the battery in response to time-of-use electricity rates.

Retail rate dispatch

Dispatch the battery to minimize the energy and demand charge portions of the monthly electricity bill.

Self-consumption

Dispatch the battery to minimize power to and from the grid.

#### Charge Options

The charge options control how the battery can charge and discharge. SAM enables and disables (greys out) the options as appropriate for the dispatch option and whether the battery is DC- or AC-connected.

Battery can charge from grid

Allow power from the grid to charge the battery.

Battery can charge from system

Allow the photovoltaic array or other power system to charge the battery.

Battery can charge from grid-limited system power

Allow the battery to charge from power in excess of the interconnection limit or from curtailed power when the interconnection limit is enabled and/or curtailment is specified on the [Grid Limits](https://samrepo.nlr.gov/help/grid_limits.html) page.

Battery can charge from clipped system power

For a photovoltaic array with DC-connected battery, allow the photovoltaic array to charge the battery when the array DC power exceeds the inverter nominal DC input power.

Battery can discharge to grid

Allow the battery to discharge to the grid.

Charge from system only when system output exceeds load

Allow the photovoltaic array or other power system to charge the battery only when the system AC output is greater than  the load.

Discharge battery only when load exceeds system output

Allow the battery to discharge only when the load is greater than the photovoltaic or other power system AC output.

Battery can charge from fuel cell

For system with fuel cells, allow the battery to charge from the fuel cell. (This option is only visible for fuel cell configurations.)