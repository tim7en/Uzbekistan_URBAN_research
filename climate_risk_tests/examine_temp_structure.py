"""
Quick diagnostic to examine temperature data structure
"""

import json
from pathlib import Path
from services.climate_data_loader import ClimateDataLoader

def examine_temp_data_structure():
    """Examine the structure of temperature data to understand why hazard scores are zero"""
    
    repo_root = Path(__file__).resolve().parent
    base_path = repo_root / "suhi_analysis_output"
    
    data_loader = ClimateDataLoader(str(base_path))
    data = data_loader.load_all_data()
    
    print("TEMPERATURE DATA STRUCTURE ANALYSIS")
    print("="*60)
    
    # Get one city's temperature data
    temp_data = data['temperature_data']
    if temp_data:
        city = list(temp_data.keys())[0]
        print(f"Examining temperature data for: {city}")
        city_temp_data = temp_data[city]
        
        if city_temp_data:
            year = list(city_temp_data.keys())[0]
            print(f"Year: {year}")
            year_data = city_temp_data[year]
            
            print(f"Year data keys: {list(year_data.keys())}")
            
            # Check for summer_season_summary
            if 'summer_season_summary' in year_data:
                summer_stats = year_data['summer_season_summary']
                print(f"Summer stats keys: {list(summer_stats.keys())}")
                print(f"Summer stats values: {summer_stats}")
            else:
                print("No 'summer_season_summary' found")
                
                # Print structure to understand what's available
                print(f"Available data structure:")
                def print_nested_dict(d, indent=0):
                    for key, value in d.items():
                        print("  " * indent + f"{key}: {type(value)}")
                        if isinstance(value, dict) and indent < 3:
                            print_nested_dict(value, indent + 1)
                        elif isinstance(value, (list, tuple)) and len(value) > 0:
                            print("  " * (indent + 1) + f"[0]: {type(value[0])}")
                
                print_nested_dict(year_data)
    
    print("\n" + "="*60)

if __name__ == "__main__":
    examine_temp_data_structure()
