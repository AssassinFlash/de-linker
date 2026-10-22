Consumption :: PV\*SOL® help

[](https://help.valentin-software.com/pvsol/en/pages/consumption/#)[PV\*SOL Help](https://help.valentin-software.com/pvsol/en/) > [Pages](https://help.valentin-software.com/pvsol/en/pages/) > Consumption

# Consumption

[![](/pvsol/images/navigationsseiten/verbrauch/page_verbrauch.en.png)](https://help.valentin-software.com/pvsol/images/navigationsseiten/verbrauch/page_verbrauch.en.png)

#### Page Consumption

On the page ![](/pvsol/images/navigationsseiten/icon_verbrauch.png) _Consumption_ a consumption profile will be created, which is to be covered by the PV system.

A created profile can be copied to the clipboard in two different ways. A right click on the diagram opens a selection window in which you can copy the diagram either as an image or the monthly totals as raw data in table form.

[![](/pvsol/images/navigationsseiten/verbrauch/screen_rechtsklick.en.png)](https://help.valentin-software.com/pvsol/images/navigationsseiten/verbrauch/screen_rechtsklick.en.png)

The button ![](/pvsol/images/buttons/btn_neuerVerbraucher2.en.png) opens a dialogue with the following options:

*   Load profiles / Individual appliances
*   Monthly/annual consumption for net metering (only for grid-connected PV systems)
*   Surplus consumption

## Load profiles / Individual appliances

In the dialog _Load profiles / Individual appliances_ a wide variety of combinations of different electrical consumers can be combined to form a consumption profile. There are three ways to determine the consumption.

[![](/pvsol/images/navigationsseiten/verbrauch/page_VerbrauchDefinieren.en.png)](https://help.valentin-software.com/pvsol/images/navigationsseiten/verbrauch/page_VerbrauchDefinieren.en.png)

#### Define consumption

The consumption can be defined

1.  via measured consumers,
2.  via a load profile
3.  or from the sum of pre-defined individual appliances

### Measured appliances

[![](/pvsol/images/navigationsseiten/verbrauch/page_GemessenerVerbraucher.en.png)](https://help.valentin-software.com/pvsol/images/navigationsseiten/verbrauch/page_GemessenerVerbraucher.en.png)

#### Measured consumer

Under the heading _Measured consumers_, electrical consumers can be defined using load profiles already imported. The database contains a large number of relevant load profiles (area 2). Area 3 shows more detailed information about the selected load profile. There, the energy consumption of the load profile can also be adapted to the actual energy consumption. The adjustment does not affect the original load profile. The options provided in area 1 allow you to import and delete new load profiles.

#### Import load profile

[![](/pvsol/images/navigationsseiten/verbrauch/page_lastprofil_importieren.en.png)](https://help.valentin-software.com/pvsol/images/navigationsseiten/verbrauch/page_lastprofil_importieren.en.png)

#### Import load profile

Procedure for importing new load profiles:

1.  Open the dialog _Import Load Profiles_ by clicking on the ![](/pvsol/images/buttons/btn_neuerVerbraucher.de.png) button in the dialogue _Load and import load profile_
    
2.  Define the Name of the load profile.
    
3.  (optional) Comment on the load profile, for example, by specifying the application areas of the load profile to be imported.
    
4.  Enter the time interval (in minutes) of the data to be imported. All components dependent on the loads (battery system control, feed-in control, mains etc.) are simulated in the resolution specified there. Everything that does not depend on it (e.g. the dependence on the climate) is simulated with a resolution of 1h (unless otherwise specified).
    
5.  Select the number of available days. Complete annual data sets can be imported. The number of values that the program expects in the file is displayed for your control.
    
6.  The minimum number of data points that must be available is displayed for your control.
    
7.  Select the present unit format.
    
8.  Select the used number format:
    
    *   `####.##` - Dot as decimal separator;
    *   `####,##` - Comma as decimal separator;
    *   `#.####,##` - Comma as decimal separator and dot as thousand separator.
9.  Use ![](/pvsol/images/buttons/btn_oeffnen.png) to select the file or load profile you want to import. The file must be a text file in `*.txt` or `*.csv` format and must consist of a column with values, without header line.
    
10.  Via the button ![](/pvsol/images/buttons/btn_werteEinlesen.en.png) the selected load profile is imported.
     
11.  If a short-term profile was selected for the number of days, the ![](/pvsol/images/buttons/btn_einsweiter.png) button appears at the end of the dialogue. If you select this, a new dialogue window opens.
     
12.  In the new dialogue window, the missing months can be estimated with a percentage value.
     

[![](/pvsol/images/navigationsseiten/verbrauch/page_extrapolation.de.png)](https://help.valentin-software.com/pvsol/images/navigationsseiten/verbrauch/page_extrapolation.de.png)

#### Extrapolation of the short-term profile

### Load profiles (from day profiles)

[![](/pvsol/images/navigationsseiten/verbrauch/page_verbraucherMitLastprofil.en.png)](https://help.valentin-software.com/pvsol/images/navigationsseiten/verbrauch/page_verbraucherMitLastprofil.en.png)

#### Consumer with load profile

In the view _consumer with load profile_ different load profiles can be loaded and individually adjusted. With the button ![](/pvsol/images/buttons/btn_neuerVerbraucher.de.png) new consumers can be created. A click on this button opens the dialog _Generate new load profile_. A consumer can be edited using the button ![](/pvsol/images/buttons/btn_bearbeiten3.en.png) . This option is only available for self-generated consumers.

[![](/pvsol/images/navigationsseiten/verbrauch/page_neues_lastprofil_generieren.en.png)](https://help.valentin-software.com/pvsol/images/navigationsseiten/verbrauch/page_neues_lastprofil_generieren.en.png)

#### Create new load profile

To define an electrical consumer, proceed as follows:

1.  Enter a Description.
2.  In the option selection you can define periodic behavior of the consumption profile.
    *   If the consumption depends on the day of the week, this can be taken into account by activating the option ![](/pvsol/images/navigationsseiten/verbrauch/screen_tagesverlaeufe_unterschiedlich.de.png) .
    *   If there are differences between the seasons, this can be taken into account by activating the option ![](/pvsol/images/navigationsseiten/verbrauch/screen_jahreszeiten_unterschiedlich.de.png)
    

```
* If the consumption differs on the respective weekdays, this can be selected by activating the option 


  
    
  
.
* If a vacation consumption is known, it can be defined in the dialog 


  
    
  
. The length of the holiday period can also be entered there
```

1.  Depending on which options you have selected, the corresponding tabs are created. Values can be entered in each table. The values are normalized to 100% when you click OK. The daily or yearly course is shown in the diagram. The diagram and the table values can be copied by right clicking on the diagram.

### Individual appliances

[![](/pvsol/images/navigationsseiten/verbrauch/page_einzelVerbraucher1.en.png)](https://help.valentin-software.com/pvsol/images/navigationsseiten/verbrauch/page_einzelVerbraucher1.en.png)

#### Definition of electrical consumption

In this dialogue, the energy requirements will be defined. A new individual appliance can be created using the button ![](/pvsol/images/buttons/btn_neuerVerbraucher.de.png) . A click opens the dialog _New individual appliance_. If the appliance is a self-generated record, it can be deleted via ![](/pvsol/images/buttons/btn_loeschen4.de.png) . An already defined individual appliance can be edited with the button ![](/pvsol/images/buttons/btn_kopieren1.de.png) .

[![](/pvsol/images/navigationsseiten/verbrauch/page_neuer_einzelverbraucher.en.png)](https://help.valentin-software.com/pvsol/images/navigationsseiten/verbrauch/page_neuer_einzelverbraucher.en.png)

#### New individual appliance

To create an individual appliance proceed as follows:

1.  Type in a name.
    
2.  Select one of four types. The following are available
    
    *   User independent appliance
    *   User dependent appliance
    *   Short time appliance
    *   Light
3.  Specify the Power and the Standby power of the device.
    
4.  Define the operating time of the device. Hourly values are determined from the input variables.
    

### Input Monthly/annual consumption

[![](/pvsol/images/navigationsseiten/verbrauch/page_netMetering.en.png)](https://help.valentin-software.com/pvsol/images/navigationsseiten/verbrauch/page_netMetering.en.png)

#### Input monthly/annual consumption

In this dialogue, you define consumption profiles on the basis of monthly and annual values.

If your net metering model shows an annual balance, enter the ![](/pvsol/images/check-checked.png) annual value of consumption, at monthly balance the ![](/pvsol/images/check-checked.png) monthly values.

The consumption profiles defined here should only be used for the profitability model Net-Metering, since only these profiles correctly represent hourly consumption. If you select Annual value, the consumption is identical for each hour of the year, for monthly values for each hour of the month.

If you want to define the hours individually, you can also enter a daily load profile for the monthly values. If the daily load profile is used, the input mask can also be used in combination with the surplus feed-in.

If different tariff times are defined in the selected Net-Metering tariff or Feed-in tariff, the Net-Metering tariff must first be selected on the page [Economy](https://help.valentin-software.com/pvsol/en/pages/financial-analysis/) because the consumption is entered separately for each tariff time.

### Surplus consumption

[![](/pvsol/images/navigationsseiten/verbrauch/page_ueberschussverbraucher.en.png)](https://help.valentin-software.com/pvsol/images/navigationsseiten/verbrauch/page_ueberschussverbraucher.en.png)

#### Surplus consumption

There are two types of surplus consumption: fixed or dynamic.  
In the case of fixed surplus consumption, it is only counted as consumption if the grid feed-in exceeds the value of the maximum power specified in the dialogue.  
In the case of dynamic surplus consumption, consumption already starts when the grid feed-in exceeds the value of the minimum power. The consumption is limited by the maximum value “maximum power”, this value is not exceeded.

### Load shedding

[![](/pvsol/images/navigationsseiten/verbrauch/page_lastabwurf.en.png)](https://help.valentin-software.com/pvsol/images/navigationsseiten/verbrauch/page_lastabwurf.en.png)

#### Load shedding

In off-grid PV systems, load shedding allows the loads to be switched on and off depending on the battery charge status and time window. A start threshold and a stop threshold can be assigned for two time windows (**time T1**, **time T2**) for switching the load according to battery charge state (SOC = state of charge). When the start threshold is reached, the load is switched off and switched on again when the stop threshold is reached. You can use the time windows to display various day and night behaviors, for example. The entries are illustrated in the graphic.

* * *

See also

*   [Calculation > Consumption](https://help.valentin-software.com/pvsol/en/calculation/consumption/)