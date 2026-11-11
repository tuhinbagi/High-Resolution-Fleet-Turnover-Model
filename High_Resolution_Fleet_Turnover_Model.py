import pandas as pd
import numpy as np
import time
import os

BASELINE_YEAR = 2019  # year of input fleet snapshot


def main(survival_mode='california', ev_scenario='BAU'):
    """
    Main function to run the California fleet turnover model.
    Simulates vehicle fleet evolution from 2019 to 2050.
    
    Conditional Kaplan-Meier survival is used for baseline (2019) vehicles
    when survival_mode is 'zipcode' or 'california' (KM curves).
    NHTSA mode applies unconditional survival to all vehicles, since NHTSA
    curves may already be period-based / conditional.
    
    Args:
        survival_mode: Choice of survival curve to use:
                      'zipcode' - Uses zipcode-specific survival curves
                      'california' - Uses California-wide survival curve
                      'nhsta' - Uses NHSTA California survival curve
        
        ev_scenario: Choice of EV adoption forecast:
                    'BAU' - Business as usual scenario
                    'ACCII' - Advanced Clean Cars II scenario (ACC II targets 2026-2035, 100% EV sales after)
    """
    start_time = time.time()
    
    valid_survival_modes = ['zipcode', 'california', 'nhsta']
    valid_ev_scenarios = ['BAU', 'ACCII']
    
    if survival_mode not in valid_survival_modes:
        raise ValueError(f"Invalid survival_mode. Choose from: {valid_survival_modes}")
    
    if ev_scenario not in valid_ev_scenarios:
        raise ValueError(f"Invalid ev_scenario. Choose from: {valid_ev_scenarios}")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    data_folder = 'Data'
    results_folder = 'results_conditional'
    os.makedirs(results_folder, exist_ok=True)
    
    print("Loading data files...")
    print(f"Configuration: Survival={survival_mode}, EV Scenario={ev_scenario}")
    
    income_data = pd.read_csv(os.path.join(data_folder, 'Californiazipcodeincome.csv'))
    fleet_2019 = pd.read_csv(os.path.join(data_folder, 'Californiazipcode2019fleet.csv'))
    sales_2019 = pd.read_csv(os.path.join(data_folder, 'Californiazipcode2019sales.csv'))
    
    if survival_mode == 'zipcode':
        survival_curves = pd.read_csv(os.path.join(data_folder, 'zipcodesurvivalcurve.csv'))
        print("  - Using zipcode-specific survival curves")
    elif survival_mode == 'california':
        survival_curves = pd.read_csv(os.path.join(data_folder, 'californiasurvivalcurve.csv'))
        print("  - Using California-wide survival curve")
    else:  # nhsta
        survival_curves = pd.read_csv(os.path.join(data_folder, 'nhstacurvecalifornia.csv'))
        print("  - Using NHSTA California survival curve")
    
    if ev_scenario == 'BAU':
        ev_forecast = pd.read_csv(os.path.join(data_folder, 'EV_forecast_BAU_only.csv'))
        print("  - Using Business As Usual (BAU) EV forecast")
    else:  # ACCII
        ev_forecast = pd.read_csv(os.path.join(data_folder, 'EV_forecast_ICEban_only.csv'))
        print("  - Using Advanced Clean Cars II (ACC II) EV forecast")
    county_sales_changes = pd.read_csv(os.path.join(data_folder, 'EMFAC_sales_change.csv'))
    zip_to_county = pd.read_csv(os.path.join(data_folder, 'zipcode2county.csv'))
    
    zipcodes = income_data.iloc[:, 2].values
    simulation_years = [2020, 2025, 2030, 2035, 2040, 2045, 2050]
    
    all_summary_results = []
    all_vehicle_details = []
    
    print("Running simulation...")
    for target_year in simulation_years:
        print(f"  Processing year {target_year}...")
        
        for i, zipcode in enumerate(zipcodes):
            vehicle_fleet = project_fleet_for_zipcode(
                zipcode, target_year, fleet_2019, sales_2019, county_sales_changes,
                zip_to_county, ev_forecast, survival_curves, survival_mode
            )
            
            summary = calculate_fleet_summary(vehicle_fleet, zipcode, income_data.iloc[i, 1], target_year)
            all_summary_results.append(summary)
            
            for vehicle_row in vehicle_fleet:
                detail_row = list(vehicle_row) + [target_year, zipcode]
                all_vehicle_details.append(detail_row)
    
    print("Saving results...")
    summary_filename = f'fleet_summary_{survival_mode}_{ev_scenario}.csv'
    details_filename = f'fleet_details_{survival_mode}_{ev_scenario}.csv'
    
    summary_df = pd.DataFrame(all_summary_results,
                             columns=['zipcode', 'income', 'ev_count', 'ice_count',
                                      'ev_percentage', 'avg_age', 'year'])
    summary_df.to_csv(os.path.join(results_folder, summary_filename), index=False)
    
    details_df = pd.DataFrame(all_vehicle_details,
                             columns=['model_year', 'fuel_type', 'original_count',
                                      'surviving_count', 'year', 'zipcode'])
    details_df.to_csv(os.path.join(results_folder, details_filename), index=False)
    
    print(f"Complete! Execution time: {time.time() - start_time:.2f} seconds")
    print(f"Results saved in '{results_folder}' folder:")
    print(f"  - {summary_filename}")
    print(f"  - {details_filename}")
    print(f"Configuration used: Survival={survival_mode}, EV={ev_scenario}")
    
    return summary_df, details_df


