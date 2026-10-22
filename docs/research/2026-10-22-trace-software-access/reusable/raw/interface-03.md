# https://samrepo.nlr.gov/help/pv_shading.html

# Shading and Layout

Shading and snow losses are reductions in the incident irradiance caused by shadows or snow on the photovoltaic modules in the array.

### Overview

SAM can model the impact of a reduction in plane-of-array irradiance on each subarray caused by external shading, self shading, and snow cover. This overview describes each, with links to the sections below that list and describe the inputs.

Notes.  
   
The monthly soiling losses on the [Losses](https://samrepo.nlr.gov/help/pv_losses.html) page also reduce the irradiance incident on the array. When comparing incident plane-of-array irradiance data, be sure to take soiling losses into account.  
   
The self-shading model does not work with the Simple Efficiency Module model on the [Module](https://samrepo.nlr.gov/help/pv_module.html) page.

#### External Shading

[External shading](https://samrepo.nlr.gov/help/pv_shading.html#externalshading) is shading of the photovoltaic subarray by trees, buildings, roof protrusions and other nearby objects. SAM represents a shadow on the subarray in a given time step by a single beam irradiance shading loss for that time step, which it determines from data you provide in the beam shade loss tables in the [Edit Shading Data window](https://samrepo.nlr.gov/help/edit_shading_data.html). SAM reduces the plane-of-array beam irradiance by the shading loss percentage. For example, if a shadow occupies 25% of the subarray's surface area at 11 am, the beam shading loss for 11 am would be 25%. A shading loss of 0 means there is no shade on the subarray, and a loss of 100% means that no beam irradiance reaches the subarray.

When you specify beam irradiance shading losses by time step, you can use SAM's partial shading model to estimate the impact of partial shading on the array's electrical output. The partial shading model does not work with the month-by-hour or solar azimuth-by-altitude beam shade loss tables. For more information about the partial shading model, see MacAlpine, S.; Deline, C. (2015) Simplified Method for Modeling the Impact of Arbitrary Partial Shading Conditions on PV Array Performance. National Renewable Energy Laboratory. 8 pp.; NREL/CP-5J00-64570. ([PDF 699 KB](http://www.nrel.gov/docs/fy15osti/64570.pdf))

SAM accounts for the effect of external shading on the plane-of-array diffuse irradiance using a single sky diffuse shading loss for the entire year.

You can generate beam and diffuse irradiance shading loss data using SAM's [3D Shade Calculator](https://samrepo.nlr.gov/help/pv_shading.html#3dshading) or outside of SAM. SAM can [import beam and diffuse shading data](https://samrepo.nlr.gov/help/edit_shading_data.html#importshadingdata) from files created by PVSyst, and beam shading data from files created by the Solmetric Suneye, and Solar Pathfinder software.

Use the following output variables to explore the effect of external shading (see [Results](https://samrepo.nlr.gov/help/pv_results.html) for descriptions of the variables):

•Subarray \[1..4\] External shading and soiling beam irradiance factor (frac) (except for partial shading model)

•Subarray \[1..4\] Partial external shading DC factor (frac) (for partial shading model only)

•Subarray \[1..4\] POA total irradiance after shading only (W/m2)

•Array POA beam radiation after shading only (kW)

#### Self Shading

[Self shading](https://samrepo.nlr.gov/help/pv_shading.html#selfshading) is caused by row-to-row shading of modules within a subarray, where shadows from modules in neighboring rows of the array block sunlight from parts of other modules in the array during certain times of day. SAM can estimate self shading for fixed subarrays and subarrays with one-axis tracking, assuming that each subarray consists of modules in parallel rows with the same number of modules per row.

For a description of the self-shading model implemented in SAM, see Gilman, P.; Dobos, A.; DiOrio, N.; Freeman, J.; Janzou, S.; Ryberg, D. (2018) SAM Photovoltaic Model Technical Reference Update. 93 pp.; NREL/TP-6A20-67399 available along with other technical documentation from the [SAM website](https://sam.nrel.gov/photovoltaic/pv-sub-page-2.html "https://sam.nrel.gov/photovoltaic/pv-sub-page-2.html").

Use the following output variables to explore the effect of self shading (see [Results](https://samrepo.nlr.gov/help/pv_results.html) for descriptions of the variables):

•Subarray \[1..4\] Self-shading linear beam irradiance factor (thin film linear only)

•Subarray \[1..4\] Self-shading non-linear DC factor (standard non-linear only)

•Subarray \[1..4\] Self-shading non-linear sky diffuse irradiance factor (thin film linear and standard non-linear)

•Subarray \[1..4\] Self-shading non-linear ground diffuse irradiance factor (thin film linear and standard non-linear)

#### Snow Losses

When your weather file contains snow depth data, SAM can estimate [snow losses](https://samrepo.nlr.gov/help/pv_shading.html#snow) in the array's output caused by snow covering the modules in the subarray.

### Shading and Snow Inputs
