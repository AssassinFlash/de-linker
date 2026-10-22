# Peak shaving with increased self-consumption (multiuse)

In projects with self-consumption and in energy system projects, the "multiuse" function can be used to optimize the inverter behavior for power exchange at the grid point of interconnection. In the process the "peak shaving" function and increased self-consumption are combined to further reduce the energy costs.

The "multi-use" function divides the useful range of the battery area of use into 2 sections:

*   Section below the SOC limiting value  
    If the battery state of charge is below the limiting value, the battery is used for peak shaving.  
    To do this, the battery-storage system is discharged in this range if the grid-supplied power exceeds the specified grid-supply limit. The battery is charged from the utility grid or with surplus PV energy if the feed-in power is higher than the specified feed-in limit.  
    If the battery is charged with energy drawn from the utility grid, a negative value must be entered for the load limit.  
    **Example:** If the peak load must be limited above 50 kW and the battery must be charged below 50 kW, 50 kW must be entered as the grid-supply limit and -50 kW as the load limit.
    
*   Section above the SOC limiting value  
    If the state of charge of the battery is above the limiting value, self-consumption must preferably be optimized.  
    To do so, the battery-storage system is discharged in this range to limit the utility grid-supplied power to the specified maximum value. As a rule, this is 0 kW. The battery is typically charged using excess PV energy. In the case of increased self-consumption, the battery-storage system can be discharged up to the specified SOC limiting value. If the battery is not charged with energy drawn from the utility grid, 0 kW must be entered for the feed-in limit.