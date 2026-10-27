Consumption (Calculation) :: PV\*SOL® help

[](https://help.valentin-software.com/pvsol/en/calculation/consumption/#)[PV\*SOL Help](https://help.valentin-software.com/pvsol/en/) > [Calculation](https://help.valentin-software.com/pvsol/en/calculation/) > Consumption

# Consumption

The consumption is transferred to the simulation in minutely or hourly time series. The time series are generated from the entered load profiles and individual consumers by addition:

$$ Consumption(\\text{h}) = \\sum\_{k=0}^{n}Load profiles(\\text{h}) + \\sum\_{k=0}^{n} Individual consumer(\\text{h}) $$

### Load profiles (from measured values)

The following load profiles are supplied in PV\*SOL®. They have a temporal resolution of 1min, 15min or 1h.

#### Households

| Name | Description | Source |
| --- | --- | --- |
| 1-person household |     | Load Profile Generator |
| 1-person household (retiree) |     | Load Profile Generator |
| 1-person household (teleworker) |     | Load Profile Generator |
| 2-person household |     | Load Profile Generator |
| 2-person household (1 teleworker) | One person works from home, the other person works from outside the home. | Load Profile Generator |
| 2-person household (2 teleworkers) | Both members of the household work from home. | Load Profile Generator |
| 2-person household (retirees) |     | Load Profile Generator |
| 2-person household with 2 children |     | Load Profile Generator |
| 2-person household with 2 children (1 teleworker) | One person works from home, the other person works from outside the home. | Load Profile Generator |
| 2-person household with 2 children (2 teleworkers) | Both members of the household work from home. | Load Profile Generator |
| 2-person household with one child |     | Load Profile Generator |
| 2-person household with one child (1 teleworker) | One person works from home, the other person works from outside the home. | Load Profile Generator |
| 2-person household with one child (2 teleworkers) | Both members of the household work from home | Load Profile Generator |

#### Air conditioning (simple)

| Name | Description | Source |
| --- | --- | --- |
| Air conditioning (simple), Austria, Wien | Simplified load profile of an air conditioning system. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Brazil, Brasília | Simplified load profile of an air conditioning system. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Chile, Santiago de Chile | Simplified load profile of an air conditioning system. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Croatia, Zagreb | Simplified load profile of an air conditioning system. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Czech Republic, Praha | Simplified load profile of an air conditioning system. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Denmark, København | Simplified load profile of an air conditioning system. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), France, Paris | Simplified load profile of an air conditioning system. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Germany, climate zone 01 | Simplified load profile of an air conditioning system; North sea coast. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Germany, climate zone 02 | Simplified load profile of an air conditioning system; Baltic sea coast. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Germany, climate zone 03 | Simplified load profile of an air conditioning system; North-West German lowlands. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Germany, climate zone 04 | Simplified load profile of an air conditioning system; North-East German lowlands. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Germany, climate zone 05 | Simplified load profile of an air conditioning system; North Rhine-Westfalian bay and Emsland. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Germany, climate zone 06 | Simplified load profile of an air conditioning system; Northern and Western low mountain ranges, peripheral areas. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Germany, climate zone 07 | Simplified load profile of an air conditioning system; Northern and Western low mountain ranges, central areas. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Germany, climate zone 08 | Simplified load profile of an air conditioning system; Upper Harz and Black Forest (low mountain range location). See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Germany, climate zone 09 | Simplified load profile of an air conditioning system; Thuringian basin and Saxon hill country. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Germany, climate zone 10 | Simplified load profile of an air conditioning system; South-Eastern low mountain ranges up to 1000 m. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Germany, climate zone 11 | Simplified load profile of an air conditioning system; Ore mountains, Bohemian and Black Forest above 1000 m. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Germany, climate zone 12 | Simplified load profile of an air conditioning system; Upper Rhine Graben and lower Neckar valley. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Germany, climate zone 13 | Simplified load profile of an air conditioning system; Swabian-Frankonian stepped country and Alpine foothills. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Germany, climate zone 14 | Simplified load profile of an air conditioning system; Swabian Alb and Baar. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Germany, climate zone 15 | Simplified load profile of an air conditioning system; Alpine foothills and valleys. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Iran, Tehran | Simplified load profile of an air conditioning system. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Netherlands, Amsterdam | Simplified load profile of an air conditioning system. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Poland, Warszawa | Simplified load profile of an air conditioning system. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Portugal, Lisboa | Simplified load profile of an air conditioning system. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), South Africa, Pretoria | Simplified load profile of an air conditioning system. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Spain, Madrid | Simplified load profile of an air conditioning system. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Sweden, Stockholm | Simplified load profile of an air conditioning system. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Switzerland, Zürich | Simplified load profile of an air conditioning system. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), Turkey, Ankara | Simplified load profile of an air conditioning system. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |
| Air conditioning (simple), United Kingdom, London | Simplified load profile of an air conditioning system. See [below](https://help.valentin-software.com/pvsol/en/calculation/consumption/#simplified-load-profile-of-an-air-conditioning-system) for details. |     |

##### Simplified load profile of an air conditioning system

The load profiles “Air conditioning (simple)” were generated based on the outdoor air temperature profile at the specified location (or at the reference location for German climate zones in accordance with VDI standard 4655):

*   If the outdoor air temperature exceeds 26°C:  
    Constant load of 2000 W (power consumption of the air conditioning system)
*   If the outdoor air temperature is 26°C or below:  
    Constant load of 20 W (standby consumption)

Climate data: Valentin Software DWD TMY3 (locations in Germany) or Meteonorm 9 (other locations).

#### BDEW

| Name | Description | Source |
| --- | --- | --- |
| BDEW commercial load profile (G1) | Business, weekdays 8 am to 6 pm (i.e. offices, doctor’s offices, workshops, administrative units) | BDEW |
| BDEW load profile business (G2) | Business with high or primary use in the evening (i.e. sport clubs, fitness studios, night clubs) | BDEW |
| BDEW load profile business (G3) | Continual business operation, i.e. cold warehouses, pumps, sewage treatment facilities (cold warehouses, pumps, sewage treatment facilities) | BDEW |
| BDEW load profile business (G4) | Shop/Hairdresser | BDEW |
| BDEW load profile business (G5) | Bakery with shop attached | BDEW |
| BDEW load profile business (G6) | Weekend operations (i.e. cinemas) | BDEW |
| BDEW load profile business (GO) | General business (weighted mean of profiles G1-G6) | BDEW |
| BDEW load profile household (H0) |     | BDEW |
| BDEW load profile agriculture (L0) | Agriculture (weighted mean value of profiles L1 and L2) | BDEW |
| BDEW load profile agriculture (L1) | Agricultural operations with milk/secondary income livestock | BDEW |
| BDEW load profile agriculture (L2) | Other agricultural operations | BDEW |

#### Brasil

| Name | Description | Source |
| --- | --- | --- |
| Brasil Centro Oeste |     | Solarize |
| Brasil Nordeste |     | Solarize |
| Brasil Norte |     | Solarize |
| Brasil Sudeste |     | Solarize |
| Brasil Sul |     | Solarize |

#### Colombia

| Name | Description | Source |
| --- | --- | --- |
| Colombia Amazonia |     | Solsta |
| Colombia Andina |     | Solsta |
| Colombia Caribe |     | Solsta |
| Colombia Orinoquia |     | Solsta |
| Colombia Pacifico |     | Solsta |

#### HTW Berlin (Households)

| Name | Description | Source |
| --- | --- | --- |
| Household, seasonal course comparable with standard profile | Load profile 31 | HTW Berlin |
| Household, load profile with high night proportion | Load profile 67 | HTW Berlin |
| Household, load profile with high summer proportion | Load profile 26 | HTW Berlin |
| Household, Load profile with high percentage of morning hours | Load profile 68 | HTW Berlin |
| Household, Load profile with low percentage of nighttime hours | Load profile 61 | HTW Berlin |
| Household, load profile with low summer proportion | Load profile 12 | HTW Berlin |
| Household, Load profile with low percentage of morning hours | Load profile 48 | HTW Berlin |
| Household, diurnal course comparable with standard profile | Load profile 17 | HTW Berlin |

|Load profile with constant load | Constant load throughout the year, e.g.broadcasting station | |

#### VDI low-energy house

| Name | Description | Source |
| --- | --- | --- |
| VDI low-energy house climate zone 01 | 4 persons; North sea coast | VDI 4655 |
| VDI low-energy house climate zone 02 | 4 persons; Baltic sea coast | VDI 4655 |
| VDI low-energy house climate zone 03 | 4 persons; North-West German lowlands | VDI 4655 |
| VDI low-energy house climate zone 04 | 4 persons; North-East German lowlands | VDI 4655 |
| VDI low-energy house climate zone 05 | 4 persons; North Rhine-Westfalian bay and Emsland | VDI 4655 |
| VDI low-energy house climate zone 06 | 4 persons; Northern and Western low mountain ranges, peripheral areas | VDI 4655 |
| VDI low-energy house climate zone 07 | 4 persons; Northern and Western low mountain ranges, central areas | VDI 4655 |
| VDI low-energy house climate zone 08 | 4 persons; Upper Harz and Black Forest (low mountain range location) | VDI 4655 |
| VDI low-energy house climate zone 09 | 4 persons; Thuringian basin and Saxon hill country | VDI 4655 |
| VDI low-energy house climate zone 10 | 4 persons; South-Eastern low mountain ranges up to 1000 m | VDI 4655 |
| VDI low-energy house climate zone 11 | 4 persons; Ore mountains, Bohemian and Black Forest above 1000 m | VDI 4655 |
| VDI low-energy house climate zone 12 | 4 persons; Upper Rhine Graben and lower Neckar valley | VDI 4655 |
| VDI low-energy house climate zone 13 | 4 persons; Swabian-Frankonian stepped country and Alpine foothills | VDI 4655 |
| VDI low-energy house climate zone 14 | 4 persons; Swabian Alb and Baar | VDI 4655 |
| VDI low-energy house climate zone 15 | 4 persons; Alpine foothills and valleys | VDI 4655 |

#### VDI multi-family house

| Name | Description | Source |
| --- | --- | --- |
| VDI multi-family house climate zone 01 | 10 persons; north sea coast | VDI 4655 |
| VDI multi-family house climate zone 02 | 10 persons; baltic sea coast | VDI 4655 |
| VDI multi-family house climate zone 03 | 10 persons; North-West German lowlands | VDI 4655 |
| VDI multi-family house climate zone 04 | 10 persons; North-East German lowlands | VDI 4655 |
| VDI multi-family house climate zone 05 | 10 persons; North Rhine-Westfalian bay and Emsland | VDI 4655 |
| VDI multi-family house climate zone 06 | 10 persons; Northern and Western low mountain ranges, peripheral areas | VDI 4655 |
| VDI multi-family house climate zone 07 | 10 persons; Northern and Western low mountain ranges, central areas | VDI 4655 |
| VDI multi-family house climate zone 08 | 10 persons; Upper Harz and Black Forest (low mountain range location) | VDI 4655 |
| VDI multi-family house climate zone 09 | 10 persons; Thuringian basin and Saxon hill country | VDI 4655 |
| VDI multi-family house climate zone 10 | 10 persons; South-Eastern low mountain ranges up to 1000m | VDI 4655 |
| VDI multi-family house climate zone 11 | 10 persons; Ore mountains, Bohemian and Black Forest above 1000m | VDI 4655 |
| VDI multi-family house climate zone 12 | 10 persons; Upper Rhine Graben and lower Neckar valley | VDI 4655 |
| VDI multi-family house climate zone 13 | 10 persons; Swabian-Frankonian stepped country and Alpine foothills | VDI 4655 |
| VDI multi-family house climate zone 14 | 10 persons; Swabian Alb and Baar | VDI 4655 |
| VDI multi-family house climate zone 15 | 10 persons; Alpine foothills and valleys | VDI 4655 |

#### VDI single-family house

| Name | Description | Source |
| --- | --- | --- |
| VDI single-family house climate zone 01 | 4 persons; north sea coast | VDI 4655 |
| VDI single-family house climate zone 02 | 4 persons; baltic sea coast | VDI 4655 |
| VDI single-family house climate zone 03 | 4 persons; North-West German lowlands | VDI 4655 |
| VDI single-family house climate zone 04 | 4 persons; North-East German lowlands | VDI 4655 |
| VDI single-family house climate zone 05 | 4 persons; North Rhine-Westfalian bay and Emsland | VDI 4655 |
| VDI single-family house climate zone 06 | 4 persons; Northern and Western low mountain ranges, peripheral areas | VDI 4655 |
| VDI single-family house climate zone 07 | 4 persons; Northern and Western low mountain ranges, central areas | VDI 4655 |
| VDI single-family house climate zone 08 | 4 persons; Upper Harz and Black Forest (low mountain range location) | VDI 4655 |
| VDI single-family house climate zone 09 | 4 persons; Thuringian basin and Saxon hill country | VDI 4655 |
| VDI single-family house climate zone 10 | 4 persons; South-Eastern low mountain ranges up to 1000m | VDI 4655 |
| VDI single-family house climate zone 11 | 4 persons; Ore mountains, Bohemian and Black Forest above 1000m | VDI 4655 |
| VDI single-family house climate zone 12 | 4 persons; Upper Rhine Graben and lower Neckar valley | VDI 4655 |
| VDI single-family house climate zone 13 | 4 persons; Swabian-Frankonian stepped country and Alpine foothills | VDI 4655 |
| VDI single-family house climate zone 14 | 4 persons; Swabian Alb and Baar | VDI 4655 |
| VDI single-family house climate zone 15 | 4 persons; Alpine foothills and valleys | VDI 4655 |

#### Heat Pump

| Name | Description | Source |
| --- | --- | --- |
| Heat Pump | Base year 2011 |     |
| Heat Pump System with Space Heating (air/water) |     | GeoT\*SOL |
| Heat Pump System with Space Heating (brine/water, geothermal collector) | GeoT\*SOL |     |
| Heat Pump System with Space Heating (brine/water, geothermal probe) |     | GeoT\*SOL |
| Heat Pump System with Space Heating (water/water) |     | GeoT\*SOL |
| Heat Pump System with Space Heating and Domestic Hot Water (air/water) | GeoT\*SOL |     |
| Heat Pump System with Space Heating and Domestic Hot Water (air/water) with Heating Element | GeoT\*SOL |     |
| Heat Pump System with Space Heating and Domestic Hot Water (brine/water, geothermal collector) | GeoT\*SOL |     |
| Heat Pump System with Space Heating and Domestic Hot Water (brine/water, geothermal probe) | GeoT\*SOL |     |
| Heat Pump System with Space Heating and Domestic Hot Water (water/water) | GeoT\*SOL |     |

#### UK - Elexon

| Name | Description | Source |
| --- | --- | --- |
| Elexon Load Profile Class 1 - Domestic Unrestricted Customers | The vast majority of small businesses and sole traders fall into the category of domestic customers with no restrictions. This category is aimed at private customers who do not require a bespoke energy contract. | Elexon |
| Elexon Load Profile Class 2 - Domestic Economy 7 Customers | This energy tariff is very similar to Profile Class 01. This tariff is also aimed at small businesses and households; the difference is that domestic customers can save on electricity costs during off-peak hours with the ‘Economy 7’ tariff. | Elexon |
| Elexon Load Profile Class 3 - Non-Domestic Unrestricted Customers | This tariff category is aimed at small businesses that do not consume large amounts of energy. Non-domestic customers without consumption limits are businesses with low consumption and predictable consumption patterns. | Elexon |
| Elexon Load Profile Class 4 - Non-Domestic Economy 7 Customers | This category includes businesses with low energy consumption that have an Economy 7 meter. The Economy 7 meter enables commercial Economy 7 customers to operate cost-effectively thanks to lower tariffs during off-peak hours. | Elexon |
| Elexon Load Profile Class 5 - Non-Domestic Maximum Demand (MD) Customers with LF < 20% | These customers have a peak load factor of less than 20%, which means they consume less energy than all other customers in the peak load category | Elexon |
| Elexon Load Profile Class 6 - Non-Domestic Maximum Demand (MD) Customers with 20 % < LF < 30% | Business customers in this category have a peak load factor of between 20% and 30%. | Elexon |
| Elexon Load Profile Class 7 - Non-Domestic Maximum Demand (MD) Customers with 30 % < LF < 40% | The peak load factor for companies in this category tends to be at the upper end of the scale – 30–40%. | Elexon |
| Elexon Load Profile Class 8 - Non-Domestic Maximum Demand (MD) Customers with LF > 40% | Businesses with a peak load of over 40% fall into this profile category. This is at the top end of the scale. | Elexon |

*   Source of load profiles: [https://bscdocs.elexon.co.uk/guidance-notes/load-profiles-and-their-use-in-electricity-settlement](https://bscdocs.elexon.co.uk/guidance-notes/load-profiles-and-their-use-in-electricity-settlement)
*   Source of descriptions: [https://www.businessenergyuk.com/knowledge-hub/profile-classes/](https://www.businessenergyuk.com/knowledge-hub/profile-classes/)
*   Load factor (LF): The load factor is the percentage ratio of consumption (in kWh) during a specific period to the amount of kWh that would have been supplied if peak demand had remained constant during that period. [https://www.elexon.co.uk/bsc/settlement/profiling/](https://www.elexon.co.uk/bsc/settlement/profiling/)

#### UK - Catapult

| Name | Description | Source |
| --- | --- | --- |
| Catapult profile - Clubs & Community centres |     | Catapult |
| Catapult profile - Higher Education - accommodation |     | Catapult |
| Catapult profile - Higher Education - teaching & research |     | Catapult |
| Catapult profile - Large distribution warehouses |     | Catapult |
| Catapult profile - Large food shops |     | Catapult |
| Catapult profile - Leisure centres |     | Catapult |
| Catapult profile - Nursing Homes |     | Catapult |
| Catapult profile - Offices (public) |     | Catapult |
| Catapult profile - State Primary school |     | Catapult |
| Catapult profile - State Secondary school |     | Catapult |
| Catapult profile - Warehouses |     | Catapult |

*   Source of load profiles: Site energy demand estimator user guide, Energy Systems Catapult 2024, UK [https://es.catapult.org.uk/wp-content/uploads/2023/05/Site-energy-demand-estimator-user-guide.pdf](https://es.catapult.org.uk/wp-content/uploads/2023/05/Site-energy-demand-estimator-user-guide.pdf)

### Load profiles (from daily profiles)

These load profiles are composed of daily curves and have a temporal resolution of 1h.

| Source | Description |
| --- | --- |
| Riot police 30000 m² (Note 1) | Source 1 |
| Brasil Centro Oeste | Solarize |
| Brasil Nordeste | Solarize |
| Brasil Norte | Solarize |
| Brasil Sudeste | Solarize |
| Brasil Sul | Solarize |
| Brewery | Source 2 |
| Village with production facilities | SMA |
| Village without production facilities | SMA |
| Single-family house Central Europe | undocumented |
| Detached house southern hemisphere | undocumented |
| Research Centre | Source 1 |
| Indoor swimming pool 900 m² (Note 1) | Source 1 |
| Household Evening peak | undocumented |
| Hospital 14000 m² (Note 1) | Source 1 |
| Hospital 16000 m² (Note 1) | Source 1 |
| Hospital 300 beds | Source 1 |
| Hospital 300 beds | Source 1 |
| Hospital 400 beds | Source 1 |
| Hospital 434 beds | Source 3 |
| Hospital 450 kW electr | Source 8 |
| Estate Ghana | SMA |
| Load profile with constant electricity consumption over the entire year |     |
| Multipurpose hall 2300 m² | Source 1 |
| Restaurant with air conditioning | Source 1 |
| School 10000 m² (Note 1) | Source 1 |
| School 18500 m² (Note 1) | Source 1 |
| School with swimming pool 21500 m² (Note 2) | Source 1 |
| UK Household | The Solar Design Company |
| Administration building 1000 employees | Source 1 |
| Administration building 16000 m² (Note 1) | Source 1 |
| Department stores’ 11000 m² (with Rlt facility) | Source 3 |
| Residential house Average Berlin households | Source 6 |
| Residential complex | IAE Annex 42 |
| Residential complex 24 residential units | Source 5 |

*   Note 1: Only winter workday measured
*   Note 2: Only transitional value day measured

### Sources

| Source | Description |
| --- | --- |
| 1   | Own measurement |
| 2   | BINE Projekt Info-Service Dec. 1993 |
| 3   | BINE Projekt Info-Service July 1986 |
| 4   | Warmwasserversorgungen heute; AT Verlag Aarau (Schweiz) 1984 |
| 5   | Düwall,P., Lange-Hüsken, M., : Lastganglinien der Haushalte. VDEW (1985) |
| 6   | Düwall, P. : Stromanwendung im Haushalt. Regionaler Abschlußbericht der Berliner Kraft- und Licht (BEWAG)-Aktiengesellschaft zum BMFT/BMWi-Forschungsauftrag. BEWAG 1986 |
| 7   | Gossenberger, M. : Der elektische Leistungsbedarf von Haushalten, Schriftenreihe der Forschungsstelle für Energiewirtschaft Band 13. Springer Verlag, Berlin Heidelberg New York 1979 |
| 8   | Bergschneider, C., Schmitt, D. : Dezentrale Kraft-Wärme-Kopplung. R. Oldenbourg Verlag 1988 |
| 9   | VDI 6025 Blatt 7. Berechnung der Kosten von Wärmeversorgungsanlagen. Blockheizkraftwerke. Beuth Verlag, Berlin 1988 |
| SMA | provided by [SMA](https://www.sma.de/) |
| IAE Annex 42 | Annex 42 - The Simulation of Building-Integrated Fuel Cell and Other Cogeneration Systems (COGEN-SIM) [(Link)](https://iea-ebc.org/projects/project?AnnexID=42) |
| Load Profile Generator | Created with [LoadProfileGenerator](https://www.loadprofilegenerator.de/) |
| HTW Berlin | Hochschule für Technik und Wirtschaft HTW Berlin: „Repräsentative elektrische Lastprofile für Einfamilienhäuser in Deutschland auf 1-sekündiger Datenbasis“, Datensatz, Berlin, 2015. [(Link)](https://pvspeicher.htw-berlin.de/veroeffentlichungen/daten/lastprofile/) |
| GeoT\*SOL | Created with [GeoT\*SOL 2020 R1](https://valentin-software.com/produkte/geotsol/) |
| Solsta | provided by [Solsta SAS](https://solsta.co/), Daten von XM (Colombian grid operator) |
| Solarize | provided by [Solarize Treinamentos Profissionais Ltda.](https://www.solarize.com.br/), data from [Eletrobrás/Procel, 2007](http://www.procelinfo.com.br/services/procel-info/Simuladores/DownloadSimulator.asp?DocumentID=%7BA9E26523-80B8-41E2-8D75-083A20E85867%7D&ServiceInstUID=%7B5E202C83-F05D-4280-9004-3D59B20BEA4F%7D) |
| The Solar Design Company | provided by [The Solar Design Company](https://www.solardesign.co.uk/) |
| BDEW | Standard load profiles (Electricity) by BDEW [(Link)](https://www.bdew.de/energie/standardlastprofile-strom/) |
| BDEW 2025 | [Aktualisierte Standardlastprofile (Strom) des BDEW 2025](https://www.bdew.de/media/documents/2025-03-17_AWH_Aktualisierte_SLP_Strom_2025_Ver%C3%B6ffentlichung.pdf) |
| Elexon | [https://bscdocs.elexon.co.uk/guidance-notes/load-profiles-and-their-use-in-electricity-settlement](https://bscdocs.elexon.co.uk/guidance-notes/load-profiles-and-their-use-in-electricity-settlement) |
| Catapult | Site energy demand estimator user guide, Energy Systems Catapult 2024, UK [https://es.catapult.org.uk/wp-content/uploads/2023/05/Site-energy-demand-estimator-user-guide.pdf](https://es.catapult.org.uk/wp-content/uploads/2023/05/Site-energy-demand-estimator-user-guide.pdf) |

### Individual consumers

This is how the peak consumption of individual consumers is calculated:

| Consumer type | Calculation method |
| --- | --- |
| User-independent consumer: | Operating period = Annual power demand / Power\*(switches every X hours) / 8760  <br>Peak consumption = Power, if operating time $\\geq 1\\text{h}$  <br>Peak consumption = Power\*Operating time/1h, if operating time$\\lt 1\\text{h}$ |
| User-dependent consumer: | Peak consumption = Power |
| Short-term consumer: | Peak consumption = Power \* Operating time / 1h |
| Light: | Peak consumption = Power |

#### Consumer influence on simulation

The consumption in one hour is assumed to be constant, i.e. with an operating time of 15 minutes per hour, it is simulated as a device that runs for 1 hour with a quarter of the load.

* * *

See also

*   [Pages > Consumption](https://help.valentin-software.com/pvsol/en/pages/consumption/)