# How OpenSolar Models Battery Energy Storage – OpenSolar

![](https://secure.gravatar.com/avatar/3e1d355512636ef2752e22dc44832575?default=https%3A%2F%2Fassets.zendesk.com%2Fhc%2Fassets%2Fdefault_avatar.png&r=g)

[Follow](https://support.opensolar.com/hc/en-us/articles/12382460685455-How-OpenSolar-Models-Battery-Energy-Storage/subscription.html "Opens a sign-in dialog")

### Summary:

OpenSolar models battery behavior with high granularity, simulating battery activity **hour-by-hour** across the entire year. This includes tracking **usable capacity**, **charging/discharging behavior**, **efficiency losses**, and **lifetime degradation**. Battery performance in OpenSolar is influenced by four key configuration areas:

1.  **Battery Specifications** (efficiency, degradation, charge/discharge limits)
    
2.  **Battery Control Scheme** (logic for when/how to charge/discharge)
    
3.  **DC vs AC Coupling** (impact on PV oversizing potential)
    
4.  **Load Offsettable Settings** (portion of load the battery can offset)
    

This article explains each factor in detail, followed by how OpenSolar simulates energy flow and optimizes for customer savings.

## Overview of How OpenSolar Models a Battery

OpenSolar models the battery state for every hour of the simulation, keeping track of its current capacity and lifetime throughput.

There are four key areas of input to OpenSolar that determines how a battery will be modelled:

1.  The **Battery Specifications** which can you view in _Control > Design & Hardware > Batteries_ > Edit your selected battery. These specifications determines things like the maximum charge/discharge rate, the degradation profile and rate of the battery, and the efficiency of the battery.   
     
2.  The **Battery Control Scheme** which sets the logic on when the battery should charge/discharge, whether it should reserve capacity to offset load at a specific time (i.e. at peak electricity rate), and if the battery is allowed to charge/discharge to the grid. You can actually create your own battery control scheme by following this guide [here.](https://support.opensolar.com/hc/en-us/articles/12447137853071-How-to-create-and-apply-a-battery-control-scheme)  
     
3.  Whether the **battery is DC-connected or AC-connected** (i.e. DC-coupled vs AC-coupled battery) for PV oversizing purposes.  
     
4.  **Load-offsettable** settings which determines the portion of the load/usage that the battery can offset.

Based on the settings in the four key areas mentioned above, OpenSolar models:

1.  **The battery's Usable Capacity.** This is given by the total capacity of the battery multiplied by its maximum depth of discharge (DOD). A battery can never discharge more than its maximum DOD.  
     
2.  **The maximum charging and discharging rate of the battery.** If the excess solar energy available to charge the battery is greater than the maximum charging rate, then the battery will only be able to charge at its maximum charging rate and the remaining excess solar energy will be exported to the grid.  
     
3.  **Efficiency losses from charging and discharging the battery.** Whenever a battery is charging or discharging, the efficiency loss of energy flowing into and out of the battery is accounted for. Most battery manufacturers would provide the round-trip efficiency (![mceclip3.png](https://support.opensolar.com/hc/article_attachments/12382460685071))of the battery. OpenSolar derives a single-trip efficiency (![mceclip2.png](https://support.opensolar.com/hc/article_attachments/12382469714959)) given by the square root of the round-trip efficiency to calculate the energy flowing in and out of the battery. Since the single-trip efficiency is applied for both the in and out energy flows of the battery, the overall loss is equal to the round-trip efficiency.  
    ![mceclip0.png](https://support.opensolar.com/hc/article_attachments/12382460685199)
4.  **Degradation of the battery.** OpenSolar keeps track of the kWh throughput of the battery, which is used for calculating the degradation of the battery. As the battery degrades, the useable capacity of the battery will also decrease until the end-of-life capacity is reached.  
     
5.  **When the battery charges and discharges.** This is determined by the battery control scheme that is applied to the battery. By default the (Solar-charged (Default) battery controlled scheme is applied, which is essentially a basic load-following strategy. You can read more on Battery Control Schemes in this guide [here](https://support.opensolar.com/hc/en-us/articles/12447137853071-How-to-create-and-apply-a-battery-control-scheme).

## DC-connected vs AC-connected Battery

On the Design page in the Batteries section, if you add a battery to the system design you may notice that you can set the battery to be either DC-connected or AC-connected (i.e. DC-coupled or AC-coupled battery).

**OpenSolar can model the benefits of using a DC-connected battery for PV system oversizing.**

What this means you can size your PV system more than the general rule-of-thumb of panel capacity being no more than 33% over the size of the solar inverter. This is because DC-coupled batteries allow excess generation to be directly fed into the battery if the inverter cannot take the full output. For example, if you have a 5kW inverter and you are producing 8kW of power, 5kW of solar power can go to the inverter and the remaining 3kW can go to the battery. Oversizing does not work well with an AC-coupled battery because the 5kW solar inverter is limited to 5kW output, and the battery charging happens after the solar inverter.

## Load Offsettable Settings

On the Design page in the Batteries section, you may notice there is 2 additional fields you can set. These are **Load Offsettable (%)** and **Load Offsettable Cap (kW)**. These fields are used to set the portion of the load/usage that the battery can offset. One example of a use for this field is if the household is on 3-phase and the battery is only installed on one of the phase. The load offsettable fields allow you to set the portion of usage that is attributed to the phase that the battery is installed on, and hence the usage that the battery can offset.

|     |     |
| --- | --- |
| **Field** | **Description** |
| **Load Offsettable (%)** | The percentage of the total usage that the battery can offset. Note that this will take the percentage of the usage profile that is offsettable by the battery at any given point in time.<br><br>For example if load offsettable is set at 33.33% and there is 3kWh of usage between 1-2pm, then only 1kWh between 1-2pm can be offset. However, if at 4-5pm the total usage is 6kWh, then only 2 kWh can be offset as that is 33.33% of 6kWh. |
| **Load Offsettable Cap (kW)** | The maximum kW of usage that can be offset by the battery.<br><br>For example if the offsettable cap is set at 5kW and the usage at 1-2pm was 8kWh, then only 5kWh can be offset by the battery. |

## Default Battery Control Scheme

|     |     |
| --- | --- |
| **Battery Control Scheme** | **Description** |
| **Self-consumption**<br><br>(Also be known as load-following) | In most cases you would want to select this battery control scheme. This control scheme gets the battery to:<br><br>1.  Charge from any excess solar generation remaining after offsetting the load until the battery is full. This occurs when generation > load.<br>2.  Discharge to meet any load after self-consumption until the battery is empty. This occurs when load > generation.<br><br>Due to the logic that applies by this battery control scheme, it will be the best control scheme to maximise self-consumption with a battery. |
| **Minimize Grid Import Cost** | This battery control scheme is designed to maximize electricity bill savings of a Time-of-Use electricity bill by withholding capacity to offset the usage during peak electricity pricing.<br><br>**Note:** most cases using the "Self-consumption" control scheme will result in similar savings, since the battery discharge period generally coincides with the peak pricing periods. There are also some occasions when "Self-consumption" may have a higher bill saving than this battery logic due to the fact that the battery must withhold capacity for peak TOU periods and hence the battery may not be fully utilized to increase self-consumption. |
| **Maximize Savings** | This battery control scheme is designed to maximize customer bill savings by smartly charging/discharging the battery based on time-of-use cost of electricity, and generation and energy usage characteristics.<br><br>It achieves this by identifying optimal periods to:<br><br>*    <br>    *   Conserve energy to ensure that the usage during the highest pricing periods get offset first before prioritizing cheaper time periods.<br>    *   It will discharge the full battery capacity to the grid to try achieve energy export during time periods with favorable export rates (i.e., export rates that are greater than the peak cost of electricity).<br>    *   It will charge the battery during off-peak pricing periods (generally this would be at night-time) to ensure the battery has sufficient capacity to offset the load during the next day. The optimization is smart enough to know not to fully charge the battery to 100% capacity at night-time in order to reserve some capacity to charge from excess solar the next day.<br><br>**(For California)** This battery control scheme enables your project to take advantage of the high export rates in August/September put in place as part of the NEM 3.0 transition.<br><br>**Note:** OpenSolar does not currently validate system's battery control capabilities to optimize for favorable export rates. We recommend pros to continue using the "Self-consumption" battery control scheme if you are unsure. |
| **NZ Optimized**  <br>(New Zealand Only) | This battery control scheme is generally not optimal for most system designs and is very specific for a niche use case in New Zealand. The battery will do the following:<br><br>1.  Charge the battery from the grid between 1-5am (low electricity prices) and 3-5pm (to top up the battery before peak electricity pricing in the evening)<br>2.  Battery can ONLY charge from excess solar generation between 11am - 5pm<br>3.  All other times the battery will charge when there is excess solar generation or discharge to offset the load.<br><br>Note: Given the niche use case of this battery logic, in most scenarios it does not result in improving electricity bill savings. |

You can create your own battery control scheme if these default schemes do not fit how your installed battery operates. Please see the guide on how to do this [here](https://support.opensolar.com/hc/en-us/articles/12447137853071-How-to-create-and-apply-a-battery-control-scheme)[.](https://support.opensolar.com/hc/en-us/articles/12447137853071-How-to-create-and-apply-a-battery-control-scheme)

### Related articles

*   [How to create and apply a battery control scheme](https://support.opensolar.com/hc/en-us/related/click?data=BAh7CjobZGVzdGluYXRpb25fYXJ0aWNsZV9pZGwrCI%2FuOhNSCzoYcmVmZXJyZXJfYXJ0aWNsZV9pZGwrCI%2BsKwRDCzoLbG9jYWxlSSIKZW4tdXMGOgZFVDoIdXJsSSJXL2hjL2VuLXVzL2FydGljbGVzLzEyNDQ3MTM3ODUzMDcxLUhvdy10by1jcmVhdGUtYW5kLWFwcGx5LWEtYmF0dGVyeS1jb250cm9sLXNjaGVtZQY7CFQ6CXJhbmtpBg%3D%3D--19fde38992e352f8081af3d64b33abfbaf541284)
*   [Battery Design Assistant on OpenSolar \[UK, AU, US\]](https://support.opensolar.com/hc/en-us/related/click?data=BAh7CjobZGVzdGluYXRpb25fYXJ0aWNsZV9pZGwrCI%2FjF62rCToYcmVmZXJyZXJfYXJ0aWNsZV9pZGwrCI%2BsKwRDCzoLbG9jYWxlSSIKZW4tdXMGOgZFVDoIdXJsSSJVL2hjL2VuLXVzL2FydGljbGVzLzEwNjMyOTQ4MDgxNTUxLUJhdHRlcnktRGVzaWduLUFzc2lzdGFudC1vbi1PcGVuU29sYXItVUstQVUtVVMGOwhUOglyYW5raQc%3D--021a7b81bff6a4454e323711f2135367fc0cd1b4)
*   [How to use the MCS calculator](https://support.opensolar.com/hc/en-us/related/click?data=BAh7CjobZGVzdGluYXRpb25fYXJ0aWNsZV9pZGwrCI82E2s%2BCzoYcmVmZXJyZXJfYXJ0aWNsZV9pZGwrCI%2BsKwRDCzoLbG9jYWxlSSIKZW4tdXMGOgZFVDoIdXJsSSJEL2hjL2VuLXVzL2FydGljbGVzLzEyMzYyNzEyMjk5MTUxLUhvdy10by11c2UtdGhlLU1DUy1jYWxjdWxhdG9yBjsIVDoJcmFua2kI--4082520cd69c57ceb2440e873bfcf26b58842f5b)
*   [🇬🇧 Battery Control Schemes](https://support.opensolar.com/hc/en-us/related/click?data=BAh7CjobZGVzdGluYXRpb25fYXJ0aWNsZV9pZGwrCI8a7EGXBzoYcmVmZXJyZXJfYXJ0aWNsZV9pZGwrCI%2BsKwRDCzoLbG9jYWxlSSIKZW4tdXMGOgZFVDoIdXJsSSI%2BL2hjL2VuLXVzL2FydGljbGVzLzgzNDYyMjc0NDg0NjMtLUJhdHRlcnktQ29udHJvbC1TY2hlbWVzBjsIVDoJcmFua2kJ--1fdba6a548cb1547d93c046e2e5c72a76bdb63a3)
*   [How to Handle Expired Proposals](https://support.opensolar.com/hc/en-us/related/click?data=BAh7CjobZGVzdGluYXRpb25fYXJ0aWNsZV9pZGwrCI%2FBrQf6BzoYcmVmZXJyZXJfYXJ0aWNsZV9pZGwrCI%2BsKwRDCzoLbG9jYWxlSSIKZW4tdXMGOgZFVDoIdXJsSSJFL2hjL2VuLXVzL2FydGljbGVzLzg3NzA0NTIwNDYyMjMtSG93LXRvLUhhbmRsZS1FeHBpcmVkLVByb3Bvc2FscwY7CFQ6CXJhbmtpCg%3D%3D--d521525d94333f0eaa7405394a0e6371931974a3)