def project_fleet_for_zipcode(zipcode, target_year, fleet_2019, sales_2019,
                              county_sales_changes, zip_to_county, ev_forecast,
                              survival_curves, survival_mode='california'):
    """Project a ZIP fleet through target_year using the selected survival curve."""
    zipcode_fleet = fleet_2019[fleet_2019['zipcode'] == zipcode].iloc[:, 2:5].values.astype(float)
    n_baseline = len(zipcode_fleet)
    
    for year in range(BASELINE_YEAR + 1, target_year + 1):
        ev_sales, ice_sales = calculate_annual_sales(year, zipcode, sales_2019,
            county_sales_changes, zip_to_county, ev_forecast)
        zipcode_fleet = np.vstack([zipcode_fleet, [[year, 0, ev_sales], [year, 1, ice_sales]]])
    
    use_conditional = survival_mode in ('zipcode', 'california')
    surviving_counts = []
    for idx, row in enumerate(zipcode_fleet):
        model_year, original_count = row[0], row[2]
        age_target = int((target_year + 1) - model_year)
        p_target = get_survival_rate(age_target, zipcode, survival_curves, survival_mode)
        if use_conditional and idx < n_baseline:
            age_baseline = int((BASELINE_YEAR + 1) - model_year)
            if age_baseline <= 0:
                rate = p_target
            else:
                p_base = get_survival_rate(age_baseline, zipcode, survival_curves, survival_mode)
                rate = min(p_target / p_base if p_base > 0 else 0.0, 1.0)
        else:
            rate = p_target
        surviving_counts.append(np.ceil(original_count * rate))
    return np.column_stack([zipcode_fleet, surviving_counts])


def calculate_annual_sales(year, zipcode, sales_2019, county_sales_changes,
                           zip_to_county, ev_forecast):
    """Calculate new vehicle sales for a specific year and zipcode."""
    baseline = sales_2019[(sales_2019['zipcode'] == zipcode) &
                          (sales_2019['modelyear'] == BASELINE_YEAR)]['vehicles'].values
    if len(baseline) == 0:
        raise ValueError(f'No {BASELINE_YEAR} sales data found for zipcode {zipcode}')
    current_sales = baseline[0]
    county_match = zip_to_county[zip_to_county['ZIP Code'] == int(zipcode)]['County'].values
    if len(county_match) == 0:
        raise ValueError(f'No county found for zipcode {zipcode}')
    county = county_match[0]
    for calc_year in range(BASELINE_YEAR + 1, year + 1):
        change_data = county_sales_changes[(county_sales_changes['County'] == county) &
            (county_sales_changes['Calendar Year'] == calc_year)]['Percentage Change'].values
        if len(change_data) > 0:
            current_sales *= 1 + change_data[0] / 100
    ev_column = f'BEV_Percentage_{year}'
    if ev_column not in ev_forecast.columns:
        raise ValueError(f'No EV forecast data for year {year}')
    ev_pct_data = ev_forecast[ev_forecast['zipcode'] == float(zipcode)][ev_column].values
    ev_percentage = ev_pct_data[0] / 100 if len(ev_pct_data) else ev_forecast[ev_column].median() / 100
    return current_sales * ev_percentage, current_sales * (1 - ev_percentage)


def get_survival_rate(age, zipcode, survival_curves, survival_mode='california'):
    """Get the survival probability for a vehicle of given age."""
    if age <= 0:
        return 1.0
    if survival_mode in ['california', 'nhsta']:
        survival_data = survival_curves[(survival_curves['age'] == age) &
            (survival_curves['zip'] == 11111)]['probability_of_survival'].values
        if len(survival_data):
            return survival_data[0]
        raise ValueError(f'No {survival_mode} survival data found for age {age}')
    specific_data = survival_curves[(survival_curves['age'] == age) &
        (survival_curves['zip'] == zipcode)]['probability_of_survival'].values
    if len(specific_data):
        return specific_data[0]
    average_data = survival_curves[survival_curves['age'] == age]['probability_of_survival'].values
    if len(average_data):
        return average_data.mean()
    raise ValueError(f'No survival data found for age {age}')


def calculate_fleet_summary(vehicle_fleet, zipcode, income, year):
    """Return ZIP, income, EV/ICE counts and fleet age summary."""
    ev_vehicles = vehicle_fleet[vehicle_fleet[:, 1] == 0]
    ice_vehicles = vehicle_fleet[vehicle_fleet[:, 1] == 1]
    total_evs = np.sum(ev_vehicles[:, 3]) if len(ev_vehicles) else 0
    total_ice = np.sum(ice_vehicles[:, 3]) if len(ice_vehicles) else 0
    total_vehicles = total_evs + total_ice
    ev_percentage = total_evs / total_vehicles * 100 if total_vehicles > 0 else 0
    if total_vehicles > 0:
        vehicle_ages = (year + 1) - vehicle_fleet[:, 0]
        avg_age = np.sum(vehicle_ages * vehicle_fleet[:, 3]) / total_vehicles
    else:
        avg_age = 0
    return [zipcode, income, total_evs, total_ice, ev_percentage, avg_age, year]


# To reproduce the paper, run: python run_all_scenarios.py
