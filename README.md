# High-Resolution Fleet Turnover Model (HRFTOM)

Code for: Bagi, T. A., Hennesey, E., & Syal, S. M. *High-Resolution Fleet Turnover Model to Assess California's Electric Vehicle Transition.* iScience (2026). DOI: [to be added]

The model projects the light-duty vehicle fleet of every California ZIP code from a 2019 baseline to 2050. It splits each fleet into EVs and internal combustion vehicles (ICE).

## How it works

For each ZIP code and each output year (2020, 2025, …, 2050), the model:
1. Starts from the 2019 fleet, broken down by model year and fuel type.
2. Adds new vehicle sales for every year from 2020 up to the output year. Sales grow with county-level EMFAC sales changes and are split into EV and ICE using the EV-share forecast.
3. Retires vehicles using a survival curve. Vehicles already in the 2019 fleet use conditional Kaplan–Meier survival. New sales, and all vehicles under the NHTSA curve, use unconditional survival.
4. Records the EV count, ICE count, EV share, and average fleet age.

## Data sources

| Dataset | Source | Link |
|---|---|---|
| CARB EMFAC fleet database (EMFAC2021; calendar years 2015–2021) | California Air Resources Board, 2023 | https://emfac.arb.ca.gov/fleet-db/ |
| CARB EMFAC Emissions Inventory (EMFAC2021; projections to 2050) | California Air Resources Board, 2025 | https://arb.ca.gov/emfac/emissions-inventory |
| CARB Advanced Clean Cars II regulation | California Air Resources Board, 2022 | https://ww2.arb.ca.gov/our-work/programs/advanced-clean-cars-program/advanced-clean-cars-ii |
| Demographic data | American Community Survey, U.S. Census Bureau | https://www.census.gov/programs-surveys/acs/data.html |
| HUD USPS ZIP Code Crosswalk (ZIP–County, Q4 2019) | U.S. Department of Housing and Urban Development | https://www.huduser.gov/portal/datasets/usps_crosswalk.html |
| TIGER/Line shapefiles | U.S. Census Bureau | https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.2019.html#list-tab-790442341 |
