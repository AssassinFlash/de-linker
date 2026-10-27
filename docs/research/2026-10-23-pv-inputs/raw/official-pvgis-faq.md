Frequently Asked Questions - Joint Research Centre - European Commission [Skip to main content](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/general-information/frequently-asked-questions_en#main-content)

[![European Commission logo](/themes/contrib/oe_theme/dist/ec/images/logo/logo-ec--mute.svg)](https://commission.europa.eu/index_en)

[en](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/general-information/frequently-asked-questions_en)

Search

Search

Joint Research Centre

# Frequently Asked Questions

## Why doesn't PVGIS work? or PVGIS doesn't let me make a calculation!

In 99% of the cases, PVGIS actually works just fine. If PVGIS doesn't allow you to make a calculation because the visualize or download buttons don't work, it is almost always because you have not chosen the location for which you want to make the calculation. You can choose the location by:

*   Clicking on the map
*   Entering an address (or country or city name)
*   Typing in latitude and longitude coordinates

## Where do I enter the PV module efficiency?, and/or, where do I enter the module area?

In PVGIS you should enter the _nominal power_ of the PV system (a.k.a. _peak power_ or _rated power_). If you know the nominal power of your system, you don't need to know the efficiency, except to calculate the area of the modules. This is why:

The nominal power or _peak power_ is the power claimed by the manufacturer of the module or system. It is the power output of the module(s) measured at 1000 W/m2 solar irradiance (and a module temperature of 25° C and a solar spectrum corresponding to an air mass of 1.5. These conditions are known as _Standard Test Conditions_ (STC)). This means that if your modules were 100% efficient, you would need 1 m2 to get a system with a peak power of 1 kW.

Since the modules are NOT 100% efficient you need a bigger area. If you have 10% efficient modules you will need 10 m2 to have a 1 kWp system. We will call the module efficiency at Standard Test Conditions as _effnom_.

In other words, if _Ppk_ is the nominal power and _A_ the area of the module(s), we have

_Ppk\= A\*effnom_ (1)

## The different PV losses do not add up!

We calculate the losses as _multiplicative_. For instance: if the angle-of-incidence losses are 3.7% and the temperature/irradiance losses are 7.2%, then we first lose 3.7% reflected away at the surface and then we lose 7.2% **of the rest** of the energy because of high temperature or low irradiance. Finally the system losses may be 14% which is calculated on what is left after the temperature/irradiance losses. The total loss will then be 100\*(1-(1-0.037)\*(1-0.072)\*(1-0.14))=23.1%.

## What methods are used for the PVGIS calculations?

We often receive questions about the methods used to calculate the PV output or the solar radiation data that PVGIS provides. The following page describes all the methods:

[Data sources & calculation methods](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/general-information/data-sources-calculation-methods_en)

Introduction to solar radiationThe solar radiation that reaches the top of the atmosphere on a perpendicular plane to the rays, known as solar...

## Do the PVGIS calculations take into account the effect of clouds?

Yes, PVGIS uses solar radiation data based on satellite images which are used to identify the presence and the thickness of clouds. A short overview of these methods is found in the page about methods.