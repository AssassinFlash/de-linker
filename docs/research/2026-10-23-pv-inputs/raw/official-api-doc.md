# API non-interactive service - Joint Research Centre

## 1 Basics

### 1.1 Entry points

All the PVGIS tools can be accessed non-interactively using our web APIs. The entry points are:

PVGIS 5.3: [https://re.jrc.ec.europa.eu/api/v5\_3/tool\_name?param1=value1&param2=value2&...](https://re.jrc.ec.europa.eu/api/v5_1/tool_name?param1=value1&param2=value2&...)

PVGIS 5.2: [https://re.jrc.ec.europa.eu/api/v5\_2/tool\_name?param1=value1&param2=value2&...](https://re.jrc.ec.europa.eu/api/v5_2/tool_name?param1=value1&param2=value2&...)

NB From 25 September 2024 the old entrypoint [https://re.jrc.ec.europa.eu/api/tool\_name?param1=value1&param2=value2&...](https://re.jrc.ec.europa.eu/api/tool_name?param1=value1&param2=value2&...)   will serve PVGIS 5.2 for a limited period. Access to PVGIS 5.1 has been removed

The variables are:

*   _tool\_name: PVcalc, SHScalc, MRcalc, DRcalc, seriescalc, tmy, printhorizon._
*   _param1=value1, param2=value2, ...:_ input parameters of the tool with their corresponding values concatenated in a query string format.

PVGIS APIs can be called directly using different languages like Python, NodeJS, Perl, Java and many others. Such languages have libraries to ease API calls management. Please, for more information check the documentation of the specific language used.

**Warning**: access to PVGIS APIs via AJAX is not allowed. Please, do not ask for changes in our CORS policy since these requests will be rejected by the system administrators.

When you report an error, please always specify the exact URL, the parameters used, the exact error text and the exact version of software/libraries you are using and any other information that may help us find and fix the problem.

### 1.2 HTTP methods allowed

API functions accept GET method only. Other methods will return an HTTP status "405 - Method not allowed". HEAD method has been kept only to confirm the existence of the desired API function, but will return a "204 - No Content" HTTP status to avoid wasting CPU computation time.

### 1.3 API calls rate limit

API calls have a rate limit of **30 calls/second per IP address**. If you exceed this threshold, the service will refuse your call and return a "429 - Too Many Requests" HTTP status.

### 1.4 Simultaneous computations tasks limit

To avoid server slowdowns due to too many simultaneous computations tasks, we introduced a new mechanism to handle excessive requests that affect the service availability.

All the exceeding computation requests that are outside the optimal computation frame, will be suspended for 150/200 milliseconds before a new try, waiting for just released resource. The number of tries are limited to a cap of 4/5 seconds, and after that limit the service will return a "529 - Site is overloaded" HTTP status code.

This status code is used to tell you that you should repeat the request after a while.

### 1.5 Inputs

*   If any of the inputs is out of the expected range, a json error message will be returned specifying the range of expected values for that input.
*   The query string must include at least all the mandatory inputs of the app (see minimal usage examples). The default values will be used for undefined optional parameters.
*   Inputs not required by the tool will be deprecated.

### 1.6 Outputs

The outputs obtained with the non-interactive service are exactly the same as those obtained with the PVGIS interface. The output type is controlled with the following two parameters:

*   _**outputformat**_:
    *   _outputformat=csv_ CSV output.
    *   _outputformat=json_ JSON output.
    *   _outputformat=basic_ Raw CSV output without metadata.
    *   _outputformat=epw_ Energy Plus EPW file (only for the TMY tool).
*   _**browser**_:
    *   _browser=0_ Output as a stream.
    *   _browser=1_ Output as a file.

We encourage users to use the JSON output for integrating PVGIS results in other web services and scripts. This will reduce potential impacts of future PVGIS upgrades in their services.

## 2 Inputs for specific PVGIS tools

### 2.1 Grid-connected & tracking PV systems

Inputs

| Name | Type\* | Obligatory | Default | Comments |
| --- | --- | --- | --- | --- |
| lat | F   | Yes | \-  | Latitude, in decimal degrees, south is negative. |
| lon | F   | Yes | \-  | Longitude, in decimal degrees, west is negative. |
| usehorizon | I   | No  | 1   | Calculate taking into account shadows from high horizon. Value of 1 for "yes". |
| userhorizon | L   | No  | \-  | Height of the horizon at equidistant directions around the point of interest, in degrees. Starting at north and moving clockwise. The series '0,10,20,30,40,15,25,5' would mean the horizon height is 0° due north, 10° for north-east, 20° for east, 30° for south-east, etc. |
| raddatabase | T   | No  | [default DB](https://ec.europa.eu/jrc/en/pvgis/docs/usermanual#fig:default_db) | Name of the radiation database. "PVGIS-SARAH3" for Europe, Africa and Asia or "PVGIS-NSRDB" for the Americas between 60°N and 20°S, "PVGIS-ERA5" . NB  "PVGIS-COSMO" and "PVGIS-CMSAF" have been deprecated), while PVGIS-NSRDB is only available with PVGIS 5.2 |
| peakpower | F   | Yes | \-  | Nominal power of the PV system, in kW. |
| pvtechchoice | T   | No  | "crystSi" | PV technology. Choices are: "crystSi", "crystSi2025", "CIS", "CdTe" and "Unknown". |
| mountingplace | T   | No  | "free" | Type of mounting of the PV modules. Choices are: "free" for free-standing and "building" for building-integrated. |
| loss | F   | Yes | \-  | Sum of system losses, in percent. |
| fixed | I   | No  | 1   | Calculate a fixed mounted system. Value of 0 for "no". All other values (or no value) mean "Yes". Note that this means the default is "yes". |
| angle | F   | No  | 0   | Inclination angle from horizontal plane of the (fixed) PV system. |
| aspect | F   | No  | 0   | Orientation (azimuth) angle of the (fixed) PV system, 0=south, 90=west, -90=east. |
| optimalinclination | I   | No  | 0   | Calculate the optimum inclination angle. Value of 1 for "yes". All other values (or no value) mean "no". |
| optimalangles | I   | No  | 0   | Calculate the optimum inclination AND orientation angles. Value of 1 for "yes". All other values (or no value) mean "no". |
| inclined\_axis | I   | No  | 0   | Calculate a single inclined axis system. Value of 1 for "yes". All other values (or no value) mean "no". |
| inclined\_optimum | I   | No  | 0   | Calculate optimum angle for a single inclined axis system. Value of 1 for "yes". All other values (or no value) mean "no". |
| inclinedaxisangle | F   | No  | 0   | Inclination angle for a single inclined axis system. Ignored if the optimum angle should be calculated (parameter "inclined\_optimum"). |
| vertical\_axis | I   | No  | 0   | Calculate a single vertical axis system. Value of 1 for "yes". All other values (or no value) mean "no". |
| vertical\_optimum | I   | No  | 0   | Calculate optimum angle for a single vertical axis system. Value of 1 for "yes". All other values (or no value) mean "no". |
| verticalaxisangle | F   | No  | 0   | Inclination angle for a single vertical axis system. Ignored if the optimum angle should be calculated (parameter "vertical\_optimum" set to 1). |
| twoaxis | I   | No  | 0   | Calculate a two axis tracking system. Value of 1 for "yes". All other values (or no value) mean "no". |
| pvprice | I   | No  | 0   | Calculate the PV electricity price \[kwh/year\] in the currency introduced by the user for the system cost. |
| systemcost | F   | if pvprice | \-  | Total cost of installing the PV system \[your currency\]. |
| interest | F   | if pvprice | \-  | Interest in %/year |
| lifetime | I   | No  | 25  | Expected lifetime of the PV system in years. |
| outputformat | T   | No  | "csv" | Type of output. Choices are: "csv" for the normal csv output with text explanations, "basic" to get only the data output with no text, and "json". |
| browser | I   | No  | 0   | Use this with a value of "1" if you access the web service from a web browser and want to save the data to a file. |

\* F = Floating point number; I = integer number; L = list of numbers; T= text string.

Example of the minimum usage:

[https://re.jrc.ec.europa.eu/api/PVcalc?lat=45&lon=8&peakpower=1&loss=14](https://re.jrc.ec.europa.eu/api/PVcalc?lat=45&lon=8&peakpower=1&loss=14)

*   For the fixed PV system, if the parameter "_optimalinclination_" is selected (set to 1), the value defined for the "_angle_" parameter is ignored. Similarly, if "_optimalangles_" is set to 1, values defined for "_angle_" and "_aspect_" are ignored and therefore are not necessary. In this case, parameter "_optimalinclination_" would not be necessary either.
*   For the inclined axis PV system analysis, the parameter "_inclined\_axis_" must be selected, along with either "_inclinedaxisangle_" or "_inclined\_optimum_". If parameter "_inclined\_optimum_" is selected, the inclination angle defined in "_inclinedaxisangle_" is ignored, so this parameter would not be necessary.
*   Parameters regarding the vertical axis ("_vertical\_axis_", "_vertical\_optimum_" and "_verticalaxisangle_") are related in the same way as the parameters used for the inclined axis PV system.

### 2.2 Off-grid PV systems

inputs

| Name | Type\* | Obligatory | Default | Comments |     |
| --- | --- | --- | --- | --- | --- |
| lat | F   | Yes | \-  | Latitude, in decimal degrees, south is negative. |     |
| lon | F   | Yes | \-  | Longitude, in decimal degrees, west is negative. |     |
| usehorizon | I   | No  | 1   | Calculate taking into account shadows from high horizon. Value of 1 for "yes". |     |
| userhorizon | L   | No  | \-  | Height of the horizon at equidistant directions around the point of interest, in degrees. Starting at north and moving clockwise. The series '0,10,20,30,40,15,25,5' would mean the horizon height is 0° due north, 10° for north-east, 20° for east, 30° for south-east, etc. |     |
| raddatabase | T   | No  | [default DB](https://ec.europa.eu/jrc/en/pvgis/docs/usermanual#fig:default_db) | Name of the radiation database. "PVGIS-SARAH" for Europe, Africa and Asia or "PVGIS-NSRDB" for the Americas between 60°N and 20°S, "PVGIS-ERA5" and "PVGIS-COSMO" for Europe (including high-latitudes), and "PVGIS-CMSAF" for Europe and Africa (will be deprecated) |     |
| peakpower | F   | Yes | \-  | Nominal power of the PV system, in W. |     |
| angle | F   | No  | 0   | Inclination angle from horizontal plane of the (fixed) PV system. |     |
| aspect | F   | No  | 0   | Orientation (azimuth) angle of the (fixed) PV system, 0=south, 90=west, -90=east. |     |
| batterysize | F   | Yes | \-  | This is the size, or energy capacity, of the battery used in the off-grid system, measured in watt-hours (Wh). |     |
| cutoff | F   | Yes | \-  | Batteries cutoff in %. The cutoff is imposed so that the battery charge cannot go below a certain percentage of full charge. |     |
| consumptionday | F   | Yes | \-  | Energy consumption of all the electrical equipment connected to the system during a 24 hour period (Wh) |     |
| hourconsumption | L   | No  | \-  | List of 24 comma separated values with the hourly consumption. The values in the file should be the _fraction_ of the daily consumption that takes place in each hour, with the sum of the numbers equal to 1. The daily consumption profile should be defined for the standard local time, without consideration of daylight saving offsets if relevant to the location. The format is the same as the [default consumption file](https://re.jrc.ec.europa.eu/pvg_download/hourconsumption_norm.csv). |     |
| outputformat | T   | No  | "csv" | Type of output. Choices are: "csv" for the normal csv output with text explanations, "basic" to get only the data output with no text, and "json". |     |
| browser | I   | No  | 0   | Use this with a value of "1" if you access the web service from a web browser and want to save the data to a file. |     |

\* F = Floating point number; I = integer number; L = list of numbers; T= text string.

Example of the minimum usage:

[https://re.jrc.ec.europa.eu/api/SHScalc?lat=45&lon=8&peakpower=10&batterysize=50&consumptionday=200&cutoff=40](https://re.jrc.ec.europa.eu/api/SHScalc?lat=45&lon=8&peakpower=10&batterysize=50&consumptionday=200&cutoff=40)

### 2.3 Monthly radiation

Inputs

| Name | Type\* | Obligatory | Default | Comments |
| --- | --- | --- | --- | --- |
| _lat_ | F   | Yes | \-  | Latitude, in decimal degrees, south is negative. |
| _lon_ | F   | Yes | \-  | Longitude, in decimal degrees, west is negative. |
| _usehorizon_ | I   | No  | 1   | Calculate taking into account shadows from high horizon. Value of 1 for "yes". |
| _userhorizon_ | L   | No  | \-  | Height of the horizon at equidistant directions around the point of interest, in degrees. Starting at north and moving clockwise. The series '0,10,20,30,40,15,25,5' would mean the horizon height is 0° due north, 10° for north-east, 20° for east, 30° for south-east, etc. |
| _raddatabase_ | T   | No  | [default DB](https://ec.europa.eu/jrc/en/pvgis/docs/usermanual#tab:db-years) | Name of the radiation database (DB): "PVGIS-SARAH" for Europe, Africa and Asia or "PVGIS-NSRDB" for the Americas between 60°N and 20°S, "PVGIS-ERA5" and "PVGIS-COSMO" for Europe (including high-latitudes), and "PVGIS-CMSAF" for Europe and Africa (will be deprecated). The default DBs are PVGIS-SARAH, PVGIS-NSRDB and PVGIS-ERA5 based on the chosen location (see Figure xx). |
| _startyear_ | I   | No  | year\_min(DB) | First year of the output of monthly averages. Availability varies with the [temporal coverage](https://ec.europa.eu/jrc/en/pvgis/docs/usermanual#tab:db-years) of the radiation DB chosen. The default value is the first year of the DB. |
| _endyear_ | I   | No  | year\_max(DB) | Final year of the output of monthly averages. Availability varies with the [temporal coverage](https://ec.europa.eu/jrc/en/pvgis/docs/usermanual#tab:db-years) of the radiation DB chosen. The default value is the last year of the DB. |
| _horirrad_ | I   | No  | 0   | Output horizontal plane irradiation. Value of 1 for "yes". All other values (or no value) mean "no". |
| _optrad_ | I   | No  | 0   | Output annual optimal angle plane irradiation. Value of 1 for "yes". All other values (or no value) mean "no". |
| _selectrad_ | I   | No  | 0   | Output irradiation on plane of selected inclination. Value of 1 for "yes". All other values (or no value) mean "no". |
| _angle_ | F   | No  | 0   | Inclinatio<br><br>Example of the minimum usage:<br><br>n angle for the selected inclination irradiation option. |
| _mr\_dni_ | I   | No  | 0   | Output direct normal irradiation. Value of 1 for "yes". All other values (or no value) mean "no". |
| _d2g_ | I   | No  | 0   | Output monthly values of the ratio of diffuse to global radiation (horizontal plane). Value of 1 for "yes". All other values (or no value) mean "no". |
| _avtemp_ | I   | No  | 0   | Output monthly average values of daily (24h) temperature. Value of 1 for "yes". All other values (or no value) mean "no". |
| _outputformat_ | T   | No  | "csv" | Type of output. Choices are: "csv" for the normal csv output with text explanations, "basic" to get only the data output with no text, and "json". |
| _browser_ | I   | No  | 0   | Use this with a value of "1" if you access the web service from a web browser and want to save the data to a file. |

\* F = Floating point number; I = integer number; L = list of numbers; T= text string.

\[/collapsed title\]

Example of the minimum usage:

[https://re.jrc.ec.europa.eu/api/MRcalc?lat=45&lon=8&horirrad=1](https://re.jrc.ec.europa.eu/api/MRcalc?lat=45&lon=8&horirrad=1)

*   At least one output option should be chosen (_horirrad_, _optrad_, _selectrad_, etc). Otherwise the output table will not have any values.

### 2.4 Daily radiation

\[collapsed title=inputs\]

| Name | Type\* | Obligatory | Default | Comments |
| --- | --- | --- | --- | --- |
| _lat_ | F   | Yes | \-  | Latitude, in decimal degrees, south is negative. |
| _lon_ | F   | Yes | \-  | Longitude, in decimal degrees, west is negative. |
| _usehorizon_ | I   | No  | 1   | Calculate taking into account shadows from high horizon. Value of 1 for "yes". |
| _userhorizon_ | L   | No  | \-  | Height of the horizon at equidistant directions around the point of interest, in degrees. Starting at north and moving clockwise. The series '0,10,20,30,40,15,25,5' would mean the horizon height is 0° due north, 10° for north-east, 20° for east, 30° for south-east, etc. |
| _raddatabase_ | T   | No  | [default DB](https://ec.europa.eu/jrc/en/pvgis/docs/usermanual#fig:default_db) | Name of the radiation database (DB): "PVGIS-SARAH" for Europe, Africa and Asia or "PVGIS-NSRDB" for the Americas between 60°N and 20°S, "PVGIS-ERA5" and "PVGIS-COSMO" for Europe (including high-latitudes), and "PVGIS-CMSAF" for Europe and Africa (will be deprecated). The default DBs are PVGIS-SARAH, PVGIS-NSRDB and PVGIS-ERA5 based on the chosen location (see Figure xx). |
| _month_ | T   | Yes | \-  | The value of this parameter should be the number of the month, starting at 1 for January. If you give the value 0 (zero) you will instead get data for all the months. |
| _angle_ | F   | No  | 0   | Inclination angle from horizontal plane of the (fixed) PV system. |
| _aspect_ | F   | No  | 0   | Orientation (azimuth) angle of the (fixed) PV system, 0=south, 90=west, -90=east. |
| _global_ | I   | No  | 0   | Output the global, direct and diffuse in-plane irradiances. Value of 1 for "yes". All other values (or no value) mean "no". |
| _glob\_2axis_ | I   | No  | 0   | Output the global, direct and diffuse two-axis tracking irradiances. Value of 1 for "yes". All other values (or no value) mean "no". |
| _clearsky_ | I   | No  | 0   | Output the global clear-sky irradiance. Value of 1 for "yes". All other values (or no value) mean "no". |
| _clearsky\_2axis_ | I   | No  | 0   | Output the global clear-sky two-axis tracking irradiance. Value of 1 for "yes". All other values (or no value) mean "no". |
| _showtemperatures_ | I   | No  | 0   | Output the daily temperature profile. Value of 1 for "yes". All other values (or no value) mean "no". |
| _localtime_ | I   | No  | 0   | Output the time in the local time zone (not daylight saving time), instead of UTC. Value of 1 for "yes". All other values (or no value) mean "no". |
| _outputformat_ | T   | No  | "csv" | Type of output. Choices are: "csv" for the normal csv output with text explanations, "basic" to get only the data output with no text, and "json". |
| _browser_ | I   | No  | 0   | Use this with a value of "1" if you access the web service from a web browser and want to save the data to a file. |

\* F = Floating point number; I = integer number; L = list of numbers; T= text string.

Example of the minimum usage:

[https://re.jrc.ec.europa.eu/api/DRcalc?lat=45&lon=8&month=3&global=1](https://re.jrc.ec.europa.eu/api/DRcalc?lat=45&lon=8&month=3&global=1)

*   Unlike the PVGIS web interface, it is also possible here to get values for all 12 months with a single call. See below for more details.

### 2.5 Hourly radiation

Inputs

| _Name_ | _Type\*_ | _Obligatory_ | _Default_ | _Comments_ |
| --- | --- | --- | --- | --- |
| _lat_ | _F_ | _Yes_ | _\-_ | _Latitude, in decimal degrees, south is negative._ |
| _lon_ | _F_ | _Yes_ | _\-_ | _Longitude, in decimal degrees, west is negative._ |
| _usehorizon_ | _I_ | _No_ | _1_ | _Calculate taking into account shadows from high horizon. Value of 1 for "yes"._ |
| _userhorizon_ | _L_ | _No_ | _\-_ | _Height of the horizon at equidistant directions around the point of interest, in degrees. Starting at north and moving clockwise. The series '0,10,20,30,40,15,25,5' would mean the horizon height is 0° due north, 10° for north-east, 20° for east, 30° for south-east, etc._ |
| _raddatabase_ | _T_ | _No_ | [_default DB_](https://ec.europa.eu/jrc/en/pvgis/docs/usermanual#fig:default_db) | _Name of the radiation database (DB): "PVGIS-SARAH" for Europe, Africa and Asia or "PVGIS-NSRDB" for the Americas between 60°N and 20°S, "PVGIS-ERA5" and "PVGIS-COSMO" for Europe (including high-latitudes), and "PVGIS-CMSAF" for Europe and Africa (will be deprecated). The default DBs are PVGIS-SARAH, PVGIS-NSRDB and PVGIS-ERA5 based on the chosen location._ |
| _startyear_ | _I_ | _No_ | _year\_min(DB)_ | _First year of the output of hourly averages. Availability varies with the_ [_temporal coverage_](https://ec.europa.eu/jrc/en/pvgis/docs/usermanual#tab:db-years) _of the radiation DB chosen. The default value is the first year of the DB._ |
| _endyear_ | _I_ | _No_ | _year\_max(DB)_ | _Final year of the output of hourly averages. Availability varies with the_ [_temporal coverage_](https://ec.europa.eu/jrc/en/pvgis/docs/usermanual#tab:db-years) _of the radiation DB chosen. The default value is the last year of the DB._ |
| _pvcalculation_ | _I_ | _No_ | _0_ | _If "0" outputs only solar radiation calculations, if "1" outputs the estimation of hourly PV production as well._ |
| _peakpower_ | _F_ | _if pvcalculation_ | _\-_ | _Nominal power of the PV system, in kW._ |
| _pvtechchoice_ | _T_ | _No_ | _"crystSi"_ | PV technology. Choices are: "crystSi", "crystSi2025", "CIS", "CdTe" and "Unknown". |
| _mountingplace_ | _T_ | _No_ | _"free"_ | _Type of mounting of the PV modules. Choices are: "free" for free-standing and "building" for building-integrated._ |
| _loss_ | _F_ | _if pvcalculation_ | _\-_ | _Sum of system losses, in percent._ |
| _trackingtype_ | _I_ | _No_ | _0_ | _Type of suntracking used, 0=fixed, 1=single horizontal axis aligned north-south, 2=two-axis tracking, 3=vertical axis tracking, 4=single horizontal axis aligned east-west, 5=single inclined axis aligned north-south._ |
| _angle_ | _F_ | _No_ | _0_ | _Inclination angle from horizontal plane. Not relevant for 2-axis tracking._ |
| _aspect_ | _F_ | _No_ | _0_ | _Orientation (azimuth) angle of the (fixed) plane, 0=south, 90=west, -90=east. Not relevant for tracking planes._ |
| _optimalinclination_ | _I_ | _No_ | _0_ | _Calculate the optimum inclination angle. Value of 1 for "yes". All other values (or no value) mean "no". Not relevant for 2-axis tracking._ |
| _optimalangles_ | _I_ | _No_ | _0_ | _Calculate the optimum inclination AND orientation angles. Value of 1 for "yes". All other values (or no value) mean "no". Not relevant for tracking planes._ |
| _components_ | _I_ | _No_ | _0_ | _If "1" outputs beam, diffuse and reflected radiation components. Otherwise, it outputs only global values._ |
| _outputformat_ | _I_ | _No_ | _"csv"_ | _Type of output. Choices are: "csv" for the normal csv output with text explanations, "basic" to get only the data output with no text, and "json"._ |
| _browser_ | _I_ | _No_ | _0_ | _Use this with a value of "1" if you access the web service from a web browser and want to save the data to a file._ |

_\*F = Floating point number; I = integer number; L = list of numbers; T= text string._

Example of the minimum usage:

[https://re.jrc.ec.europa.eu/api/seriescalc?lat=45&lon=8](https://re.jrc.ec.europa.eu/api/seriescalc?lat=45&lon=8)

### 2.6 TMY

Inputs

| Name | Type\* | Obligatory | Default | Comments |
| --- | --- | --- | --- | --- |
| _lat_ | F   | Yes | \-  | Latitude, in decimal degrees, south is negative. |
| _lon_ | F   | Yes | \-  | Longitude, in decimal degrees, west is negative. |
| _usehorizon_ | I   | No  | 1   | Calculate taking into account shadows from high horizon. Value of 1 for "yes". |
| _userhorizon_ | L   | No  | \-  | Height of the horizon at equidistant directions around the point of interest, in degrees. Starting at north and moving clockwise. The series '0,10,20,30,40,15,25,5' would mean the horizon height is 0° due north, 10° for north-east, 20° for east, 30° for south-east, etc. |
| _startyear_ | I   | No  | year\_min(DB) | First year of the TMY. Availability depends on the [temporal coverage](https://ec.europa.eu/jrc/en/pvgis/docs/usermanual#tab:db-years) of the radiation DB chosen. The default value is the first year of the DB chosen. |
| _endyear_ | I   | No  | year\_max(DB) | Final year of the TMY. Availability depends on the [temporal coverage](https://ec.europa.eu/jrc/en/pvgis/docs/usermanual#tab:db-years) of the radiation DB chosen. The default value is the last year of the DB chosen. The period defined by _startyear, endyea_r should be >= 10 years. |
| _outputformat_ | T   | No  | "csv" | Type of output. Choices are: "csv" for the normal csv output with text explanations, "basic" to get only the data output with no text, "epw" to get a format suitable for the EnergyPlus software, and "json". |
| _browser_ | I   | No  | 0   | Use this with a value of "1" if you access the web service from a web browser and want to save the data to a file. |

\* F = Floating point number; I = integer number; L = list of numbers; T= text string.

Example of the minium usage:

 [https://re.jrc.ec.europa.eu/api/tmy?lat=45&lon=8](https://re.jrc.ec.europa.eu/api/tmy?lat=45&lon=8)

## 3 Horizon profile

Inputs

| Name | Type\* | Obligatory | Default | Comments |
| --- | --- | --- | --- | --- |
| _lat_ | F   | Yes | \-  | Latitude, in decimal degrees, south is negative. |
| _lon_ | F   | Yes | \-  | Longitude, in decimal degrees, west is negative. |
| _userhorizon_ | L   | No  | \-  | Height of the horizon at equidistant directions around the point of interest, in degrees. Starting at north and moving clockwise. The series '0,10,20,30,40,15,25,5' would mean the horizon height is 0° due north, 10° for north-east, 20° for east, 30° for south-east, etc. |
| _outputformat_ | T   | No  | "csv" | Type of output. Choices are: "csv" for the normal csv output with text explanations, "basic" to get only the data output with no text, and "json". |
| _browser_ | I   | No  | 0   | Use this with a value of "1" if you access the web service from a web browser and want to save the data to a file. |

\* F = Floating point number; I = integer number; L = list of numbers; T= text string.

Example of minimum usage:

[https://re.jrc.ec.europa.eu/api/printhorizon?lat=45&lon=8](https://re.jrc.ec.europa.eu/api/printhorizon?lat=45&lon=8)

*   There is also the option to supply user-defined horizon information. This would not normally be useful since the web service will just send the horizon information back to you. However, it can be a way to check that PVGIS interprets the user-supplied horizon information correctly

## 4 Python wrap for API calls 

Below is an example of python code for to create and run calls to PVGIS. NB Not a complete working code!

import os, csv, json, requests  
import glob  
import pandas as pd  
import numpy as np  
from datetime import date

  
\# -----------Set up array with lat - long values ------------------------------   
\# -----------WGS84 format if not alreaady--------------------------------------  
def xy2latlon(x,y):  
    lon = float(point\_WGS84.split(' ')\[1\]\[:-1\])  
    lat = float(point\_WGS84.split(' ')\[0\]\[:-1\])  
    return (lat, lon)

\----------------------------------

csv\_list=\[f for f in glob.glob(os.path.join(r'Q:\\projects\\csv\_fpr pvgis', "\*.csv"))\] #list of csv to check

#-----------------PVGIS create URLs----------------------------------                     
url\_base = f"[https://re.jrc.ec.europa.eu/api/v5\_2/PVcalc](https://re.jrc.ec.europa.eu/api/v5_2/PVcalc)?"

#----- set API call parameters (examples below) ------------------  
pvgis\_params = dict(  
peakpower=1,  
loss=14,  
vertical\_axis=1,  
angle = 90,  
azimuth = 0,  
outputformat = 'json',)

params = "&".join(\[f'{key}={value}' for key, value in pvgis\_params.items()\])  
url\_pvcalc = f'{url\_base}&{params}'

#----convert LAEA to WGS84 --------------      
    df\_csv\['lat'\]=''  
    df\_csv\['lon'\]=''  
    for ii in range(0,len(df\_csv)):  
        \[lat,lon\]=xy2latlon(df\_csv.loc\[ii,'POINT\_X'\],df\_csv.loc\[ii,'POINT\_Y'\])  
        df\_csv.loc\[ii,'lat'\]=lat  
        df\_csv.loc\[ii,'lon'\]=lon

                                # \_\_\_\_\_\_\_\_\_\_\_ URLs  
    df\_csv\['url\_cw'\] = url\_pvcalc + '&aspect=' + df\_csv\['azimuth\_cw'\].map(str) + '&lat=' + df\_csv\['lat'\].map(str) + '&lon=' + df\_csv\['lon'\].map(str)   
    df\_csv\['url\_aw'\] = url\_pvcalc + '&aspect=' + df\_csv\['azimuth\_aw'\].map(str) + '&lat=' + df\_csv\['lat'\].map(str) + '&lon=' + df\_csv\['lon'\].map(str)   
\# df.to\_csv(csv\_outfile, index = False)  
\# print (df\_select)

#---------------  
    i = 0  
    for idx, row in df\_csv.iterrows():  
        id = row\['ORIG\_FID'\]  
        lat = row\['lat'\]  
        lon = row\['lon'\]

            urls = dict(        
            cw = row\['url\_cw'\],

        # \_\_\_\_\_\_\_\_\_\_\_\_\_ qeury pvgis data (clockwise)  
        for key, url in urls.items():    

               response = requests.get(url)  
            row\_json = json.loads(response.text)     

                                   try:      
                # \_\_\_\_\_\_\_\_\_\_\_\_\_ parse data from pvgis  
                e\_y = row\_json.get('outputs').get('totals').get('fixed').get('E\_y')  
                print (f'i:{i}\\tid: {id}\\tside: {key}\\tazimuth: {azimuth\[key\]}\\t\\tradiation: {e\_y}')  
            except:  
                e\_y = -9999  
                print (f'i:{i}\\t\\t\\tERROR\\nid: {id}\\tside: {key}\\tazimuth: {azimuth\[key\]}\\t\\tradiation: {e\_y}\\t\\tlat: {lat}\\tlon: {lon}')            

                    # \_\_\_\_\_\_\_\_\_\_\_\_\_ update df  
            df\_csv.loc\[df\_csv\["ORIG\_FID"\] == id, f"E\_Y\_{key}"\] = e\_y

                    # \_\_\_\_\_\_\_\_\_\_\_\_\_ save partial results  
            if i > 50:    
                print ('\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_')  
                df\_csv.to\_csv(os.path.join(r'Q:\\projects\\\\pv\_gis\_output', csv40:42\]),index=False)  
                i = 0

                        i +=1