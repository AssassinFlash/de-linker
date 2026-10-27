Electricity Rates and Load — SAM Help

[Skip to main content](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/index.html#main-content)

Back to top  

 Ctrl+K

[![SAM Help - Home](../_static/SAM-logo-horizontal.png)](https://natlabrockies.github.io/SAM/doc/index.html)

*   [.rst](https://natlabrockies.github.io/SAM/doc/_sources/electricity-rates-and-load/index.rst "Download source file")
*   .pdf

# Electricity Rates and Load

# Electricity Rates and Load[#](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/index.html#electricity-rates-and-load "Link to this heading")

For projects with the [residential or commercial](https://natlabrockies.github.io/SAM/doc/introduction/fin_overview.html#rescom) or [third party ownership](https://natlabrockies.github.io/SAM/doc/introduction/fin_overview.html#thirdparty) financial model that buy and sell electricity at retail rates, you specify a rate structure (net metering, energy rates, demand charges, and monthly charges) on the [Electricity Rates](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html) page, and a building or facility load on the [Electric Load](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_load.html) page.

*   [Electric Load](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_load.html)
    
*   [Electricity Rates](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html)
    
*   [Electricity Bill Results](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_bill_results.html)
    

*   [Electric Load](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_load.html)
    *   [Input Time Series Load Data](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_load.html#input-time-series-load-data)
        *   [Hourly or Subhourly Load Profile](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_load.html#hourly-or-subhourly-load-profile)
        *   [Adjust Load Profile to Monthly Usage](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_load.html#adjust-load-profile-to-monthly-usage)
        *   [Download](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_load.html#download)
        *   [Monthly Load Summary](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_load.html#monthly-load-summary)
    *   [Calculate Load Data](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_load.html#calculate-load-data)
        *   [Building Energy Load Profile Estimator](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_load.html#building-energy-load-profile-estimator)
        *   [Annual Adjustment](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_load.html#annual-adjustment)
    *   [Working with Time Series Load Data](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_load.html#working-with-time-series-load-data)
    *   [Data Sources](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_load.html#data-sources)
    *   [Time Step and Convention](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_load.html#time-step-and-convention)
    *   [Importing Data from a File](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_load.html#importing-data-from-a-file)
    *   [Pasting Load Data from your Computer’s Clipboard](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_load.html#pasting-load-data-from-your-computer-s-clipboard)
*   [Electricity Rates](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html)
    *   [Overview](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html#overview)
    *   [Electricity Rates Glossary](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html#electricity-rates-glossary)
    *   [Rate Structure Definitions](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html#rate-structure-definitions)
    *   [Metering and Billing Definitions](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html#metering-and-billing-definitions)
    *   [OpenEI Utility Rate Database](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html#openei-utility-rate-database)
    *   [Save / Load Rate Data](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html#save-load-rate-data)
    *   [Metering and Billing](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html#metering-and-billing)
    *   [Fixed Charge](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html#fixed-charge)
    *   [Minimum Charges](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html#minimum-charges)
    *   [Annual Escalation](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html#annual-escalation)
    *   [Description and Applicability](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html#description-and-applicability)
    *   [Energy Charges](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html#energy-charges)
    *   [Energy Rate Table](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html#energy-rate-table)
    *   [Weekday and Weekend Schedules for Energy Charges](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html#weekday-and-weekend-schedules-for-energy-charges)
    *   [Energy Rate Structure Examples](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html#energy-rate-structure-examples)
    *   [Billing Demand](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html#billing-demand)
    *   [Billing Demand by Month Table](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html#billing-demand-by-month-table)
    *   [Billing Demand by Time-of use Period for Demand Charges](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html#billing-demand-by-time-of-use-period-for-demand-charges)
    *   [Demand Charges](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html#demand-charges)
    *   [Demand Rates by Month with Optional Tiers Rate Table](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html#demand-rates-by-month-with-optional-tiers-rate-table)
    *   [Demand Rates by Time-of-use and/or Tiers](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html#demand-rates-by-time-of-use-and-or-tiers)
    *   [Weekday and Weekend Schedules for Demand Charges](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_rates.html#weekday-and-weekend-schedules-for-demand-charges)
*   [Electricity Purchases](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_purchases.html)
    *   [Electricity Purchases](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_purchases.html#id1)
    *   [Rate Structure Definitions](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_purchases.html#rate-structure-definitions)
    *   [OpenEI Utility Rate Database](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_purchases.html#openei-utility-rate-database)
    *   [Save / Load Rate Data](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_purchases.html#save-load-rate-data)
    *   [Metering and Billing](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_purchases.html#metering-and-billing)
    *   [Fixed Charge](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_purchases.html#fixed-charge)
    *   [Minimum Charges](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_purchases.html#minimum-charges)
    *   [Annual Escalation](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_purchases.html#annual-escalation)
    *   [Description and Applicability](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_purchases.html#description-and-applicability)
    *   [Energy Charges](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_purchases.html#energy-charges)
    *   [Energy Rate Table](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_purchases.html#energy-rate-table)
    *   [Weekday and Weekend Schedules](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_purchases.html#weekday-and-weekend-schedules)
    *   [Billing Demand](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_purchases.html#billing-demand)
    *   [Billing Demand by Month Table](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_purchases.html#billing-demand-by-month-table)
    *   [Billing Demand by Time-of use Period](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_purchases.html#billing-demand-by-time-of-use-period)
    *   [Demand Charges](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_purchases.html#demand-charges)
    *   [Demand Rates by Month with Optional Tiers Rate Table](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_purchases.html#demand-rates-by-month-with-optional-tiers-rate-table)
    *   [Demand Rates by Time-of-use and/or Tiers](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_purchases.html#demand-rates-by-time-of-use-and-or-tiers)
*   [Electricity Bill Results](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_bill_results.html)
    *   [Summary](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_bill_results.html#summary)
    *   [Data Tables](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_bill_results.html#data-tables)
    *   [Monthly Data / Electricity Rate Data by Year](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_bill_results.html#monthly-data-electricity-rate-data-by-year)
    *   [Hourly / n Minute Data](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_bill_results.html#hourly-n-minute-data)
    *   [Electricity Rate Data by Tier and Period](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_bill_results.html#electricity-rate-data-by-tier-and-period)
    *   [Electricity Demand Data by Period](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_bill_results.html#electricity-demand-data-by-period)