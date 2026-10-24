PVGIS typical meteorological year (TMY) generator - Joint Research Centre [Skip to main content](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-tools/pvgis-typical-meteorological-year-tmy-generator_en#main-content)

[![European Commission logo](/themes/contrib/oe_theme/dist/ec/images/logo/logo-ec--mute.svg)](https://commission.europa.eu/index_en)

[en](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-tools/pvgis-typical-meteorological-year-tmy-generator_en)

Search

Search

Joint Research Centre

# PVGIS typical meteorological year (TMY) generator

## 1\. Overview

A typical meteorological year (TMY) is a set of meteorological data with data values for every hour in a year for a given geographical location. The data are selected from hourly data for the full time period available, currently 2005-2020 in PVGIS 5.2 and 2005-2016 in PVGIS 5.1.

PVGIS generates a TMY following the ISO 15927-4 procedure. The methodology is further described in the open access publication: T. Huld et al, Assembling Typical Meteorological Year Data Sets for Building Energy Performance Using Reanalysis and Satellite-Based Data, Atmosphere 2018, 9, 53; doi:10.3390/atmos9020053.

The TMY tool can be used to interactively visualise all data or to download in CSV, json or epw file formats.

The solar radiation database (DB) used is the [default DB](https://ec.europa.eu/jrc/en/pvgis/docs/usermanual#fig:default_db) for the given location, either PVGIS-SARAH3, PVGIS-NSRDB or PVGIS-ERA5. The other meteorological variables are obtained from ERA reanalysis data. For users wishing to resolve the irradiance dato onto a specific plane (for instance, corresponding to that of PV system) the output header contains the time offset to the actual timestamp of the irradiance value. This offset should be  applied if calculating the corresponding sun height. For the SARAH data, the offset depends on the latitude of the location of interest. For ERA5 it is fixed at 0.500 h (30 minutes).

The tool can be accessed with:

*   [PVGIS interface](https://re.jrc.ec.europa.eu/pvg_tools#TMY) - TMY tab
*   [Non-interactive service](https://joint-research-centre.ec.europa.eu/pvgis-photovoltaic-geographical-information-system/getting-started-pvgis/api-non-interactive-service_en) - _tmy_ app

## 2\. Outputs

Note update to the header to include the irradiance time offset (December 2024)

### 2.1 csv

The CSV output contains a header with the following information:

*   Latitude \[decimal degrees\]
*   Longitude \[decimal degrees\]
*   Elevation \[m\]
*   Irradiance Time Offset (h): x.xxx
*   A list of years used for each month to construct the TMY. If the full time series is requested, this list will not be included in the output.

After this follows the header line for the actual data. The consist of 1 year (or several years) of hourly data, each hour on a separate line, with the following columns:

*   _Date & time_ (UTC)
*   _T2m \[°C\] -_ Dry bulb (air) temperature.
*   _RH \[%\] -_ Relative Humidity.
*   _G(h) \[W/m2\]_ - Global horizontal irradiance.
*   _Gb(n) \[W/m2\]_ - Direct (beam) irradiance.
*   _Gd(h) \[W/m2\]_ - Diffuse horizontal irradiance.
*   _IR(h) \[W/m2\] -_ Infrared radiation downwards.
*   _WS10m \[m/s\] -_ Windspeed.
*   _WD10m \[°\]_ - Wind direction.
*   _SP \[Pa\] -_ Surface (air) pressure.

Please also note that  the timestamp is HH:00, but returns values corresponding to the PVGIS-SARAH (HH:MM) or ERA5 (HH:30) timestamps, depending on the database used for solar radiation.

### 2.2 json

{    "inputs": {        "location": {           "latitude": 45.809,           "longitude": 8.632,           "elevation": 223     "irradiance\_time\_offset": x.xxxx  },    "meteo\_data": {           "radiation\_db": "PVGIS-SARAH",           "meteo\_db": "ERA-Interim",           "year\_min": 2005,           "year\_max": 2014,           "use\_horizon": true,           "horizon\_db": "DEM-calcualted",        }    },    "outputs": {        "months\_selected": {            {                "month": 1,                "year": 2007            },            {...}        },        "tmy\_hourly": {            {                "time": "20070101:0000",                "T2m": 5.23,                "RH": 79.72,                "G(h)": 0,                "Gb(n)": 0,                "Gd(h)": 0,                "IR(h)": 242.14,                "WS10m": 1.92,                "WD10m": 30,                "SP": 100570,            },            {...}        }    },    "meta": {        "inputs": {            "location": {                "description": "Selected location"                "variables": {                    "latitude": {                        "description": "Latitude",                        "units": "decimal degrees"                    },                    {...}                }            },            {...}        },        "outputs": {            "months\_selected": {                "type": "time series"                "timestamp": "monthly"                "description": "months selected for the TMY"            },            {...}        }    } }

### 2.3 epw

This is the format used by the open source EnergyPlus software, the file extension is ".epw". For this format, consult the EnergyPlus documentation

Note that that the date & time timestamp is  local time for the EPW format. Also, the format requires that each variable is reported with a value corresponding to the amount during the hour preceding the time indicated. The PVGIS .epw data series therefore starts at 01:00, but reports the same values as for the .csv and .json files at 00:00.

The time offset of the irradiance value with respect to the TMY timestamp is given in the comments 2 line, e.g. COMMENTS 2,Irradiance Time Offset (h):x.xxx