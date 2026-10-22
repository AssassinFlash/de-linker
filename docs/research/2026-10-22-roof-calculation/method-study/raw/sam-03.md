# Battery Dispatch FOM

The Battery Dispatch page displays inputs for controlling the battery dispatch, or timing of battery charging and discharging. For inputs that describe the battery's performance characteristics, see the [Battery Cell and System](https://samrepo.nlr.gov/help/battery_storage_fom.html) page.

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

### Front-of-meter (FOM) Storage Dispatch Options

The battery dispatch options determine when the battery charges and discharges. The charge options determine any limits on how the battery can charge or discharge.

#### Dispatch Options

Choose the dispatch option that most closely represents when you want the battery to charge and discharge.

Note. The list below provides a brief description of each option. To see a detailed description of each heading, click the appropriate grey and blue heading below to expand the detailed description.

Automated dispatch

Automated dispatch dispatches the battery in response to changes in the power price to maximize revenue from power sales. Use this option for PPA projects that involve time-of-delivery price multipliers or Merchant Plant projects.

PV smoothing

PV smoothing dispatches the battery for photovoltaic-battery systems to limit power ramp rates at the grid interconnection point. Use this option for projects required to meet ramp rate limits. This option is available for PV battery and Custom Generation Profile - Battery systems. It is not available for standalone batteries.

Dispatch to custom time series

Dispatch the battery according to time series charge and discharge power values you provide. Use this option when you know exactly how you want the battery to charge and discharge.

Manual dispatch

No automation. You specify the timing of battery charges and discharges manually using up to six dispatch periods and a set of weekday and weekend hourly profiles by month. Use this option when you want the battery to charge and discharge according to daily or seasonal schedules.

#### Charge Options

Choose the source of power for charging the battery. SAM enables and disables (greys out) the options as appropriate for the dispatch option and whether the battery is DC- or AC-connected.

Battery can charge from grid

Allow the grid to charge the battery.

Battery can charge from system

Allow the system to charge the battery.

Battery can charge from grid-limited system power

Allow the battery to charge from power in excess of the interconnection limit or from curtailed power when the interconnection limit is enabled and/or curtailment is specified on the [Grid Limits](https://samrepo.nlr.gov/help/grid_limits.html) page.

Battery can charge from clipped system power

For DC-connected batteries with a photovoltaic system, allow DC array power in excess of the inverter's nominal DC input power to charge the battery.