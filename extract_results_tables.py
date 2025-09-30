import os
import json
import pandas as pd

# Define the base path
base_path = r'd:\dev\Uzbekistan_URBAN_research\suhi_analysis_output\vegetation'

# Get list of cities
cities = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]

# Years
years = list(range(2016, 2025))

# Initialize data structures for each table
tables = {
    'summer_ndvi': [],
    'winter_ndvi': [],
    'ndvi_change': [],
    'summer_lst_mean': [],
    'winter_lst': [],
    'summer_lst': [],
    'lst_change_mean': [],
    'summer_biomass': [],
    'winter_biomass': [],
    'biomass_change': []
}

# Collect data
for city in cities:
    city_path = os.path.join(base_path, city)
    for year in years:
        json_file = os.path.join(city_path, f'{city}_auxiliary_{year}.json')
        if os.path.exists(json_file):
            with open(json_file, 'r') as f:
                data = json.load(f)
                stats = data.get('stats', {})
                
                # Extract values
                summer_ndvi = stats.get('summer_ndvi_mean')
                winter_ndvi = stats.get('winter_ndvi_mean')
                ndvi_change = stats.get('ndvi_change_mean')
                summer_lst_mean = stats.get('summer_lst_mean')
                winter_lst = stats.get('winter_lst_mean')
                summer_lst = stats.get('summer_lst_mean')  # Same as summer_lst_mean
                lst_change_mean = stats.get('lst_change_mean')
                summer_biomass = stats.get('summer_biomass_t_per_ha')
                winter_biomass = stats.get('winter_biomass_t_per_ha')
                biomass_change = stats.get('biomass_change_t_per_ha')
                
                # Append to tables
                tables['summer_ndvi'].append({'City': city, 'Year': year, 'Summer NDVI': summer_ndvi})
                tables['winter_ndvi'].append({'City': city, 'Year': year, 'Winter NDVI': winter_ndvi})
                tables['ndvi_change'].append({'City': city, 'Year': year, 'NDVI Change': ndvi_change})
                tables['summer_lst_mean'].append({'City': city, 'Year': year, 'Summer LST Mean': summer_lst_mean})
                tables['winter_lst'].append({'City': city, 'Year': year, 'Winter LST': winter_lst})
                tables['summer_lst'].append({'City': city, 'Year': year, 'Summer LST': summer_lst})
                tables['lst_change_mean'].append({'City': city, 'Year': year, 'LST Change Mean': lst_change_mean})
                tables['summer_biomass'].append({'City': city, 'Year': year, 'Summer Biomass': summer_biomass})
                tables['winter_biomass'].append({'City': city, 'Year': year, 'Winter Biomass': winter_biomass})
                tables['biomass_change'].append({'City': city, 'Year': year, 'Biomass Change': biomass_change})

# Create DataFrames and save to CSV
output_dir = r'd:\dev\Uzbekistan_URBAN_research'
os.makedirs(output_dir, exist_ok=True)

table_names = {
    'summer_ndvi': 'Table1_Summer_NDVI.csv',
    'winter_ndvi': 'Table2_Winter_NDVI.csv',
    'ndvi_change': 'Table3_NDVI_Change.csv',
    'summer_lst_mean': 'Table4_Summer_LST_Mean.csv',
    'winter_lst': 'Table5_Winter_LST.csv',
    'summer_lst': 'Table6_Summer_LST.csv',
    'lst_change_mean': 'Table7_LST_Change_Mean.csv',
    'summer_biomass': 'Table8_Summer_Biomass.csv',
    'winter_biomass': 'Table9_Winter_Biomass.csv',
    'biomass_change': 'Table10_Biomass_Change.csv'
}

for key, data_list in tables.items():
    df = pd.DataFrame(data_list)
    # Pivot to City-Year format
    df_pivot = df.pivot(index='City', columns='Year', values=df.columns[-1])
    output_file = os.path.join(output_dir, table_names[key])
    df_pivot.to_csv(output_file)
    print(f'Saved {table_names[key]}')

print('All tables created successfully!')